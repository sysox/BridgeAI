from __future__ import annotations

from typing import Any, Dict, List, Tuple

SUPPORTED_OPS = {"create_file", "delete_path", "replace_file", "replace_text"}


def _is_sha256_ref(s: Any) -> bool:
    return isinstance(s, str) and s.startswith("sha256:") and len(s) >= len("sha256:") + 16


def validate_packet(pkt: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate BridgePacket v1.
    Returns (ok, errors). Unknown keys are allowed.
    """
    errs: List[str] = []

    if not isinstance(pkt, dict):
        return False, ["packet must be a JSON object"]

    if pkt.get("v") != 1:
        errs.append("packet.v must be 1")

    ops = pkt.get("ops")
    if not isinstance(ops, list) or len(ops) == 0:
        errs.append("packet.ops must be a non-empty list")
        return False, errs

    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            errs.append(f"ops[{i}] must be an object")
            continue

        t = op.get("op")
        if t not in SUPPORTED_OPS:
            errs.append(f"ops[{i}].op unsupported: {t}")

        path = op.get("path")
        if not isinstance(path, str) or not path.strip():
            errs.append(f"ops[{i}].path must be a non-empty string")

        exp = op.get("expect_sha256")
        if exp is not None and not _is_sha256_ref(exp):
            errs.append(f"ops[{i}].expect_sha256 must be 'sha256:<hex>' if present")

        if t in {"create_file", "replace_file"}:
            if "content" not in op or not isinstance(op.get("content"), str):
                errs.append(f"ops[{i}].content must be a string for op={t}")

        if t == "replace_text":
            if "old" not in op or "new" not in op:
                errs.append(f"ops[{i}] replace_text requires old and new")
            else:
                if not isinstance(op.get("old"), str) or not isinstance(op.get("new"), str):
                    errs.append(f"ops[{i}] replace_text old/new must be strings")

    run = pkt.get("run")
    if run is not None:
        if not isinstance(run, list) or not all(isinstance(x, str) for x in run):
            errs.append("packet.run must be a list of strings if present")

    git = pkt.get("git")
    if git is not None:
        if not isinstance(git, dict):
            errs.append("packet.git must be an object if present")
        else:
            add = git.get("add")
            if add is not None:
                if not isinstance(add, list) or not all(isinstance(x, str) for x in add):
                    errs.append("git.add must be a list of strings if present")
            commit = git.get("commit")
            if commit is not None and not isinstance(commit, str):
                errs.append("git.commit must be a string if present")

    post = pkt.get("post")
    if post is not None and not isinstance(post, dict):
        errs.append("packet.post must be an object if present")

    return (len(errs) == 0), errs
