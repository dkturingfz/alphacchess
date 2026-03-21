import json
import subprocess
import sys


def _run_small_train(tmp_path):
    out_dir = tmp_path / "extended"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/train_selfplay.py",
            "--iterations",
            "3",
            "--games-per-iter",
            "4",
            "--terminal-enrichment-games",
            "2",
            "--terminal-enrichment-max-moves",
            "4",
            "--epochs",
            "1",
            "--batch-size",
            "32",
            "--quick-eval-games",
            "4",
            "--checkpoint-eval-games",
            "4",
            "--seed",
            "13",
            "--out-dir",
            str(out_dir),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    summary = json.loads(proc.stdout)
    return out_dir, summary


def test_multi_iteration_train_summary_retains_required_replay_quality_fields(tmp_path):
    _, summary = _run_small_train(tmp_path)
    assert len(summary["iterations"]) == 3

    required = [
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

    for row in summary["iterations"]:
        for key in required:
            assert key in row
        assert row["natural_terminations"] + row["step_cap_truncations"] == row["total_games"]


def test_checkpoint_comparison_stays_structured_across_iterations(tmp_path):
    _, summary = _run_small_train(tmp_path)

    for row in summary["iterations"]:
        eval_payload = row.get("checkpoint_eval_vs_previous")
        if row["iteration"] == 0:
            assert eval_payload is None
            continue

        assert eval_payload is not None
        assert eval_payload["evaluation_type"] == "candidate_vs_previous_checkpoint"
        assert eval_payload["games"] == 4
        assert eval_payload["candidate_wins"] + eval_payload["baseline_wins"] + eval_payload["draws"] == 4
        assert "candidate_score" in eval_payload


def test_non_zero_value_supervision_metrics_exposed_through_extended_summary(tmp_path):
    out_dir, summary = _run_small_train(tmp_path)
    train_summary = out_dir / "train_summary.json"
    assert train_summary.exists()

    summarized = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_extended_run.py",
            "--train-summary",
            str(train_summary),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(summarized.stdout)

    assert payload["aggregate"]["iterations"] == len(summary["iterations"])
    assert payload["aggregate"]["min_value_non_zero_fraction"] > 0.0
    assert payload["readiness"]["non_zero_value_supervision_present"] is True
    assert len(payload["replay_quality_trend"]) == len(summary["iterations"])
