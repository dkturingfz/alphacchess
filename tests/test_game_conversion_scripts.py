import json
import subprocess
import sys


def test_build_positions_script_smoke(tmp_path):
    games = tmp_path / "mini.pgns"
    games.write_text(
        """
[Event "mini"]
[FEN "4k4/9/9/9/9/9/9/9/4R4/4K4 w"]
1. e1e9 1-0
""".strip()
    )
    out = tmp_path / "positions.jsonl"

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_test_positions_from_games.py",
            "--inputs",
            str(games),
            "--output",
            str(out),
            "--emit-start-position",
            "--max-games",
            "1",
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    stats = json.loads(proc.stdout)
    assert stats["games_converted"] == 1
    assert out.exists()
    rows = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
    assert rows
    assert all("fen" in row for row in rows)


def test_validate_positions_script_smoke(tmp_path):
    positions = tmp_path / "positions.jsonl"
    positions.write_text(json.dumps({"fen": "4k4/9/9/9/9/9/9/9/4R4/4K4 w"}) + "\n")

    proc = subprocess.run(
        [sys.executable, "scripts/validate_test_positions.py", "--input", str(positions)],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["status"] == "ok"
    assert payload["valid_fen"] == 1
    assert payload["invalid_fen"] == 0
