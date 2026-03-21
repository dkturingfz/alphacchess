#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.phase1_eval import EvalConfig, eval_metadata, evaluate_model_vs_model, evaluate_vs_random
from alphacchess.phase1_model import PolicyValueNet
from alphacchess.phase1_replay import ReplayDataset, summarize_replay
from alphacchess.phase1_selfplay import SelfPlayConfig, run_selfplay
from alphacchess.phase1_train import TrainConfig, train_on_replay
from alphacchess.versions import VERSION_METADATA


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 2 pure RL self-play training loop")
    ap.add_argument("--iterations", type=int, default=6)
    ap.add_argument("--games-per-iter", type=int, default=64)
    ap.add_argument("--max-moves", type=int, default=80)
    ap.add_argument("--terminal-enrichment-games", type=int, default=8)
    ap.add_argument("--terminal-enrichment-max-moves", type=int, default=6)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--quick-eval-games", type=int, default=20)
    ap.add_argument("--checkpoint-eval-games", type=int, default=16)
    ap.add_argument("--checkpoint-eval-max-moves", type=int, default=120)
    ap.add_argument("--baseline-checkpoint", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out-dir", default="artifacts/phase2_pure_rl")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    replay_dir = out_dir / "replays"
    ckpt_dir = out_dir / "checkpoints"
    iter_dir = out_dir / "iteration_summaries"
    eval_dir = out_dir / "evaluations"
    out_dir.mkdir(parents=True, exist_ok=True)
    replay_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    iter_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)

    model = PolicyValueNet.for_xiangqi_v1(seed=args.seed)
    baseline_model = None
    baseline_metadata = None
    if args.baseline_checkpoint:
        baseline_model, baseline_metadata = PolicyValueNet.load_checkpoint(args.baseline_checkpoint)

    history = []
    previous_checkpoint = args.baseline_checkpoint if args.baseline_checkpoint else None
    for it in range(args.iterations):
        ds, sp = run_selfplay(
            model,
            SelfPlayConfig(
                games=args.games_per_iter,
                max_moves=args.max_moves,
                terminal_enrichment_games=args.terminal_enrichment_games,
                terminal_enrichment_max_moves=args.terminal_enrichment_max_moves,
            ),
            seed=args.seed + it,
        )
        replay_path = replay_dir / f"iter_{it:03d}.json"
        ds.save(replay_path)
        replay_stats = summarize_replay(ds)
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
        quick_eval = evaluate_vs_random(model, EvalConfig(games=args.quick_eval_games, seed=args.seed + it))

        checkpoint_eval_summary = None
        if previous_checkpoint:
            previous_model, previous_meta = PolicyValueNet.load_checkpoint(previous_checkpoint)
            c2c = evaluate_model_vs_model(
                model,
                previous_model,
                EvalConfig(
                    games=args.checkpoint_eval_games,
                    max_moves=args.checkpoint_eval_max_moves,
                    seed=args.seed + it,
                ),
            )
            checkpoint_eval_summary = {
                "metadata": eval_metadata(),
                "evaluation_type": "candidate_vs_previous_checkpoint",
                "candidate_checkpoint": str(ckpt_path),
                "baseline_checkpoint": str(previous_checkpoint),
                "candidate_checkpoint_metadata": checkpoint_metadata,
                "baseline_checkpoint_metadata": previous_meta,
                "games": c2c.games,
                "candidate_wins": c2c.candidate_wins,
                "baseline_wins": c2c.baseline_wins,
                "draws": c2c.draws,
                "candidate_score": c2c.candidate_score,
            }
            (eval_dir / f"iter_{it:03d}_vs_previous.json").write_text(json.dumps(checkpoint_eval_summary, indent=2))

        fixed_baseline_eval_summary = None
        if baseline_model is not None:
            c2b = evaluate_model_vs_model(
                model,
                baseline_model,
                EvalConfig(
                    games=args.checkpoint_eval_games,
                    max_moves=args.checkpoint_eval_max_moves,
                    seed=args.seed + 10000 + it,
                ),
            )
            fixed_baseline_eval_summary = {
                "metadata": eval_metadata(),
                "evaluation_type": "candidate_vs_fixed_baseline",
                "candidate_checkpoint": str(ckpt_path),
                "baseline_checkpoint": str(args.baseline_checkpoint),
                "candidate_checkpoint_metadata": checkpoint_metadata,
                "baseline_checkpoint_metadata": baseline_metadata,
                "games": c2b.games,
                "candidate_wins": c2b.candidate_wins,
                "baseline_wins": c2b.baseline_wins,
                "draws": c2b.draws,
                "candidate_score": c2b.candidate_score,
            }
            (eval_dir / f"iter_{it:03d}_vs_fixed_baseline.json").write_text(
                json.dumps(fixed_baseline_eval_summary, indent=2)
            )

        iter_summary = {
            "metadata": dict(VERSION_METADATA),
            "iteration": it,
            "replay_path": str(replay_path),
            "checkpoint": str(ckpt_path),
            "total_games": sp.games,
            "samples": sp.samples,
            "selfplay_games": sp.selfplay_games,
            "terminal_enrichment_games": sp.terminal_enrichment_games,
            "natural_terminations": sp.natural_terminations,
            "step_cap_truncations": sp.step_cap_truncations,
            "result_counts": replay_stats["result_counts"],
            "value_mean": replay_stats["value_mean"],
            "value_non_zero_fraction": replay_stats["value_non_zero_fraction"],
            "value_positive_count": replay_stats["value_positive_count"],
            "value_zero_count": replay_stats["value_zero_count"],
            "value_negative_count": replay_stats["value_negative_count"],
            "train_steps": ts.steps,
            "last_loss": ts.metrics[-1]["loss"] if ts.metrics else None,
            "quick_eval_win_rate": quick_eval.win_rate,
            "quick_eval_wins": quick_eval.wins,
            "quick_eval_losses": quick_eval.losses,
            "quick_eval_draws": quick_eval.draws,
            "checkpoint_eval_vs_previous": checkpoint_eval_summary,
            "checkpoint_eval_vs_fixed_baseline": fixed_baseline_eval_summary,
        }
        (iter_dir / f"iter_{it:03d}.json").write_text(json.dumps(iter_summary, indent=2))
        history.append(iter_summary)
        previous_checkpoint = str(ckpt_path)

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
