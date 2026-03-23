#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.xiangqi_game import XiangqiState


@dataclass
class ValidationStats:
    positions_seen: int = 0
    valid_fen: int = 0
    invalid_fen: int = 0
    zero_legal_moves: int = 0


def _iter_fens(path: Path):
    if path.suffix.lower() == ".jsonl":
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            fen = rec.get("fen") or rec.get("initial_fen") or rec.get("final_fen")
            if fen:
                yield str(fen).strip()
        return

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        yield text


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate FEN test positions with Xiangqi rules checks")
    parser.add_argument("--input", required=True, help="Input .jsonl or plain-text FEN list")
    parser.add_argument("--max-positions", type=int, default=0, help="Optional cap for smoke validation")
    parser.add_argument(
        "--fail-on-zero-legal",
        action="store_true",
        help="Treat non-terminal positions with 0 legal actions as invalid",
    )
    args = parser.parse_args()

    stats = ValidationStats()
    samples: list[dict[str, str]] = []

    for fen in _iter_fens(Path(args.input)):
        if args.max_positions and stats.positions_seen >= args.max_positions:
            break
        stats.positions_seen += 1
        try:
            state = XiangqiState.from_fen(fen)
            legal_count = len(state.legal_actions())
            stats.valid_fen += 1
            if legal_count == 0 and not state.is_terminal():
                stats.zero_legal_moves += 1
                if len(samples) < 5:
                    samples.append({"fen": fen, "issue": "non-terminal with zero legal moves"})
        except Exception as exc:
            stats.invalid_fen += 1
            if len(samples) < 5:
                samples.append({"fen": fen, "issue": str(exc)})

    if args.fail_on_zero_legal and stats.zero_legal_moves > 0:
        stats.invalid_fen += stats.zero_legal_moves

    payload = {
        **stats.__dict__,
        "samples": samples,
        "status": "ok" if stats.invalid_fen == 0 else "failed",
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
