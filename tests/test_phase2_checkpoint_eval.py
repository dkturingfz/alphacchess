import json
import subprocess
import sys

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
