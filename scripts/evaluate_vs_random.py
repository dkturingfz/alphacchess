#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.phase1_eval import EvalConfig, eval_metadata, evaluate_vs_random
from alphacchess.phase1_model import PolicyValueNet


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate Phase 1 model vs random baseline")
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--max-moves", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    model, ckpt_meta = PolicyValueNet.load_checkpoint(args.checkpoint)
    result = evaluate_vs_random(model, EvalConfig(games=args.games, max_moves=args.max_moves, seed=args.seed))

    payload = {
        "metadata": eval_metadata(),
        "checkpoint_metadata": ckpt_meta,
        "checkpoint": args.checkpoint,
        "games": result.games,
        "wins": result.wins,
        "losses": result.losses,
        "draws": result.draws,
        "win_rate": result.win_rate,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
