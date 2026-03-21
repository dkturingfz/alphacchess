import json
import subprocess
import sys

from alphacchess.phase1_model import PolicyValueNet


def test_profile_rules_script_emits_hotspot_ranking(tmp_path):
    out = tmp_path / "profile.json"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/profile_rules.py",
            "--legal-iters",
            "10",
            "--clone-iters",
            "20",
            "--apply-iters",
            "10",
            "--top-n",
            "5",
            "--out",
            str(out),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["profile_schema_version"] == "phase3_profile_v1"
    assert payload["hotspot_ranking"]
    components = {row["component"] for row in payload["hotspot_ranking"]}
    assert {"legal_actions", "apply_action", "clone", "selfplay_loop"}.issubset(components)
    assert out.exists()


def test_summarize_extended_run_uses_stricter_readiness_grade(tmp_path):
    train_summary = {
        "metadata": {},
        "final_checkpoint": "ckpt_002",
        "iterations": [
            {
                "iteration": 0,
                "total_games": 10,
                "natural_terminations": 3,
                "step_cap_truncations": 7,
                "result_counts": {"win": 2, "loss": 1, "draw": 0, "truncated_draw": 7},
                "value_mean": 0.0,
                "value_non_zero_fraction": 0.03,
                "value_positive_count": 2,
                "value_zero_count": 8,
                "value_negative_count": 0,
                "checkpoint_eval_vs_previous": None,
                "checkpoint_eval_vs_fixed_baseline": None,
            },
            {
                "iteration": 1,
                "total_games": 10,
                "natural_terminations": 1,
                "step_cap_truncations": 9,
                "result_counts": {"win": 1, "loss": 0, "draw": 0, "truncated_draw": 9},
                "value_mean": 0.0,
                "value_non_zero_fraction": 0.012,
                "value_positive_count": 1,
                "value_zero_count": 9,
                "value_negative_count": 0,
                "checkpoint_eval_vs_previous": {"games": 2, "candidate_wins": 1, "baseline_wins": 1, "draws": 0},
                "checkpoint_eval_vs_fixed_baseline": None,
            },
            {
                "iteration": 2,
                "total_games": 10,
                "natural_terminations": 0,
                "step_cap_truncations": 10,
                "result_counts": {"win": 0, "loss": 0, "draw": 0, "truncated_draw": 10},
                "value_mean": 0.0,
                "value_non_zero_fraction": 0.005,
                "value_positive_count": 0,
                "value_zero_count": 10,
                "value_negative_count": 0,
                "checkpoint_eval_vs_previous": {"games": 2, "candidate_wins": 1, "baseline_wins": 0, "draws": 1},
                "checkpoint_eval_vs_fixed_baseline": None,
            },
        ],
    }
    summary_path = tmp_path / "train_summary.json"
    summary_path.write_text(json.dumps(train_summary))

    proc = subprocess.run(
        [sys.executable, "scripts/summarize_extended_run.py", "--train-summary", str(summary_path)],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["readiness"]["readiness_grade"] == "fail"
    assert payload["readiness"]["ready_for_next_stage"] is False
    assert "checks" in payload["readiness"]


def test_benchmark_dry_run_records_protocol_metadata(tmp_path):
    candidate = tmp_path / "candidate.json"
    model = PolicyValueNet.for_xiangqi_v1(seed=3)
    model.save_checkpoint(
        candidate,
        {
            "action_encoding_version": "v1_8100_from_to",
            "observation_encoding_version": "v1_15planes",
            "dataset_schema_version": "v1",
            "rules_version": "v1_python_rules",
            "checkpoint_schema_version": "phase1_checkpoint_v1",
            "iteration": "5",
        },
    )

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_vs_pikafish.py",
            "--checkpoint",
            str(candidate),
            "--benchmark-config",
            "configs/benchmark_pikafish_v1.yaml",
            "--engine-version",
            "pikafish-202603",
            "--seed",
            "137",
            "--dry-run",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["benchmark_config_name"] == "benchmark_pikafish_v1.yaml"
    assert payload["benchmark_config_hash"]
    assert payload["engine_name"] == "pikafish"
    assert payload["engine_version"] == "pikafish-202603"
    assert payload["checkpoint_id"] == "candidate:iter_5"
    assert payload["seed"] == 137


def test_strength_benchmark_and_style_eval_outputs_remain_separate(tmp_path):
    ckpt = tmp_path / "model.json"
    model = PolicyValueNet.for_xiangqi_v1(seed=9)
    model.save_checkpoint(
        ckpt,
        {
            "action_encoding_version": "v1_8100_from_to",
            "observation_encoding_version": "v1_15planes",
            "dataset_schema_version": "v1",
            "rules_version": "v1_python_rules",
            "checkpoint_schema_version": "phase1_checkpoint_v1",
        },
    )

    bench = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_vs_pikafish.py",
            "--checkpoint",
            str(ckpt),
            "--dry-run",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    bench_payload = json.loads(bench.stdout)
    assert "quality_zone" not in bench_payload
    assert bench_payload["benchmark_schema_version"] == "phase3_strength_benchmark_v1"

    style = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_style.py",
            "--checkpoint",
            str(ckpt),
            "--dataset",
            "data/style_demo/target_player_positions.jsonl",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    style_payload = json.loads(style.stdout)
    assert "benchmark_config_name" not in style_payload
    assert "quality_zone" in style_payload
