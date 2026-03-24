from __future__ import annotations

from scripts.build_systematic_benchmark_pairs import build_pair_plan


def test_build_pair_plan_has_required_coverage() -> None:
    train_summary = {
        "iterations": [
            {"iteration": 0, "natural_terminations": 10, "step_cap_truncations": 2, "value_non_zero_fraction": 0.3},
            {"iteration": 1, "natural_terminations": 8, "step_cap_truncations": 4, "value_non_zero_fraction": 0.25},
            {"iteration": 2, "natural_terminations": 7, "step_cap_truncations": 5, "value_non_zero_fraction": 0.2},
            {"iteration": 3, "natural_terminations": 2, "step_cap_truncations": 10, "value_non_zero_fraction": 0.1},
            {"iteration": 4, "natural_terminations": 1, "step_cap_truncations": 11, "value_non_zero_fraction": 0.08},
        ]
    }

    plan = build_pair_plan(train_summary)

    assert plan["num_checkpoints"] == 5
    assert plan["pair_counts_by_kind"]["adjacent"] == 4
    assert plan["pair_counts_by_kind"]["vs_iter000"] == 3
    assert plan["pair_counts_by_kind"]["large_span"] >= 3
    assert 3 in plan["anomaly_iterations"]
    assert 4 in plan["anomaly_iterations"]

    pairs = {(row["candidate_iter"], row["baseline_iter"], row["kind"]) for row in plan["pairs"]}
    assert (1, 0, "adjacent") in pairs
    assert (4, 0, "vs_iter000") in pairs
    assert (4, 1, "large_span") in pairs


def test_build_pair_plan_deduplicates_pairs() -> None:
    train_summary = {
        "iterations": [
            {"iteration": 0, "natural_terminations": 5, "step_cap_truncations": 0, "value_non_zero_fraction": 0.4},
            {"iteration": 1, "natural_terminations": 5, "step_cap_truncations": 0, "value_non_zero_fraction": 0.4},
            {"iteration": 2, "natural_terminations": 5, "step_cap_truncations": 0, "value_non_zero_fraction": 0.4},
        ]
    }
    plan = build_pair_plan(train_summary)
    unique_pairs = {(row["candidate_iter"], row["baseline_iter"]) for row in plan["pairs"]}
    assert len(unique_pairs) == len(plan["pairs"])
