from __future__ import annotations

import json
from pathlib import Path

from scripts.summarize_route_sweep_progress import summarize


def _write_run(
    root: Path,
    run_name: str,
    *,
    anchors: dict[int, float],
    key_panel: dict[tuple[int, int], float],
    value_non_zero_fraction: float,
    natural_terminations: int,
    step_cap_truncations: int,
) -> None:
    run_dir = root / run_name
    benchmark_dir = run_dir / "benchmark_start_sanity"
    benchmark_dir.mkdir(parents=True)

    for cand, score in anchors.items():
        payload = {"aggregate": {"candidate_score": score}}
        (benchmark_dir / f"iter_{cand:03d}_vs_iter_000.json").write_text(json.dumps(payload))

    for (cand, base), score in key_panel.items():
        payload = {"aggregate": {"candidate_score": score}}
        (benchmark_dir / f"iter_{cand:03d}_vs_iter_{base:03d}.json").write_text(json.dumps(payload))

    train_dir = run_dir / "train"
    train_dir.mkdir(parents=True)
    train_summary = {
        "iterations": [
            {
                "iteration": 0,
                "value_non_zero_fraction": value_non_zero_fraction,
                "natural_terminations": natural_terminations,
                "step_cap_truncations": step_cap_truncations,
            },
            {
                "iteration": 1,
                "value_non_zero_fraction": value_non_zero_fraction,
                "natural_terminations": natural_terminations,
                "step_cap_truncations": step_cap_truncations,
            },
        ]
    }
    (train_dir / "train_summary.json").write_text(json.dumps(train_summary))


def test_summarize_classification_and_route_status(tmp_path: Path) -> None:
    _write_run(
        tmp_path,
        "run_000_endgame_density_first_r1",
        anchors={1: 0.45, 2: 0.46, 3: 0.47},
        key_panel={(1, 0): 0.45, (3, 0): 0.47, (2, 1): 0.48},
        value_non_zero_fraction=0.20,
        natural_terminations=6,
        step_cap_truncations=6,
    )
    _write_run(
        tmp_path,
        "run_001_endgame_density_first_r2",
        anchors={1: 0.64, 2: 0.65, 3: 0.66},
        key_panel={(1, 0): 0.64, (3, 0): 0.66, (2, 1): 0.55},
        value_non_zero_fraction=0.24,
        natural_terminations=8,
        step_cap_truncations=4,
    )

    summary = summarize(tmp_path)
    assert summary["found_feasible_anchor"] is True
    assert summary["core_anchor_interval"] == [0.47, 0.66]

    first_run = summary["runs"][0]
    assert first_run["classification"] == "no_improvement"
    assert first_run["route_status"] == "淘汰"

    second_run = summary["runs"][1]
    assert second_run["classification"] == "true_improvement"
    assert second_run["route_status"] == "继续深入"


def test_summarize_detects_fake_improvement_and_elimination(tmp_path: Path) -> None:
    _write_run(
        tmp_path,
        "run_000_directionality_repair_first_r1",
        anchors={1: 0.54, 3: 0.56},
        key_panel={(1, 0): 0.54, (3, 0): 0.56, (2, 1): 0.57},
        value_non_zero_fraction=0.20,
        natural_terminations=7,
        step_cap_truncations=5,
    )
    _write_run(
        tmp_path,
        "run_001_directionality_repair_first_r2",
        anchors={1: 0.44, 3: 0.45},
        key_panel={(1, 0): 0.44, (3, 0): 0.45, (2, 1): 0.48},
        value_non_zero_fraction=0.24,
        natural_terminations=8,
        step_cap_truncations=3,
    )

    summary = summarize(tmp_path)

    second_run = summary["runs"][1]
    assert second_run["classification"] == "fake_improvement"
    assert second_run["route_status"] == "淘汰"
    assert summary["eliminated_families"][0]["route_family"] == "directionality_repair_first"
