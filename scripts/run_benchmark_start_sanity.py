#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.phase1_eval import eval_metadata, evaluate_model_vs_model_on_start_fens
from alphacchess.phase1_model import PolicyValueNet


def _load_fens(path: Path, max_positions: int) -> list[str]:
    fens = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    unique_fens: list[str] = []
    seen = set()
    for fen in fens:
        if fen in seen:
            continue
        seen.add(fen)
        unique_fens.append(fen)
    if max_positions > 0:
        unique_fens = unique_fens[:max_positions]
    if not unique_fens:
        raise ValueError(f"No start FENs available from {path}")
    return unique_fens


def _parse_seeds(raw: str) -> list[int]:
    seeds = [int(chunk.strip()) for chunk in raw.split(",") if chunk.strip()]
    if not seeds:
        raise ValueError("--seeds must contain at least one integer")
    return seeds


def main() -> int:
    parser = argparse.ArgumentParser(description="Small checkpoint sanity check from benchmark_start FEN pool")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument(
        "--start-fens",
        default="data/benchmark_positions/samples/benchmark_start_fens_sample.txt",
        help="Path to benchmark_start-style FEN text file",
    )
    parser.add_argument("--max-start-positions", type=int, default=5)
    parser.add_argument("--games-per-start", type=int, default=2)
    parser.add_argument("--max-moves", type=int, default=120)
    parser.add_argument("--seeds", default="17,29")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    start_fens_path = Path(args.start_fens)
    start_fens = _load_fens(start_fens_path, args.max_start_positions)
    seeds = _parse_seeds(args.seeds)

    candidate_model, candidate_meta = PolicyValueNet.load_checkpoint(args.candidate)
    baseline_model, baseline_meta = PolicyValueNet.load_checkpoint(args.baseline)

    per_seed = []
    for seed in seeds:
        result = evaluate_model_vs_model_on_start_fens(
            candidate_model,
            baseline_model,
            start_fens=start_fens,
            games_per_start=args.games_per_start,
            max_moves=args.max_moves,
            seed=seed,
        )
        per_seed.append(
            {
                "seed": seed,
                "games": result.games,
                "candidate_wins": result.candidate_wins,
                "baseline_wins": result.baseline_wins,
                "draws": result.draws,
                "candidate_score": result.candidate_score,
            }
        )

    total_games = sum(item["games"] for item in per_seed)
    total_candidate_wins = sum(item["candidate_wins"] for item in per_seed)
    total_baseline_wins = sum(item["baseline_wins"] for item in per_seed)
    total_draws = sum(item["draws"] for item in per_seed)

    payload = {
        "metadata": eval_metadata(),
        "evaluation_type": "benchmark_start_checkpoint_sanity_v1",
        "candidate_checkpoint": args.candidate,
        "baseline_checkpoint": args.baseline,
        "candidate_checkpoint_metadata": candidate_meta,
        "baseline_checkpoint_metadata": baseline_meta,
        "start_fens_file": str(start_fens_path),
        "start_positions_used": len(start_fens),
        "games_per_start": args.games_per_start,
        "max_moves": args.max_moves,
        "seeds": seeds,
        "per_seed": per_seed,
        "aggregate": {
            "games": total_games,
            "candidate_wins": total_candidate_wins,
            "baseline_wins": total_baseline_wins,
            "draws": total_draws,
            "candidate_score": ((total_candidate_wins + 0.5 * total_draws) / total_games) if total_games else 0.0,
        },
        "notes": [
            "Exploratory internal sanity check only; not a final strength benchmark claim.",
            "Uses tracked benchmark_start sample FENs and checkpoint-vs-checkpoint proxy gameplay only.",
        ],
    }

    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
