import json
from pathlib import Path
import subprocess
import sys

from alphacchess.phase1_eval import evaluate_model_vs_model_on_start_fens
from alphacchess.phase1_model import PolicyValueNet


def test_checkpoint_comparison_script_outputs_structured_payload(tmp_path):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"

    b_model = PolicyValueNet.for_xiangqi_v1(seed=1)
    c_model = PolicyValueNet.for_xiangqi_v1(seed=2)
    b_model.capture_weight = 2.0
    c_model.capture_weight = 6.0

    metadata = {
        "action_encoding_version": "v1_8100_from_to",
        "observation_encoding_version": "v1_15planes",
        "dataset_schema_version": "v1",
        "rules_version": "v1_python_rules",
        "checkpoint_schema_version": "phase1_checkpoint_v1",
    }
    b_model.save_checkpoint(baseline, metadata)
    c_model.save_checkpoint(candidate, metadata)

    out = tmp_path / "eval.json"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/evaluate_checkpoints.py",
            "--candidate",
            str(candidate),
            "--baseline",
            str(baseline),
            "--games",
            "6",
            "--max-moves",
            "60",
            "--seed",
            "9",
            "--out",
            str(out),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["evaluation_type"] == "checkpoint_vs_checkpoint"
    assert payload["games"] == 6
    assert payload["candidate_wins"] + payload["baseline_wins"] + payload["draws"] == 6
    assert "candidate_score" in payload

    disk = json.loads(out.read_text())
    assert disk["candidate_checkpoint"] == str(candidate)
    assert disk["baseline_checkpoint"] == str(baseline)


def test_evaluate_model_vs_model_on_start_fens_smoke():
    baseline = PolicyValueNet.for_xiangqi_v1(seed=3)
    candidate = PolicyValueNet.for_xiangqi_v1(seed=4)
    fens = [
        "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
        "r1bakab1r/3c5/2n3nc1/p3p1p1p/9/2R6/P3P1P1P/2N1C2C1/9/2BAKABNR w",
    ]

    result = evaluate_model_vs_model_on_start_fens(
        candidate,
        baseline,
        start_fens=fens,
        games_per_start=2,
        max_moves=60,
        seed=11,
    )
    assert result.games == 4
    assert result.candidate_wins + result.baseline_wins + result.draws == 4


def test_benchmark_start_sanity_script_outputs_summary(tmp_path):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"

    b_model = PolicyValueNet.for_xiangqi_v1(seed=12)
    c_model = PolicyValueNet.for_xiangqi_v1(seed=13)
    metadata = {
        "action_encoding_version": "v1_8100_from_to",
        "observation_encoding_version": "v1_15planes",
        "dataset_schema_version": "v1",
        "rules_version": "v1_python_rules",
        "checkpoint_schema_version": "phase1_checkpoint_v1",
    }
    b_model.save_checkpoint(baseline, metadata)
    c_model.save_checkpoint(candidate, metadata)

    out = tmp_path / "sanity.json"
    fens_file = Path("data/benchmark_positions/samples/benchmark_start_fens_sample.txt")
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark_start_sanity.py",
            "--candidate",
            str(candidate),
            "--baseline",
            str(baseline),
            "--start-fens",
            str(fens_file),
            "--max-start-positions",
            "3",
            "--games-per-start",
            "2",
            "--max-moves",
            "50",
            "--seeds",
            "5",
            "--out",
            str(out),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["evaluation_type"] == "benchmark_start_checkpoint_sanity_v1"
    assert payload["start_positions_used"] == 3
    assert payload["aggregate"]["games"] == 6
    assert payload["aggregate"]["candidate_wins"] + payload["aggregate"]["baseline_wins"] + payload["aggregate"]["draws"] == 6

    disk = json.loads(out.read_text())
    assert disk["candidate_checkpoint"] == str(candidate)
    assert disk["baseline_checkpoint"] == str(baseline)


def test_benchmark_start_sanity_script_handles_quoted_seeds_and_creates_output_dir(tmp_path):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"

    b_model = PolicyValueNet.for_xiangqi_v1(seed=21)
    c_model = PolicyValueNet.for_xiangqi_v1(seed=22)
    metadata = {
        "action_encoding_version": "v1_8100_from_to",
        "observation_encoding_version": "v1_15planes",
        "dataset_schema_version": "v1",
        "rules_version": "v1_python_rules",
        "checkpoint_schema_version": "phase1_checkpoint_v1",
    }
    b_model.save_checkpoint(baseline, metadata)
    c_model.save_checkpoint(candidate, metadata)

    nested_out = tmp_path / "nested" / "results" / "sanity.json"
    fens_file = Path("data/benchmark_positions/samples/benchmark_start_fens_sample.txt")
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark_start_sanity.py",
            "--candidate",
            str(candidate),
            "--baseline",
            str(baseline),
            "--start-fens",
            str(fens_file),
            "--max-start-positions",
            "2",
            "--games-per-start",
            "1",
            "--max-moves",
            "40",
            "--seeds",
            '"5,7"',
            "--out",
            str(nested_out),
        ],
        check=True,
        text=True,
        capture_output=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["seeds"] == [5, 7]
    assert nested_out.exists()


def test_benchmark_start_sanity_script_missing_start_fens_has_clear_error(tmp_path):
    baseline = tmp_path / "baseline.json"
    candidate = tmp_path / "candidate.json"

    b_model = PolicyValueNet.for_xiangqi_v1(seed=31)
    c_model = PolicyValueNet.for_xiangqi_v1(seed=32)
    metadata = {
        "action_encoding_version": "v1_8100_from_to",
        "observation_encoding_version": "v1_15planes",
        "dataset_schema_version": "v1",
        "rules_version": "v1_python_rules",
        "checkpoint_schema_version": "phase1_checkpoint_v1",
    }
    b_model.save_checkpoint(baseline, metadata)
    c_model.save_checkpoint(candidate, metadata)

    missing_fens = tmp_path / "missing_start_fens.txt"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark_start_sanity.py",
            "--candidate",
            str(candidate),
            "--baseline",
            str(baseline),
            "--start-fens",
            str(missing_fens),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 2
    assert f"--start-fens file does not exist: {missing_fens}" in proc.stderr
