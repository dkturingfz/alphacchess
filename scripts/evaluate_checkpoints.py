#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.phase1_eval import EvalConfig, eval_metadata, evaluate_model_vs_model
from alphacchess.phase1_model import PolicyValueNet


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate candidate checkpoint vs baseline checkpoint")
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--games", type=int, default=32)
    ap.add_argument("--max-moves", type=int, default=120)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    candidate_model, candidate_meta = PolicyValueNet.load_checkpoint(args.candidate)
    baseline_model, baseline_meta = PolicyValueNet.load_checkpoint(args.baseline)

    result = evaluate_model_vs_model(
        candidate_model,
        baseline_model,
        EvalConfig(games=args.games, max_moves=args.max_moves, seed=args.seed),
    )

    payload = {
        "metadata": eval_metadata(),
        "evaluation_type": "checkpoint_vs_checkpoint",
        "candidate_checkpoint": args.candidate,
        "baseline_checkpoint": args.baseline,
        "candidate_checkpoint_metadata": candidate_meta,
        "baseline_checkpoint_metadata": baseline_meta,
        "games": result.games,
        "candidate_wins": result.candidate_wins,
        "baseline_wins": result.baseline_wins,
        "draws": result.draws,
        "candidate_score": result.candidate_score,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
