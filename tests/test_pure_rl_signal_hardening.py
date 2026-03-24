from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    path = Path("scripts/pure_rl_signal_hardening.py")
    spec = importlib.util.spec_from_file_location("pure_rl_signal_hardening", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_pair_panel_stable_core_pairs():
    mod = _load_module()
    summary = {"iterations": [{"iteration": i} for i in range(4)]}
    panel = mod._pair_panel_for_summary(summary)
    assert panel == [(1, 0), (3, 0), (3, 2)]


def test_diagnose_flags_low_directionality_and_low_nonzero():
    mod = _load_module()
    quality = {
        "avg_truncation_ratio": 0.55,
        "avg_value_non_zero_fraction": 0.18,
        "checkpoint_eval_vs_previous_range": 0.35,
    }
    pairs = [
        {"distance_from_50": 0.02, "seed_stddev": 0.05},
        {"distance_from_50": 0.04, "seed_stddev": 0.03},
        {"distance_from_50": 0.03, "seed_stddev": 0.04},
    ]
    d = mod._diagnose(quality, pairs)
    assert d["truncation_too_high"] is True
    assert d["value_non_zero_too_low"] is True
    assert d["checkpoint_eval_noisy"] is True
    assert d["pairs_lack_directionality"] is True


def test_improvement_matches_threshold_rule():
    mod = _load_module()

    prev = mod.RunMetrics(
        run_id=0,
        run_name="baseline",
        train_out_dir="x",
        config={},
        quality={"avg_truncation_ratio": 0.45, "avg_value_non_zero_fraction": 0.20},
        pairs=[],
        pair_panel=[[1, 0]],
        pair_abs_distance_mean=0.03,
        pair_seed_stddev_mean=0.06,
        improved=True,
        improvement_reasons=["baseline"],
        diagnosis={},
    )
    curr_quality = {"avg_truncation_ratio": 0.40, "avg_value_non_zero_fraction": 0.24}
    curr_pairs = [
        {"distance_from_50": 0.10, "seed_stddev": 0.03},
        {"distance_from_50": 0.08, "seed_stddev": 0.04},
    ]
    improved, reasons = mod._improvement(prev, curr_quality, curr_pairs)
    assert improved is True
    assert reasons
