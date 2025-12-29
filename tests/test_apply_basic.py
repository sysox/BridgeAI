from pathlib import Path

from bridgeai.apply import apply_packet


def test_apply_create_replace_delete(tmp_path: Path):
    # Create
    pkt = {
        "v": 1,
        "ops": [{"op": "create_file", "path": "a.txt", "content": "hello\n"}],
    }
    rep = apply_packet(tmp_path, pkt)
    assert rep["ok"] is True
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hello\n"

    # Replace text
    pkt = {
        "v": 1,
        "ops": [{"op": "replace_text", "path": "a.txt", "old": "hello", "new": "hi"}],
    }
    rep = apply_packet(tmp_path, pkt)
    assert rep["ok"] is True
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "hi\n"

    # Delete
    pkt = {
        "v": 1,
        "ops": [{"op": "delete_path", "path": "a.txt"}],
    }
    rep = apply_packet(tmp_path, pkt)
    assert rep["ok"] is True
    assert not (tmp_path / "a.txt").exists()
