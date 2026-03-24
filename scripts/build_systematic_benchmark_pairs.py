#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FROZEN_PROTOCOL = {
    "start_fens_file": "data/benchmark_positions/samples/benchmark_start_fens_sample.txt",
    "max_start_positions": 8,
    "games_per_start": 4,
    "max_moves": 60,
    "seeds": [17, 29, 41, 53],
}


def _iter_stats(train_summary: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = train_summary.get("iterations", [])
    return {int(row["iteration"]): row for row in rows}


def _add_pair(
    pairs: list[dict[str, Any]],
    seen: set[tuple[int, int]],
    candidate: int,
    baseline: int,
    reason: str,
    kind: str,
) -> None:
    if candidate <= baseline:
        return
    key = (candidate, baseline)
    if key in seen:
        return
    seen.add(key)
    pairs.append(
        {
            "candidate_iter": candidate,
            "baseline_iter": baseline,
            "kind": kind,
            "reason": reason,
        }
    )


def build_pair_plan(train_summary: dict[str, Any]) -> dict[str, Any]:
    stats = _iter_stats(train_summary)
    if not stats:
        raise ValueError("train_summary contains no iterations")

    iteration_ids = sorted(stats)
    max_iter = iteration_ids[-1]
    pairs: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()

    for cand in iteration_ids[1:]:
        _add_pair(
            pairs,
            seen,
            cand,
            cand - 1,
            reason="adjacent_pair_full_coverage",
            kind="adjacent",
        )

    for cand in iteration_ids[1:]:
        _add_pair(
            pairs,
            seen,
            cand,
            0,
            reason="candidate_vs_iter000_full_coverage",
            kind="vs_iter000",
        )

    for cand in iteration_ids[2:]:
        _add_pair(
            pairs,
            seen,
            cand,
            cand - 2,
            reason="larger_span_stride2",
            kind="large_span",
        )
    for cand in iteration_ids[3:]:
        _add_pair(
            pairs,
            seen,
            cand,
            cand - 3,
            reason="larger_span_stride3",
            kind="large_span",
        )

    _add_pair(
        pairs,
        seen,
        max_iter,
        max_iter // 2,
        reason="latest_vs_midpoint_anchor",
        kind="large_span",
    )

    anomaly_iterations: list[int] = []
    for it in iteration_ids[1:]:
        row = stats[it]
        total = row.get("natural_terminations", 0) + row.get("step_cap_truncations", 0)
        trunc_ratio = (row.get("step_cap_truncations", 0) / total) if total else 0.0
        value_non_zero_fraction = float(row.get("value_non_zero_fraction", 0.0))
        if trunc_ratio >= 0.7 or value_non_zero_fraction <= 0.12:
            anomaly_iterations.append(it)
            _add_pair(
                pairs,
                seen,
                it,
                max(0, it - 4),
                reason="iteration_quality_anomaly_probe",
                kind="anomaly_probe",
            )

    pairs.sort(key=lambda row: (row["candidate_iter"], row["baseline_iter"]))
    kind_counts: dict[str, int] = {}
    for row in pairs:
        kind_counts[row["kind"]] = kind_counts.get(row["kind"], 0) + 1

    return {
        "plan_schema_version": "phase3_systematic_pair_plan_v1",
        "frozen_protocol": dict(FROZEN_PROTOCOL),
        "num_checkpoints": len(iteration_ids),
        "checkpoint_iterations": iteration_ids,
        "anomaly_iterations": anomaly_iterations,
        "pair_counts_by_kind": kind_counts,
        "pairs": pairs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic benchmark_start pair plan from train_summary")
    parser.add_argument("--train-summary", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    train_summary = json.loads(Path(args.train_summary).read_text())
    plan = build_pair_plan(train_summary)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, indent=2))
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
