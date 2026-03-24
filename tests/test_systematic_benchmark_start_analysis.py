from __future__ import annotations

import json
from pathlib import Path

from scripts.systematic_benchmark_start_analysis import build_report


def _pair_payload(candidate_iter: int, baseline_iter: int, candidate_score: float) -> dict:
    return {
        "candidate_checkpoint": f"/tmp/iter_{candidate_iter:03d}.json",
        "baseline_checkpoint": f"/tmp/iter_{baseline_iter:03d}.json",
        "aggregate": {
            "games": 128,
            "games_expected": 128,
            "candidate_score": candidate_score,
            "candidate_score_stddev_across_seeds": 0.01,
            "candidate_score_min_across_seeds": candidate_score - 0.02,
            "candidate_score_max_across_seeds": candidate_score + 0.02,
        },
        "per_seed": [
            {"candidate_score": candidate_score - 0.01},
            {"candidate_score": candidate_score + 0.01},
        ],
    }


def test_build_report_pair_type_and_counts(tmp_path: Path) -> None:
    train_summary = {
        "iterations": [
            {
                "iteration": 0,
                "value_non_zero_fraction": 0.2,
                "natural_terminations": 6,
                "step_cap_truncations": 6,
                "checkpoint_eval_vs_previous": None,
            },
            {
                "iteration": 1,
                "value_non_zero_fraction": 0.25,
                "natural_terminations": 7,
                "step_cap_truncations": 5,
                "checkpoint_eval_vs_previous": {"candidate_score": 0.6},
            },
            {
                "iteration": 3,
                "value_non_zero_fraction": 0.1,
                "natural_terminations": 5,
                "step_cap_truncations": 7,
                "checkpoint_eval_vs_previous": {"candidate_score": 0.4},
            },
        ]
    }
    train_path = tmp_path / "train_summary.json"
    train_path.write_text(json.dumps(train_summary))

    pair_adj = tmp_path / "iter_001_vs_iter_000.json"
    pair_adj.write_text(json.dumps(_pair_payload(1, 0, 0.6)))

    pair_large = tmp_path / "iter_003_vs_iter_001.json"
    pair_large.write_text(json.dumps(_pair_payload(3, 1, 0.47)))

    report = build_report(train_path, [pair_adj, pair_large])

    assert report["num_checkpoints"] == 3
    assert report["num_pairs_total"] == 2
    assert report["pair_type_stats"]["adjacent"]["count"] == 1
    assert report["pair_type_stats"]["large_span"]["count"] == 1
