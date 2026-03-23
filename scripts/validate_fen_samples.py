#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.xiangqi_game import XiangqiState

DEFAULT_SAMPLE_FILES = {
    "opening": Path("data/test_positions/samples/opening_fens_sample.txt"),
    "middlegame": Path("data/test_positions/samples/middlegame_fens_sample.txt"),
    "endgame": Path("data/test_positions/samples/endgame_fens_sample.txt"),
    "near_terminal": Path("data/test_positions/samples/near_terminal_fens_sample.txt"),
    "regression": Path("data/test_positions/samples/regression_fens_sample.txt"),
    "benchmark_start": Path("data/benchmark_positions/samples/benchmark_start_fens_sample.txt"),
}


def _iter_fens(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _validate_file(path: Path, near_terminal_limit: int, enforce_near_terminal: bool) -> dict[str, object]:
    fens = _iter_fens(path)
    invalid = 0
    zero_non_terminal = 0
    near_terminal_violations = 0
    samples: list[dict[str, str]] = []

    for fen in fens:
        try:
            state = XiangqiState.from_fen(fen)
            legal = len(state.legal_actions())
            terminal = state.is_terminal()
            if legal == 0 and not terminal:
                zero_non_terminal += 1
            if enforce_near_terminal and not (terminal or legal <= near_terminal_limit):
                near_terminal_violations += 1
                if len(samples) < 5:
                    samples.append({"fen": fen, "issue": f"legal_actions={legal}"})
        except Exception as exc:
            invalid += 1
            if len(samples) < 5:
                samples.append({"fen": fen, "issue": str(exc)})

    return {
        "positions_seen": len(fens),
        "invalid_fen": invalid,
        "zero_legal_non_terminal": zero_non_terminal,
        "near_terminal_violations": near_terminal_violations,
        "status": "ok" if invalid == 0 and zero_non_terminal == 0 and near_terminal_violations == 0 else "failed",
        "samples": samples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate all tracked curated FEN sample sets")
    parser.add_argument("--near-terminal-legal-limit", type=int, default=4)
    args = parser.parse_args()

    summary: dict[str, object] = {}
    failed = False

    for name, rel_path in DEFAULT_SAMPLE_FILES.items():
        path = ROOT / rel_path
        result = _validate_file(
            path=path,
            near_terminal_limit=args.near_terminal_legal_limit,
            enforce_near_terminal=(name == "near_terminal"),
        )
        summary[name] = {"path": str(rel_path), **result}
        if result["status"] != "ok":
            failed = True

    payload = {
        "status": "ok" if not failed else "failed",
        "near_terminal_legal_limit": args.near_terminal_legal_limit,
        "sets": summary,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
