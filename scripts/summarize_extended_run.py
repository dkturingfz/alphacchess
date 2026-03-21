#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.versions import VERSION_METADATA


REPLAY_FIELDS = [
    "total_games",
    "natural_terminations",
    "step_cap_truncations",
    "result_counts",
    "value_mean",
    "value_non_zero_fraction",
    "value_positive_count",
    "value_zero_count",
    "value_negative_count",
]

DEFAULT_THRESHOLDS = {
    "min_non_zero_value_fraction": 0.02,
    "caution_non_zero_value_fraction": 0.01,
    "max_truncation_rate": 0.60,
    "caution_truncation_rate": 0.75,
    "min_natural_termination_ratio": 0.90,
    "caution_natural_termination_ratio": 0.75,
    "min_checkpoint_eval_ratio": 0.75,
    "caution_checkpoint_eval_ratio": 0.50,
    "min_iterations": 3,
}


def _require_fields(iter_payload: dict, fields: list[str], iteration: int) -> None:
    missing = [field for field in fields if field not in iter_payload]
    if missing:
        raise ValueError(f"iteration={iteration} missing required fields: {missing}")


def _flatten_checkpoint_eval(iteration: int, payload: dict | None, baseline_kind: str) -> dict | None:
    if not payload:
        return None
    return {
        "iteration": iteration,
        "baseline_kind": baseline_kind,
        "evaluation_type": payload.get("evaluation_type"),
        "games": payload.get("games", 0),
        "candidate_wins": payload.get("candidate_wins", 0),
        "baseline_wins": payload.get("baseline_wins", 0),
        "draws": payload.get("draws", 0),
        "candidate_score": payload.get("candidate_score"),
        "candidate_checkpoint": payload.get("candidate_checkpoint"),
        "baseline_checkpoint": payload.get("baseline_checkpoint"),
    }


def _grade_check(value: float, pass_cutoff: float, caution_cutoff: float, higher_is_better: bool = True) -> str:
    if higher_is_better:
        if value >= pass_cutoff:
            return "pass"
        if value >= caution_cutoff:
            return "caution"
        return "fail"
    if value <= pass_cutoff:
        return "pass"
    if value <= caution_cutoff:
        return "caution"
    return "fail"


def _grade_readiness(checks: dict) -> str:
    levels = [checks[name]["status"] for name in checks]
    if any(level == "fail" for level in levels):
        return "fail"
    if any(level == "caution" for level in levels):
        return "caution"
    return "pass"


def summarize_extended_run(train_summary: dict, train_summary_path: str, thresholds: dict | None = None) -> dict:
    thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    iterations = train_summary.get("iterations", [])
    replay_quality_trend = []
    checkpoint_progress_trend = []

    for iter_payload in iterations:
        iteration = int(iter_payload.get("iteration", -1))
        _require_fields(iter_payload, REPLAY_FIELDS, iteration)

        replay_quality_trend.append({"iteration": iteration, **{field: iter_payload[field] for field in REPLAY_FIELDS}})

        vs_previous = _flatten_checkpoint_eval(iteration, iter_payload.get("checkpoint_eval_vs_previous"), "previous")
        if vs_previous:
            checkpoint_progress_trend.append(vs_previous)

        vs_baseline = _flatten_checkpoint_eval(
            iteration,
            iter_payload.get("checkpoint_eval_vs_fixed_baseline"),
            "fixed_baseline",
        )
        if vs_baseline:
            checkpoint_progress_trend.append(vs_baseline)

    non_zero_fractions = [row["value_non_zero_fraction"] for row in replay_quality_trend]
    total_games = [row["total_games"] for row in replay_quality_trend]
    truncation_rates = [
        (row["step_cap_truncations"] / row["total_games"]) if row["total_games"] else 0.0 for row in replay_quality_trend
    ]

    aggregate = {
        "iterations": len(replay_quality_trend),
        "total_games": sum(total_games),
        "min_value_non_zero_fraction": min(non_zero_fractions) if non_zero_fractions else 0.0,
        "max_value_non_zero_fraction": max(non_zero_fractions) if non_zero_fractions else 0.0,
        "avg_value_non_zero_fraction": (
            sum(non_zero_fractions) / len(non_zero_fractions) if non_zero_fractions else 0.0
        ),
        "max_step_cap_truncation_rate": max(truncation_rates) if truncation_rates else 0.0,
        "avg_step_cap_truncation_rate": sum(truncation_rates) / len(truncation_rates) if truncation_rates else 0.0,
        "iterations_with_natural_terminations": sum(1 for row in replay_quality_trend if row["natural_terminations"] > 0),
        "iterations_with_checkpoint_eval_vs_previous": sum(
            1 for row in checkpoint_progress_trend if row["baseline_kind"] == "previous"
        ),
    }

    iteration_count = max(aggregate["iterations"], 1)
    natural_termination_ratio = aggregate["iterations_with_natural_terminations"] / iteration_count
    checkpoint_eval_ratio = aggregate["iterations_with_checkpoint_eval_vs_previous"] / iteration_count

    readiness_checks = {
        "non_zero_value_supervision": {
            "value": aggregate["min_value_non_zero_fraction"],
            "status": _grade_check(
                aggregate["min_value_non_zero_fraction"],
                thresholds["min_non_zero_value_fraction"],
                thresholds["caution_non_zero_value_fraction"],
                higher_is_better=True,
            ),
            "pass_threshold": thresholds["min_non_zero_value_fraction"],
            "caution_threshold": thresholds["caution_non_zero_value_fraction"],
        },
        "truncation_control": {
            "value": aggregate["max_step_cap_truncation_rate"],
            "status": _grade_check(
                aggregate["max_step_cap_truncation_rate"],
                thresholds["max_truncation_rate"],
                thresholds["caution_truncation_rate"],
                higher_is_better=False,
            ),
            "pass_threshold": thresholds["max_truncation_rate"],
            "caution_threshold": thresholds["caution_truncation_rate"],
        },
        "natural_termination_visibility": {
            "value": natural_termination_ratio,
            "status": _grade_check(
                natural_termination_ratio,
                thresholds["min_natural_termination_ratio"],
                thresholds["caution_natural_termination_ratio"],
                higher_is_better=True,
            ),
            "pass_threshold": thresholds["min_natural_termination_ratio"],
            "caution_threshold": thresholds["caution_natural_termination_ratio"],
        },
        "checkpoint_progress_visibility": {
            "value": checkpoint_eval_ratio,
            "status": _grade_check(
                checkpoint_eval_ratio,
                thresholds["min_checkpoint_eval_ratio"],
                thresholds["caution_checkpoint_eval_ratio"],
                higher_is_better=True,
            ),
            "pass_threshold": thresholds["min_checkpoint_eval_ratio"],
            "caution_threshold": thresholds["caution_checkpoint_eval_ratio"],
        },
        "sufficient_iterations": {
            "value": aggregate["iterations"],
            "status": "pass" if aggregate["iterations"] >= thresholds["min_iterations"] else "caution",
            "pass_threshold": thresholds["min_iterations"],
            "caution_threshold": max(1, thresholds["min_iterations"] - 1),
        },
    }

    readiness_grade = _grade_readiness(readiness_checks)
    readiness = {
        "replay_quality_healthy": readiness_checks["truncation_control"]["status"] != "fail"
        and readiness_checks["natural_termination_visibility"]["status"] != "fail",
        "non_zero_value_supervision_present": readiness_checks["non_zero_value_supervision"]["status"] != "fail",
        "checkpoint_progress_visible": readiness_checks["checkpoint_progress_visibility"]["status"] != "fail",
        "readiness_grade": readiness_grade,
        "checks": readiness_checks,
        "thresholds": thresholds,
    }
    readiness["ready_for_next_stage"] = readiness_grade == "pass"

    return {
        "metadata": dict(VERSION_METADATA),
        "phase": "phase2_1_extended_run",
        "train_summary_path": train_summary_path,
        "final_checkpoint": train_summary.get("final_checkpoint"),
        "replay_quality_trend": replay_quality_trend,
        "checkpoint_progress_trend": checkpoint_progress_trend,
        "aggregate": aggregate,
        "readiness": readiness,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Summarize multi-iteration phase2.1 extended pure-RL run")
    ap.add_argument("--train-summary", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    path = Path(args.train_summary)
    payload = json.loads(path.read_text())
    summary = summarize_extended_run(payload, str(path))
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
