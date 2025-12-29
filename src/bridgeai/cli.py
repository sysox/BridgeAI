from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bridgeai.apply import apply_packet


def _read_packet(path: str) -> dict:
    if path == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="bridge")
    sub = p.add_subparsers(dest="cmd", required=True)

    ap = sub.add_parser("apply", help="Apply a BridgePacket JSON to a repo")
    ap.add_argument("packet", help="Path to packet JSON, or '-' for stdin")
    ap.add_argument("--root", default=".", help="Repo/workspace root")

    args = p.parse_args(argv)

    if args.cmd == "apply":
        pkt = _read_packet(args.packet)
        report = apply_packet(Path(args.root), pkt)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report.get("ok") else 2

    return 0
