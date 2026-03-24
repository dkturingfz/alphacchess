from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    path = Path("scripts/pure_rl_closed_loop_experiment.py")
    spec = importlib.util.spec_from_file_location("pure_rl_closed_loop_experiment", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_panel_prefers_fixed_template_when_available():
    mod = _load_module()
    panel = mod._build_panel_for_run([0, 1, 2, 3])
    assert panel == [(1, 0), (3, 0), (2, 1)]


def test_direction_guardrail_detects_clear_flip():
    mod = _load_module()
    prev = mod.RoundResult(
        run_id=0,
        run_name="baseline",
        config={},
        quality={},
        pair_results=[
            {"pair": [1, 0], "candidate_score": 0.60, "seed_stddev": 0.04, "abs_score_minus_0_5": 0.10},
            {"pair": [3, 0], "candidate_score": 0.57, "seed_stddev": 0.05, "abs_score_minus_0_5": 0.07},
            {"pair": [2, 1], "candidate_score": 0.55, "seed_stddev": 0.05, "abs_score_minus_0_5": 0.05},
        ],
        diagnosis={},
        classification="baseline",
        rationale=[],
        next_adjustment_reason=[],
    )
    curr_pairs = [
        {"pair": [1, 0], "candidate_score": 0.43, "seed_stddev": 0.03, "abs_score_minus_0_5": 0.07},
        {"pair": [3, 0], "candidate_score": 0.45, "seed_stddev": 0.03, "abs_score_minus_0_5": 0.05},
        {"pair": [2, 1], "candidate_score": 0.46, "seed_stddev": 0.03, "abs_score_minus_0_5": 0.04},
    ]
    degraded, reasons = mod._direction_guardrail(prev, curr_pairs)
    assert degraded is True
    assert reasons


def test_classify_fake_improvement_when_signal_better_but_direction_degrades():
    mod = _load_module()
    prev = mod.RoundResult(
        run_id=0,
        run_name="baseline",
        config={},
        quality={
            "value_non_zero_fraction_mean": 0.20,
            "truncation_ratio_mean": 0.50,
            "checkpoint_eval_vs_previous_range": 0.30,
        },
        pair_results=[
            {"pair": [1, 0], "candidate_score": 0.58, "seed_stddev": 0.07, "abs_score_minus_0_5": 0.08},
            {"pair": [3, 0], "candidate_score": 0.56, "seed_stddev": 0.06, "abs_score_minus_0_5": 0.06},
            {"pair": [2, 1], "candidate_score": 0.55, "seed_stddev": 0.05, "abs_score_minus_0_5": 0.05},
        ],
        diagnosis={},
        classification="baseline",
        rationale=[],
        next_adjustment_reason=[],
    )
    quality = {
        "value_non_zero_fraction_mean": 0.24,
        "truncation_ratio_mean": 0.48,
        "checkpoint_eval_vs_previous_range": 0.20,
    }
    pairs = [
        {"pair": [1, 0], "candidate_score": 0.44, "seed_stddev": 0.04, "abs_score_minus_0_5": 0.06},
        {"pair": [3, 0], "candidate_score": 0.46, "seed_stddev": 0.04, "abs_score_minus_0_5": 0.04},
        {"pair": [2, 1], "candidate_score": 0.47, "seed_stddev": 0.03, "abs_score_minus_0_5": 0.03},
    ]
    category, reasons = mod._classify(prev, quality, pairs)
    assert category == "fake_improvement"
    assert reasons
