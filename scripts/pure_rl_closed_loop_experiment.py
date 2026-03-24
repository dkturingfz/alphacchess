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

ALLOWED_TRAIN_KEYS = {
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

# Stable panel type across all rounds (resolved against available checkpoints).
PANEL_TEMPLATE = [(1, 0), (3, 0), (2, 1)]


@dataclass
class RoundResult:
    run_id: int
    run_name: str
    config: dict
    quality: dict
    pair_results: list[dict]
    diagnosis: dict
    classification: str
    rationale: list[str]
    next_adjustment_reason: list[str]


def _run_cmd(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _build_panel_for_run(iterations: list[int]) -> list[tuple[int, int]]:
    available = set(iterations)
    pairs: list[tuple[int, int]] = []
    for cand, base in PANEL_TEMPLATE:
        if cand in available and base in available and cand > base and (cand, base) not in pairs:
            pairs.append((cand, base))
    if len(pairs) < 3:
        latest = max(iterations)
        fallback = [(1, 0), (latest, 0), (latest, max(0, latest - 1))]
        for cand, base in fallback:
            if cand in available and base in available and cand > base and (cand, base) not in pairs:
                pairs.append((cand, base))
    return pairs[:4]


def _quality_from_summary(summary: dict) -> dict:
    rows = summary["iterations"]
    per_iter = []
    checkpoint_scores = []
    for row in rows:
        total = row["natural_terminations"] + row["step_cap_truncations"]
        trunc_ratio = (row["step_cap_truncations"] / total) if total else 0.0
        cprev = row.get("checkpoint_eval_vs_previous")
        cscore = cprev.get("candidate_score") if cprev else None
        if cscore is not None:
            checkpoint_scores.append(float(cscore))
        per_iter.append(
            {
                "iteration": int(row["iteration"]),
                "natural_terminations": int(row["natural_terminations"]),
                "truncation_ratio": trunc_ratio,
                "value_non_zero_fraction": float(row["value_non_zero_fraction"]),
                "checkpoint_eval_vs_previous": cscore,
                "quick_eval_win_rate": float(row["quick_eval_win_rate"]),
            }
        )

    return {
        "per_iteration": per_iter,
        "natural_terminations_mean": mean(item["natural_terminations"] for item in per_iter),
        "truncation_ratio_mean": mean(item["truncation_ratio"] for item in per_iter),
        "value_non_zero_fraction_mean": mean(item["value_non_zero_fraction"] for item in per_iter),
        "quick_eval_win_rate_mean": mean(item["quick_eval_win_rate"] for item in per_iter),
        "checkpoint_eval_vs_previous_mean": mean(checkpoint_scores) if checkpoint_scores else None,
        "checkpoint_eval_vs_previous_range": (max(checkpoint_scores) - min(checkpoint_scores)) if checkpoint_scores else 0.0,
    }


def _eval_pair(run_dir: Path, ckpt_dir: Path, cand: int, base: int) -> dict:
    out_path = run_dir / "benchmark_start_sanity" / f"iter_{cand:03d}_vs_iter_{base:03d}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
        str(out_path),
    ]
    _run_cmd(cmd)
    payload = _load_json(out_path)
    agg = payload["aggregate"]
    return {
        "pair": [cand, base],
        "candidate_score": float(agg["candidate_score"]),
        "seed_stddev": float(agg["candidate_score_stddev_across_seeds"]),
        "abs_score_minus_0_5": abs(float(agg["candidate_score"]) - 0.5),
        "file": str(out_path),
    }


def _find_pair(pairs: list[dict], cand: int, base: int) -> dict | None:
    for item in pairs:
        if item["pair"] == [cand, base]:
            return item
    return None


def _diagnose(quality: dict, pairs: list[dict]) -> dict:
    pair_std_mean = mean(item["seed_stddev"] for item in pairs)
    pair_dir_mean = mean(item["abs_score_minus_0_5"] for item in pairs)
    reflective = max(pairs, key=lambda x: (x["abs_score_minus_0_5"] - 0.5 * x["seed_stddev"]))

    main_issue = "checkpoint updates too small"
    if quality["truncation_ratio_mean"] >= 0.50:
        main_issue = "truncation too high"
    elif quality["value_non_zero_fraction_mean"] <= 0.20:
        main_issue = "value supervision too weak"
    elif quality["checkpoint_eval_vs_previous_range"] >= 0.30:
        main_issue = "evaluation noise high"

    return {
        "main_issue": main_issue,
        "most_reflective_pair": reflective["pair"],
        "pair_abs_distance_mean": pair_dir_mean,
        "pair_seed_stddev_mean": pair_std_mean,
    }


def _signal_improvement(prev: RoundResult, curr_quality: dict, curr_pairs: list[dict]) -> tuple[bool, list[str]]:
    reasons = []
    if curr_quality["value_non_zero_fraction_mean"] - prev.quality["value_non_zero_fraction_mean"] >= 0.03:
        reasons.append("value_non_zero_fraction +>=0.03")
    if prev.quality["truncation_ratio_mean"] - curr_quality["truncation_ratio_mean"] >= 0.10:
        reasons.append("truncation_ratio -=0.10")
    if curr_quality["checkpoint_eval_vs_previous_range"] < prev.quality["checkpoint_eval_vs_previous_range"]:
        reasons.append("checkpoint_eval_vs_previous extreme range reduced")

    prev_std = mean(item["seed_stddev"] for item in prev.pair_results)
    curr_std = mean(item["seed_stddev"] for item in curr_pairs)
    if prev_std - curr_std >= 0.02:
        reasons.append("key-pair seed stddev -=0.02")

    return (len(reasons) > 0), reasons


def _direction_guardrail(prev: RoundResult, curr_pairs: list[dict]) -> tuple[bool, list[str]]:
    reasons = []
    degraded = False

    prev_10 = _find_pair(prev.pair_results, 1, 0)
    curr_10 = _find_pair(curr_pairs, 1, 0)
    if prev_10 and curr_10 and prev_10["candidate_score"] >= 0.55 and curr_10["candidate_score"] <= 0.45:
        degraded = True
        reasons.append("iter_001 vs iter_000 flipped from clear positive to clear negative")

    curr_later = _find_pair(curr_pairs, 3, 0)
    if curr_later and curr_later["candidate_score"] < 0.47:
        degraded = True
        reasons.append("later vs iter_000 significantly below 0.5")

    if all(item["abs_score_minus_0_5"] <= 0.03 for item in curr_pairs):
        degraded = True
        reasons.append("key-pair directionality collapsed near 0.5")

    return degraded, reasons


def _classify(prev: RoundResult | None, curr_quality: dict, curr_pairs: list[dict]) -> tuple[str, list[str]]:
    if prev is None:
        return "baseline", ["baseline round"]

    signal_better, signal_reasons = _signal_improvement(prev, curr_quality, curr_pairs)
    degraded, guardrail_reasons = _direction_guardrail(prev, curr_pairs)

    if signal_better and degraded:
        return "fake_improvement", signal_reasons + guardrail_reasons
    if signal_better and not degraded:
        return "true_improvement", signal_reasons
    if degraded:
        return "no_improvement", guardrail_reasons
    return "no_improvement", ["no signal-level threshold met"]


def _next_config(prev_cfg: dict, diagnosis: dict) -> tuple[dict, list[str]]:
    cfg = deepcopy(prev_cfg)
    reasons = []

    issue = diagnosis["main_issue"]
    if issue == "truncation too high":
        cfg["max_moves"] = min(140, int(cfg["max_moves"]) + 20)
        cfg["terminal_enrichment_games"] = int(cfg["terminal_enrichment_games"]) + 2
        cfg["terminal_enrichment_max_moves"] = min(18, int(cfg["terminal_enrichment_max_moves"]) + 2)
        reasons.append("raise move horizon + terminal enrichment to reduce truncations")
    elif issue == "value supervision too weak":
        cfg["games_per_iter"] = int(cfg["games_per_iter"]) + 2
        cfg["epochs"] = min(4, int(cfg["epochs"]) + 1)
        reasons.append("increase training signal density for non-zero values")
    elif issue == "evaluation noise high":
        cfg["quick_eval_games"] = int(cfg["quick_eval_games"]) + 2
        cfg["checkpoint_eval_games"] = int(cfg["checkpoint_eval_games"]) + 2
        reasons.append("increase eval games to reduce variance")
    else:
        cfg["checkpoint_eval_games"] = int(cfg["checkpoint_eval_games"]) + 2
        cfg["checkpoint_eval_max_moves"] = min(120, int(cfg["checkpoint_eval_max_moves"]) + 10)
        reasons.append("increase checkpoint eval sensitivity for small updates")

    return {k: v for k, v in cfg.items() if k in ALLOWED_TRAIN_KEYS}, reasons


def _train_round(run_dir: Path, cfg: dict, seed: int) -> dict:
    out = run_dir / "train"
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
        str(out),
    ]
    _run_cmd(cmd)
    return _load_json(out / "train_summary.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Unattended pure-RL closed-loop experiment with frozen key-pair checks")
    parser.add_argument("--min-runs", type=int, default=3)
    parser.add_argument("--max-runs", type=int, default=6)
    parser.add_argument("--seed", type=int, default=20260324)
    parser.add_argument("--out-root", default="")
    args = parser.parse_args()

    if args.min_runs < 3:
        raise ValueError("--min-runs must be >= 3")
    if args.max_runs > 6:
        raise ValueError("--max-runs must be <= 6")

    if args.out_root:
        root = Path(args.out_root)
    else:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        root = Path("artifacts") / f"local_pure_rl_closed_loop_{ts}"
    root.mkdir(parents=True, exist_ok=True)

    config = {
        "iterations": 4,
        "games_per_iter": 10,
        "max_moves": 80,
        "terminal_enrichment_games": 4,
        "terminal_enrichment_max_moves": 8,
        "epochs": 2,
        "batch_size": 64,
        "quick_eval_games": 6,
        "checkpoint_eval_games": 6,
        "checkpoint_eval_max_moves": 80,
    }

    rounds: list[RoundResult] = []
    no_true_improve_streak = 0
    fake_improve_streak = 0
    stop_reason = "max_runs_reached"

    for run_id in range(args.max_runs):
        run_name = "baseline" if run_id == 0 else f"adjust_round_{run_id}"
        run_dir = root / run_name
        summary = _train_round(run_dir, config, args.seed + run_id * 100)
        quality = _quality_from_summary(summary)
        iterations = [item["iteration"] for item in quality["per_iteration"]]
        panel = _build_panel_for_run(iterations)
        pair_results = [_eval_pair(run_dir, run_dir / "train" / "checkpoints", cand, base) for cand, base in panel]
        diagnosis = _diagnose(quality, pair_results)

        prev = rounds[-1] if rounds else None
        classification, rationale = _classify(prev, quality, pair_results)

        if classification == "true_improvement":
            no_true_improve_streak = 0
            fake_improve_streak = 0
        elif classification == "fake_improvement":
            no_true_improve_streak += 1
            fake_improve_streak += 1
        else:
            no_true_improve_streak += 1
            fake_improve_streak = 0

        next_cfg, adj_reason = _next_config(config, diagnosis)
        rounds.append(
            RoundResult(
                run_id=run_id,
                run_name=run_name,
                config=deepcopy(config),
                quality=quality,
                pair_results=pair_results,
                diagnosis=diagnosis,
                classification=classification,
                rationale=rationale,
                next_adjustment_reason=adj_reason,
            )
        )

        # Early stop checks, only after minimum runs.
        if len(rounds) >= args.min_runs:
            if no_true_improve_streak >= 2:
                stop_reason = "two_consecutive_runs_without_true_improvement"
                break
            if fake_improve_streak >= 2:
                stop_reason = "two_consecutive_fake_improvements"
                break
            if len(rounds) >= 4 and rounds[-1].classification == "true_improvement" and rounds[-2].classification == "true_improvement":
                stop_reason = "stable_better_config_confirmed"
                break

        config = next_cfg

    report = {
        "experiment_schema_version": "pure_rl_closed_loop_v1",
        "frozen_protocol": deepcopy(FROZEN_PROTOCOL),
        "constraints": {
            "style_disabled": True,
            "external_engine_disabled": True,
            "training_keys_adjustable_only": sorted(ALLOWED_TRAIN_KEYS),
            "key_pair_panel_template": [list(p) for p in PANEL_TEMPLATE],
        },
        "stop_reason": stop_reason,
        "runs": [
            {
                "run_id": item.run_id,
                "run_name": item.run_name,
                "config": item.config,
                "quality": item.quality,
                "pair_results": item.pair_results,
                "diagnosis": item.diagnosis,
                "classification": item.classification,
                "rationale": item.rationale,
                "next_adjustment_reason": item.next_adjustment_reason,
            }
            for item in rounds
        ],
        "total_runs": len(rounds),
        "artifact_root": str(root),
    }

    out_file = root / "closed_loop_report.json"
    out_file.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
