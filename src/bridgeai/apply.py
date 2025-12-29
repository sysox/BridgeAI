from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from bridgeai.schema import validate_packet


def sha256_text(s: str) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def is_git_repo(root: Path) -> bool:
    return (root / ".git").exists()


def run_cmd(root: Path, cmd: str) -> Dict[str, Any]:
    proc = subprocess.run(cmd, shell=True, cwd=str(root), capture_output=True, text=True)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _apply_one_op(root: Path, op: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """
    Apply a single op. Returns (changed_relpath_or_None, note).
    Optional precondition: expect_sha256 compares current whole-file content hash.
    """
    rel = op["path"]
    p = (root / rel)

    exp = op.get("expect_sha256")
    if exp is not None:
        cur = read_text(p) if p.exists() else ""
        got = sha256_text(cur)
        if got != exp:
            raise RuntimeError(f"precondition failed for {rel}: expected {exp}, got {got}")

    t = op["op"]

    if t == "create_file":
        if p.exists():
            raise RuntimeError(f"create_file: already exists: {rel}")
        write_text(p, op.get("content", ""))
        return rel, "created"

    if t == "delete_path":
        if p.exists():
            p.unlink()
            return rel, "deleted"
        return None, "missing"

    if t == "replace_file":
        write_text(p, op.get("content", ""))
        return rel, "replaced"

    if t == "replace_text":
        cur = read_text(p) if p.exists() else ""
        new = cur.replace(op.get("old", ""), op.get("new", ""))
        write_text(p, new)
        return rel, "replaced_text"

    raise RuntimeError(f"unsupported op: {t}")


def _git_add_commit(root: Path, git_cfg: Dict[str, Any]) -> Dict[str, Any]:
    add_paths = git_cfg.get("add", ["."])
    subprocess.run(["git", "add", *add_paths], cwd=str(root), check=False)
    msg = git_cfg.get("commit", "apply patch")
    proc = subprocess.run(["git", "commit", "-m", msg], cwd=str(root), capture_output=True, text=True)
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def apply_packet(root: Path, pkt: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply BridgePacket v1.
    Fail-fast on first error. Always returns a JSON-serializable report dict.
    """
    root = root.resolve()

    ok, errs = validate_packet(pkt)
    if not ok:
        return {"ok": False, "errors": errs}

    changed: List[str] = []
    notes: List[Dict[str, Any]] = []

    # 1) Apply ops
    try:
        for op in pkt.get("ops", []):
            ch, note = _apply_one_op(root, op)
            if ch:
                changed.append(ch)
            notes.append({"op": op.get("op"), "path": op.get("path"), "note": note})
    except Exception as e:
        return {"ok": False, "error": str(e), "changed": changed, "notes": notes}

    # 2) Run commands
    run_reports: List[Dict[str, Any]] = []
    for cmd in (pkt.get("run") or []):
        r = run_cmd(root, cmd)
        run_reports.append(r)
        if r["returncode"] != 0:
            return {"ok": False, "changed": changed, "notes": notes, "run": run_reports}

    # 3) Git commit (optional)
    git_report = None
    git_cfg = pkt.get("git")
    if git_cfg and is_git_repo(root):
        git_report = _git_add_commit(root, git_cfg)

    return {"ok": True, "changed": changed, "notes": notes, "run": run_reports, "git": git_report}
