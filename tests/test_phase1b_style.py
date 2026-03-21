import json
import subprocess
import sys

from alphacchess.notation import iccs_to_action
from alphacchess.phase1_model import PolicyValueNet
from alphacchess.style_phase1b import (
    StylePositionSample,
    classify_style_quality,
    evaluate_style_samples,
    load_style_eval_config,
    load_style_position_samples,
    phase_of_ply,
)


def test_style_eval_reads_historical_positions_from_game_records(tmp_path):
    data = tmp_path / "games.jsonl"
    data.write_text(
        json.dumps(
            {
                "game_id": "g1",
                "initial_fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
                "moves_iccs": ["a3a4", "a6a5", "c3c4"],
            }
        )
        + "\n"
    )
    samples = load_style_position_samples(data)
    assert len(samples) == 3
    assert samples[0].ply == 1
    assert samples[1].ply == 2
    assert samples[2].ply == 3


def test_phase_split_and_thresholds_match_v1_protocol():
    cfg = load_style_eval_config("configs/style_eval_v1.yaml")
    assert phase_of_ply(1, cfg.phase_split) == "opening"
    assert phase_of_ply(20, cfg.phase_split) == "opening"
    assert phase_of_ply(21, cfg.phase_split) == "middlegame"
    assert phase_of_ply(60, cfg.phase_split) == "middlegame"
    assert phase_of_ply(61, cfg.phase_split) == "endgame"

    assert classify_style_quality(24.99, cfg.thresholds) == "unusable"
    assert classify_style_quality(25.0, cfg.thresholds) == "gray"
    assert classify_style_quality(34.99, cfg.thresholds) == "gray"
    assert classify_style_quality(35.0, cfg.thresholds) == "usable"
    assert classify_style_quality(40.0, cfg.thresholds) == "preferred"


class DummyModel:
    def __init__(self, top1_action: int, top2_action: int, top3_action: int):
        self.top_actions = [top1_action, top2_action, top3_action]

    def forward(self, obs_batch):
        logits = []
        for _ in obs_batch:
            row = [-1000.0] * 8100
            row[self.top_actions[0]] = 3.0
            row[self.top_actions[1]] = 2.0
            row[self.top_actions[2]] = 1.0
            logits.append(row)
        return logits, [0.0 for _ in obs_batch]


def test_top1_top3_metrics_computed_consistently():
    a1 = iccs_to_action("a3a4")
    a2 = iccs_to_action("c3c4")
    a3 = iccs_to_action("e3e4")

    samples = [
        StylePositionSample(
            fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
            move_iccs="a3a4",
            ply=1,
        ),
        StylePositionSample(
            fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
            move_iccs="c3c4",
            ply=22,
        ),
        StylePositionSample(
            fen="rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w",
            move_iccs="i3i4",
            ply=62,
        ),
    ]
    model = DummyModel(top1_action=a1, top2_action=a2, top3_action=a3)
    cfg = load_style_eval_config("configs/style_eval_v1.yaml")
    metrics = evaluate_style_samples(model, samples, cfg.phase_split)

    assert metrics["global"].sample_count == 3
    assert abs(metrics["global"].top1 - (100.0 / 3.0)) < 1e-6
    assert abs(metrics["global"].top3 - (200.0 / 3.0)) < 1e-6


def test_frozen_style_checkpoint_save_reload(tmp_path):
    ckpt = tmp_path / "style.json"
    model = PolicyValueNet.for_xiangqi_v1(seed=9)
    metadata = {
        "checkpoint_schema_version": "phase1b_style_reference_v1",
        "frozen_style_reference": "true",
    }
    model.save_checkpoint(ckpt, metadata)
    reloaded, reloaded_meta = PolicyValueNet.load_checkpoint(ckpt)
    assert reloaded_meta["frozen_style_reference"] == "true"
    assert reloaded_meta["checkpoint_schema_version"] == "phase1b_style_reference_v1"
    logits, _ = reloaded.forward([[[[0 for _ in range(9)] for _ in range(10)] for _ in range(15)]])
    assert len(logits[0]) == 8100


def test_gray_zone_recovery_script_runs_from_prior_checkpoint_and_config(tmp_path):
    ckpt = tmp_path / "initial_style.json"
    train_out = subprocess.run(
        [
            sys.executable,
            "scripts/train_style_reference.py",
            "--target-dataset",
            "data/style_demo/target_player_positions.jsonl",
            "--epochs",
            "1",
            "--out-checkpoint",
            str(ckpt),
            "--out-report",
            str(tmp_path / "train_report.json"),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "checkpoint" in train_out.stdout

    rec = subprocess.run(
        [
            sys.executable,
            "scripts/run_style_recovery.py",
            "--checkpoint",
            str(ckpt),
            "--target-dataset",
            "data/style_demo/target_player_positions.jsonl",
            "--generic-pretrain-dataset",
            "data/style_demo/generic_positions.jsonl",
            "--config",
            "configs/style_eval_v1.yaml",
            "--out-dir",
            str(tmp_path / "recovery"),
            "--force-recovery",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(rec.stdout)
    assert "steps" in payload
    assert payload["steps"][0]["step"] == "verify_evaluation_and_data_integrity"
