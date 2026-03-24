#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = sum((x - mx) ** 2 for x in xs)
    den_y = sum((y - my) ** 2 for y in ys)
    den = (den_x * den_y) ** 0.5
    if den == 0:
        return None
    return num / den


def _pair_type(candidate_iter: int, baseline_iter: int) -> str:
    span = candidate_iter - baseline_iter
    if span == 1:
        return "adjacent"
    if baseline_iter == 0:
        return "vs_iter000"
    return "large_span"


def _load_pairs(pair_files: list[Path], iter_stats: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: dict[tuple[int, int], dict[str, Any]] = {}
    for pair_file in pair_files:
        payload = json.loads(pair_file.read_text())
        candidate_iter = int(Path(payload["candidate_checkpoint"]).stem.split("_")[1])
        baseline_iter = int(Path(payload["baseline_checkpoint"]).stem.split("_")[1])
        agg = payload["aggregate"]
        row: dict[str, Any] = {
            "file": str(pair_file),
            "candidate_iter": candidate_iter,
            "baseline_iter": baseline_iter,
            "span": candidate_iter - baseline_iter,
            "type": _pair_type(candidate_iter, baseline_iter),
            "candidate_score": agg["candidate_score"],
            "seed_stddev": agg["candidate_score_stddev_across_seeds"],
            "seed_min": agg["candidate_score_min_across_seeds"],
            "seed_max": agg["candidate_score_max_across_seeds"],
            "games": agg["games"],
            "games_expected": agg["games_expected"],
            "per_seed": [item["candidate_score"] for item in payload["per_seed"]],
        }
        row["distance_from_50"] = abs(row["candidate_score"] - 0.5)

        cand = iter_stats[candidate_iter]
        row["cand_value_non_zero_fraction"] = cand["value_non_zero_fraction"]
        total = cand["natural_terminations"] + cand["step_cap_truncations"]
        row["cand_truncation_ratio"] = (cand["step_cap_truncations"] / total) if total else 0.0

        if row["type"] == "adjacent" and cand.get("checkpoint_eval_vs_previous"):
            train_prev_score = cand["checkpoint_eval_vs_previous"]["candidate_score"]
            row["train_prev_score"] = train_prev_score
            row["agreement_with_train_prev"] = ((row["candidate_score"] - 0.5) * (train_prev_score - 0.5)) > 0

        key = (candidate_iter, baseline_iter)
        if key not in rows or "followup" in str(pair_file):
            rows[key] = row
    return list(rows.values())


def build_report(train_summary_path: Path, pair_files: list[Path]) -> dict[str, Any]:
    train_summary = json.loads(train_summary_path.read_text())
    iter_stats = {item["iteration"]: item for item in train_summary["iterations"]}

    rows = _load_pairs(pair_files, iter_stats)
    rows_sorted = sorted(rows, key=lambda item: item["distance_from_50"], reverse=True)
    rows_near_50 = sorted(rows, key=lambda item: item["distance_from_50"])

    by_type: dict[str, dict[str, float | int]] = {}
    for kind in sorted(set(item["type"] for item in rows)):
        vals = [item["distance_from_50"] for item in rows if item["type"] == kind]
        by_type[kind] = {
            "count": len(vals),
            "mean_abs_distance_from_50": (sum(vals) / len(vals)) if vals else 0.0,
            "max_abs_distance_from_50": max(vals) if vals else 0.0,
        }

    adjacent = [item for item in rows if item["type"] == "adjacent" and "agreement_with_train_prev" in item]
    agree_count = sum(1 for item in adjacent if item["agreement_with_train_prev"])

    cor_v = _corr([item["cand_value_non_zero_fraction"] for item in rows], [item["distance_from_50"] for item in rows])
    cor_t = _corr([item["cand_truncation_ratio"] for item in rows], [item["distance_from_50"] for item in rows])

    return {
        "num_checkpoints": len(iter_stats),
        "num_pairs_total": len(rows),
        "pair_type_stats": by_type,
        "pair_top_directional": rows_sorted[:8],
        "pair_near_50": rows_near_50[:8],
        "adjacent_vs_train_prev_agreement": {
            "count": len(adjacent),
            "agree_count": agree_count,
            "agree_rate": (agree_count / len(adjacent)) if adjacent else None,
        },
        "correlation": {
            "cand_value_non_zero_fraction_vs_pair_directionality": cor_v,
            "cand_truncation_ratio_vs_pair_directionality": cor_t,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize systematic benchmark_start pair results")
    parser.add_argument("--train-summary", required=True)
    parser.add_argument("--pair-glob", action="append", required=True, help="Glob for pair JSONs; can be repeated")
    parser.add_argument("--out-json", required=True)
    args = parser.parse_args()

    pair_files: list[Path] = []
    for pattern in args.pair_glob:
        pair_files.extend(sorted(Path().glob(pattern)))
    if not pair_files:
        raise SystemExit("No pair files matched --pair-glob")

    report = build_report(Path(args.train_summary), pair_files)
    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
