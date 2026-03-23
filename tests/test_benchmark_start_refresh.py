import json
import subprocess
import sys
from pathlib import Path


def _read_fens(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def test_refresh_benchmark_start_samples_is_deterministic(tmp_path):
    corpus = tmp_path / "positions.jsonl"
    rows = [
        {"source_file": "a.pgns", "source_game_index": 1, "source_ply": 0, "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w", "category": "benchmark_start"},
        {"source_file": "a.pgns", "source_game_index": 1, "source_ply": 4, "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/2P6/P3P1P1P/1C5C1/9/RNBAKABNR w", "category": "opening"},
        {"source_file": "b.pgns", "source_game_index": 3, "source_ply": 8, "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/4P4/9/P1P3P1P/1C5C1/9/RNBAKABNR w", "category": "opening"},
        {"source_file": "c.pgns", "source_game_index": 2, "source_ply": 12, "fen": "rnbakabnr/9/1c5c1/p1p1p3p/6p2/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w", "category": "opening"},
        {"source_file": "d.pgns", "source_game_index": 5, "source_ply": 20, "fen": "rnbakabnr/9/1c5c1/p1p1p3p/6p2/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w", "category": "opening"},
    ]
    corpus.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    out1 = tmp_path / "sample1.txt"
    out2 = tmp_path / "sample2.txt"
    summary1 = tmp_path / "summary1.json"
    summary2 = tmp_path / "summary2.json"

    cmd1 = [
        sys.executable,
        "scripts/refresh_benchmark_start_samples.py",
        "--input",
        str(corpus),
        "--output-sample",
        str(out1),
        "--selected-count",
        "3",
        "--max-source-ply",
        "12",
        "--summary-output",
        str(summary1),
    ]
    cmd2 = [
        sys.executable,
        "scripts/refresh_benchmark_start_samples.py",
        "--input",
        str(corpus),
        "--output-sample",
        str(out2),
        "--selected-count",
        "3",
        "--max-source-ply",
        "12",
        "--summary-output",
        str(summary2),
    ]

    subprocess.run(cmd1, check=True, capture_output=True, text=True)
    subprocess.run(cmd2, check=True, capture_output=True, text=True)

    assert _read_fens(out1) == _read_fens(out2)

    payload = json.loads(summary1.read_text(encoding="utf-8"))
    assert payload["total_candidate_count"] == 4
    assert payload["deduplicated_candidate_count"] == 4
    assert payload["selected_sample_count"] == 3
    assert payload["selected_diversity"]["unique_fens"] == 3
