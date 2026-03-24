#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean

FROZEN_PROTOCOL = {
    "start_fens_file": "data/benchmark_positions/samples/benchmark_start_fens_sample.txt",
    "max_start_positions": 8,
    "games_per_start": 4,
    "max_moves": 60,
    "seeds": "17,29,41,53",
}

ALLOWED_KEYS = {
    "iterations",
    "games_per_iter",
    "max_moves",
    "terminal_enrichment_games",
    "terminal_enrichment_max_moves",
    "epochs",
    "batch_size",
    "quick_eval_games",
    "checkpoint_eval_games",
    "checkpoint_eval_max_moves",
}


@dataclass
class RunMetrics:
    run_id: int
    run_name: str
    train_out_dir: str
    config: dict
    quality: dict
    pairs: list[dict]
    pair_panel: list[list[int]]
    pair_abs_distance_mean: float
    pair_seed_stddev_mean: float
    improved: bool
    improvement_reasons: list[str]
    diagnosis: dict


def _run_cmd(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _pair_panel_for_summary(train_summary: dict) -> list[tuple[int, int]]:
    iterations = sorted(int(row["iteration"]) for row in train_summary["iterations"])
    if len(iterations) < 2:
        raise ValueError("Need at least 2 iterations for pair panel")
    latest = iterations[-1]
    later = min(3, latest)
    pairs = [(1, 0), (later, 0), (later, max(0, later - 1))]
    deduped: list[tuple[int, int]] = []
    for cand, base in pairs:
        if cand <= base:
            continue
        if (cand, base) not in deduped:
            deduped.append((cand, base))
    return deduped


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _quality_metrics(train_summary: dict) -> dict:
    rows = train_summary["iterations"]
    per_iter = []
    for row in rows:
        total_games = row["natural_terminations"] + row["step_cap_truncations"]
        trunc_ratio = (row["step_cap_truncations"] / total_games) if total_games else 0.0
        prev = row.get("checkpoint_eval_vs_previous")
        per_iter.append(
            {
                "iteration": row["iteration"],
                "natural_terminations": row["natural_terminations"],
                "step_cap_truncations": row["step_cap_truncations"],
                "truncation_ratio": trunc_ratio,
                "value_non_zero_fraction": row["value_non_zero_fraction"],
                "quick_eval_win_rate": row["quick_eval_win_rate"],
                "checkpoint_eval_vs_previous": (prev.get("candidate_score") if prev else None),
            }
        )
    avg_trunc = mean(item["truncation_ratio"] for item in per_iter)
    avg_vnz = mean(item["value_non_zero_fraction"] for item in per_iter)
    cprev = [item["checkpoint_eval_vs_previous"] for item in per_iter if item["checkpoint_eval_vs_previous"] is not None]
    cprev_std_proxy = (max(cprev) - min(cprev)) if cprev else 0.0
    return {
        "iterations": per_iter,
        "avg_truncation_ratio": avg_trunc,
        "avg_value_non_zero_fraction": avg_vnz,
        "checkpoint_eval_vs_previous_range": cprev_std_proxy,
    }


def _run_pair_eval(run_root: Path, ckpt_dir: Path, cand: int, base: int) -> dict:
    out_file = run_root / "benchmark_start_sanity" / f"iter_{cand:03d}_vs_iter_{base:03d}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python",
        "scripts/run_benchmark_start_sanity.py",
        "--candidate",
        str(ckpt_dir / f"iter_{cand:03d}.json"),
        "--baseline",
        str(ckpt_dir / f"iter_{base:03d}.json"),
        "--start-fens",
        FROZEN_PROTOCOL["start_fens_file"],
        "--max-start-positions",
        str(FROZEN_PROTOCOL["max_start_positions"]),
        "--games-per-start",
        str(FROZEN_PROTOCOL["games_per_start"]),
        "--max-moves",
        str(FROZEN_PROTOCOL["max_moves"]),
        "--seeds",
        FROZEN_PROTOCOL["seeds"],
        "--out",
        str(out_file),
    ]
    _run_cmd(cmd)
    payload = _load_json(out_file)
    agg = payload["aggregate"]
    return {
        "pair": [cand, base],
        "file": str(out_file),
        "candidate_score": agg["candidate_score"],
        "seed_stddev": agg["candidate_score_stddev_across_seeds"],
        "distance_from_50": abs(agg["candidate_score"] - 0.5),
    }


def _diagnose(quality: dict, pairs: list[dict]) -> dict:
    avg_trunc = quality["avg_truncation_ratio"]
    avg_vnz = quality["avg_value_non_zero_fraction"]
    cprev_noise = quality["checkpoint_eval_vs_previous_range"]
    pair_dir = mean(item["distance_from_50"] for item in pairs)
    pair_std = mean(item["seed_stddev"] for item in pairs)
    return {
        "truncation_too_high": avg_trunc >= 0.50,
        "value_non_zero_too_low": avg_vnz <= 0.20,
        "checkpoint_eval_noisy": cprev_noise >= 0.30,
        "pairs_lack_directionality": pair_dir <= 0.06,
        "avg_truncation_ratio": avg_trunc,
        "avg_value_non_zero_fraction": avg_vnz,
        "checkpoint_eval_vs_previous_range": cprev_noise,
        "pair_abs_distance_mean": pair_dir,
        "pair_seed_stddev_mean": pair_std,
    }


def _next_config(prev: dict, diagnosis: dict, round_id: int) -> tuple[dict, list[str]]:
    cfg = deepcopy(prev)
    reasons = []
    if diagnosis["truncation_too_high"]:
        cfg["max_moves"] = min(120, int(cfg["max_moves"]) + 20)
        cfg["terminal_enrichment_games"] = int(cfg["terminal_enrichment_games"]) + 4
        cfg["terminal_enrichment_max_moves"] = min(16, int(cfg["terminal_enrichment_max_moves"]) + 2)
        reasons.append("reduce truncation, raise terminal supervision chance")
    if diagnosis["value_non_zero_too_low"]:
        cfg["games_per_iter"] = int(cfg["games_per_iter"]) + 2
        cfg["epochs"] = min(4, int(cfg["epochs"]) + 1)
        reasons.append("increase non-zero value coverage")
    if diagnosis["checkpoint_eval_noisy"] or diagnosis["pairs_lack_directionality"]:
        cfg["checkpoint_eval_games"] = int(cfg["checkpoint_eval_games"]) + 2
        cfg["quick_eval_games"] = int(cfg["quick_eval_games"]) + 2
        reasons.append("reduce eval variance to improve checkpoint separability")

    if not reasons:
        ladder = [
            ("games_per_iter", 4),
            ("checkpoint_eval_games", 4),
            ("epochs", 1),
            ("batch_size", -32),
            ("checkpoint_eval_max_moves", 20),
        ]
        key, delta = ladder[(round_id - 1) % len(ladder)]
        cfg[key] = max(32, int(cfg[key]) + delta)
        reasons.append(f"conservative fallback adjustment on {key}")

    filtered = {k: v for k, v in cfg.items() if k in ALLOWED_KEYS}
    return filtered, reasons


def _improvement(prev: RunMetrics, curr_quality: dict, curr_pairs: list[dict]) -> tuple[bool, list[str]]:
    reasons = []
    curr_vnz = curr_quality["avg_value_non_zero_fraction"]
    prev_vnz = prev.quality["avg_value_non_zero_fraction"]
    if curr_vnz - prev_vnz >= 0.03:
        reasons.append("value_non_zero_fraction +>=0.03")

    curr_tr = curr_quality["avg_truncation_ratio"]
    prev_tr = prev.quality["avg_truncation_ratio"]
    if prev_tr - curr_tr >= 0.10:
        reasons.append("truncation_ratio ->=0.10")

    curr_pair_abs = mean(item["distance_from_50"] for item in curr_pairs)
    prev_pair_abs = prev.pair_abs_distance_mean
    if curr_pair_abs - prev_pair_abs >= 0.05:
        reasons.append("pair |score-0.5| mean +>=0.05")

    curr_std = mean(item["seed_stddev"] for item in curr_pairs)
    prev_std = prev.pair_seed_stddev_mean
    if (prev_std - curr_std >= 0.02) and (curr_pair_abs > prev_pair_abs):
        reasons.append("pair stddev down and directionality up")

    return (len(reasons) > 0), reasons


def _run_training(run_dir: Path, cfg: dict, seed: int) -> dict:
    train_out = run_dir / "train"
    cmd = [
        "python",
        "scripts/train_selfplay.py",
        "--iterations",
        str(cfg["iterations"]),
        "--games-per-iter",
        str(cfg["games_per_iter"]),
        "--max-moves",
        str(cfg["max_moves"]),
        "--terminal-enrichment-games",
        str(cfg["terminal_enrichment_games"]),
        "--terminal-enrichment-max-moves",
        str(cfg["terminal_enrichment_max_moves"]),
        "--epochs",
        str(cfg["epochs"]),
        "--batch-size",
        str(cfg["batch_size"]),
        "--quick-eval-games",
        str(cfg["quick_eval_games"]),
        "--checkpoint-eval-games",
        str(cfg["checkpoint_eval_games"]),
        "--checkpoint-eval-max-moves",
        str(cfg["checkpoint_eval_max_moves"]),
        "--seed",
        str(seed),
        "--out-dir",
        str(train_out),
    ]
    _run_cmd(cmd)
    return _load_json(train_out / "train_summary.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Autonomous pure-RL training signal hardening loop")
    parser.add_argument("--max-adjust-rounds", type=int, default=5)
    parser.add_argument("--max-total-runs", type=int, default=6)
    parser.add_argument("--max-total-pairs", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260324)
    parser.add_argument("--out-root", default="")
    args = parser.parse_args()

    if args.out_root:
        root = Path(args.out_root)
    else:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        root = Path("artifacts") / f"local_signal_hardening_{ts}"
    root.mkdir(parents=True, exist_ok=True)

    baseline_cfg = {
        "iterations": 3,
        "games_per_iter": 6,
        "max_moves": 60,
        "terminal_enrichment_games": 2,
        "terminal_enrichment_max_moves": 6,
        "epochs": 1,
        "batch_size": 64,
        "quick_eval_games": 4,
        "checkpoint_eval_games": 4,
        "checkpoint_eval_max_moves": 60,
    }

    all_runs: list[RunMetrics] = []
    total_pairs = 0
    no_improve_streak = 0
    next_cfg = deepcopy(baseline_cfg)

    for run_id in range(0, args.max_total_runs):
        run_name = "baseline" if run_id == 0 else f"adjust_round_{run_id}"
        run_dir = root / run_name
        summary = _run_training(run_dir, next_cfg, args.seed + 1000 * run_id)
        quality = _quality_metrics(summary)
        pair_panel = _pair_panel_for_summary(summary)

        pairs = []
        for cand, base in pair_panel:
            if total_pairs >= args.max_total_pairs:
                break
            pairs.append(_run_pair_eval(run_dir, run_dir / "train" / "checkpoints", cand, base))
            total_pairs += 1
        if not pairs:
            break

        diagnosis = _diagnose(quality, pairs)
        pair_abs_mean = mean(item["distance_from_50"] for item in pairs)
        pair_std_mean = mean(item["seed_stddev"] for item in pairs)

        improved = run_id == 0
        reasons = ["baseline"]
        if all_runs:
            improved, reasons = _improvement(all_runs[-1], quality, pairs)

        metrics = RunMetrics(
            run_id=run_id,
            run_name=run_name,
            train_out_dir=str(run_dir / "train"),
            config=deepcopy(next_cfg),
            quality=quality,
            pairs=pairs,
            pair_panel=[[a, b] for a, b in pair_panel],
            pair_abs_distance_mean=pair_abs_mean,
            pair_seed_stddev_mean=pair_std_mean,
            improved=improved,
            improvement_reasons=reasons,
            diagnosis=diagnosis,
        )
        all_runs.append(metrics)

        if run_id == 0:
            next_cfg, _ = _next_config(next_cfg, diagnosis, run_id + 1)
            continue

        if improved:
            no_improve_streak = 0
        else:
            no_improve_streak += 1

        if no_improve_streak >= 2:
            break
        if run_id >= args.max_adjust_rounds:
            break
        if total_pairs >= args.max_total_pairs:
            break
        next_cfg, _ = _next_config(next_cfg, diagnosis, run_id + 1)

    report = {
        "experiment_schema_version": "pure_rl_signal_hardening_v1",
        "frozen_protocol": deepcopy(FROZEN_PROTOCOL),
        "hard_limits": {
            "max_adjust_rounds": args.max_adjust_rounds,
            "max_total_runs": args.max_total_runs,
            "max_total_pairs": args.max_total_pairs,
        },
        "baseline_config": baseline_cfg,
        "runs_executed": [
            {
                "run_id": r.run_id,
                "run_name": r.run_name,
                "train_out_dir": r.train_out_dir,
                "config": r.config,
                "quality": r.quality,
                "pairs": r.pairs,
                "pair_panel": r.pair_panel,
                "pair_abs_distance_mean": r.pair_abs_distance_mean,
                "pair_seed_stddev_mean": r.pair_seed_stddev_mean,
                "improved": r.improved,
                "improvement_reasons": r.improvement_reasons,
                "diagnosis": r.diagnosis,
            }
            for r in all_runs
        ],
        "stopped_early": len(all_runs) < args.max_total_runs,
        "total_runs": len(all_runs),
        "total_pair_evaluations": total_pairs,
    }

    out_file = root / "signal_hardening_report.json"
    out_file.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
