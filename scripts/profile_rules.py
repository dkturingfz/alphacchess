#!/usr/bin/env python3
from __future__ import annotations

import argparse
import cProfile
import json
import pstats
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.phase1_eval import EvalConfig, evaluate_model_vs_model
from alphacchess.phase1_model import PolicyValueNet
from alphacchess.phase1_replay import ReplayDataset
from alphacchess.phase1_selfplay import SelfPlayConfig, run_selfplay
from alphacchess.versions import VERSION_METADATA
from alphacchess.xiangqi_game import XiangqiGame


def _profile_call(label: str, fn):
    prof = cProfile.Profile()
    t0 = time.perf_counter()
    prof.enable()
    fn()
    prof.disable()
    elapsed = time.perf_counter() - t0
    stats = pstats.Stats(prof)
    return {"label": label, "elapsed_sec": elapsed, "stats": stats}


def _top_stats(stats: pstats.Stats, limit: int) -> list[dict]:
    rows = []
    for (filename, lineno, funcname), data in stats.stats.items():
        cc, nc, tt, ct, _ = data
        rows.append(
            {
                "function": f"{Path(filename).name}:{funcname}:{lineno}",
                "primitive_calls": cc,
                "total_calls": nc,
                "total_time_sec": tt,
                "cumulative_time_sec": ct,
            }
        )
    rows.sort(key=lambda r: r["cumulative_time_sec"], reverse=True)
    return rows[:limit]


def build_profile_report(legal_iters: int, clone_iters: int, apply_iters: int, top_n: int, seed: int) -> dict:
    game = XiangqiGame()
    state = game.new_initial_state()

    def bench_legal_actions():
        for _ in range(legal_iters):
            state.legal_actions()

    legal = state.legal_actions()

    def bench_clone():
        local_state = game.new_initial_state()
        for _ in range(clone_iters):
            local_state = local_state.clone()

    def bench_apply_action():
        local_state = game.new_initial_state()
        for idx in range(apply_iters):
            if local_state.is_terminal():
                local_state = game.new_initial_state()
            legal_actions = local_state.legal_actions()
            if not legal_actions:
                break
            local_state.apply_action(legal_actions[idx % len(legal_actions)])

    model = PolicyValueNet.for_xiangqi_v1(seed=seed)

    def bench_selfplay_overhead():
        run_selfplay(
            model,
            SelfPlayConfig(games=2, max_moves=20, terminal_enrichment_games=1, terminal_enrichment_max_moves=4),
            seed=seed,
        )

    ds, _ = run_selfplay(
        model,
        SelfPlayConfig(games=1, max_moves=16, terminal_enrichment_games=1, terminal_enrichment_max_moves=4),
        seed=seed + 1,
    )

    def bench_replay_serialization():
        payload = ds.to_json()
        ReplayDataset.from_json(payload)

    baseline = PolicyValueNet.for_xiangqi_v1(seed=seed + 2)

    def bench_checkpoint_eval():
        evaluate_model_vs_model(model, baseline, EvalConfig(games=4, max_moves=40, seed=seed + 3))

    runs = [
        _profile_call("legal_actions", bench_legal_actions),
        _profile_call("clone", bench_clone),
        _profile_call("apply_action", bench_apply_action),
        _profile_call("selfplay_loop", bench_selfplay_overhead),
        _profile_call("replay_serialization", bench_replay_serialization),
        _profile_call("checkpoint_eval", bench_checkpoint_eval),
    ]

    hotspots = sorted(
        [{"component": run["label"], "elapsed_sec": run["elapsed_sec"]} for run in runs],
        key=lambda row: row["elapsed_sec"],
        reverse=True,
    )

    details = {}
    for run in runs:
        details[run["label"]] = {
            "elapsed_sec": run["elapsed_sec"],
            "top_functions_by_cumulative_time": _top_stats(run["stats"], top_n),
        }

    return {
        "metadata": dict(VERSION_METADATA),
        "profile_schema_version": "phase3_profile_v1",
        "inputs": {
            "legal_action_iterations": legal_iters,
            "clone_iterations": clone_iters,
            "apply_action_iterations": apply_iters,
            "seed": seed,
            "initial_state_legal_actions": len(legal),
        },
        "hotspot_ranking": hotspots,
        "component_details": details,
        "notes": [
            "This profile is a low-scale deterministic sample for hotspot ranking, not a final throughput benchmark.",
            "Use this output to decide whether optimization is justified before architectural changes.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Profile Phase 3 pure-RL hot paths")
    ap.add_argument("--legal-iters", type=int, default=80)
    ap.add_argument("--clone-iters", type=int, default=300)
    ap.add_argument("--apply-iters", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--top-n", type=int, default=12)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    payload = build_profile_report(
        legal_iters=args.legal_iters,
        clone_iters=args.clone_iters,
        apply_iters=args.apply_iters,
        top_n=args.top_n,
        seed=args.seed,
    )
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
