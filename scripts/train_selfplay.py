#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.phase1_eval import EvalConfig, evaluate_vs_random
from alphacchess.phase1_model import PolicyValueNet
from alphacchess.phase1_replay import ReplayDataset
from alphacchess.phase1_selfplay import SelfPlayConfig, run_selfplay
from alphacchess.phase1_train import TrainConfig, train_on_replay
from alphacchess.versions import VERSION_METADATA


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 1 minimal self-play training loop")
    ap.add_argument("--iterations", type=int, default=4)
    ap.add_argument("--games-per-iter", type=int, default=30)
    ap.add_argument("--max-moves", type=int, default=80)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out-dir", default="artifacts/phase1")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    replay_dir = out_dir / "replays"
    ckpt_dir = out_dir / "checkpoints"
    out_dir.mkdir(parents=True, exist_ok=True)
    replay_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    model = PolicyValueNet.for_xiangqi_v1(seed=args.seed)

    history = []
    for it in range(args.iterations):
        ds, sp = run_selfplay(
            model,
            SelfPlayConfig(games=args.games_per_iter, max_moves=args.max_moves),
            seed=args.seed + it,
        )
        replay_path = replay_dir / f"iter_{it:03d}.json"
        ds.save(replay_path)
        obs, pol, val = ds.as_arrays()
        ts = train_on_replay(
            model,
            obs,
            pol,
            val,
            TrainConfig(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr, seed=args.seed + it),
        )
        checkpoint_metadata = dict(VERSION_METADATA)
        checkpoint_metadata["checkpoint_schema_version"] = "phase1_checkpoint_v1"
        checkpoint_metadata["iteration"] = str(it)
        ckpt_path = ckpt_dir / f"iter_{it:03d}.json"
        model.save_checkpoint(ckpt_path, checkpoint_metadata)
        quick_eval = evaluate_vs_random(model, EvalConfig(games=20, seed=args.seed + it))
        history.append(
            {
                "iteration": it,
                "replay_path": str(replay_path),
                "checkpoint": str(ckpt_path),
                "selfplay_games": sp.games,
                "samples": sp.samples,
                "train_steps": ts.steps,
                "last_loss": ts.metrics[-1]["loss"] if ts.metrics else None,
                "quick_eval_win_rate": quick_eval.win_rate,
            }
        )

    summary = {
        "metadata": dict(VERSION_METADATA),
        "iterations": history,
        "final_checkpoint": history[-1]["checkpoint"] if history else None,
    }
    summary_path = out_dir / "train_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
