import json
import subprocess
import sys

from alphacchess.phase1_model import PolicyValueNet
from alphacchess.phase1_selfplay import SelfPlayConfig, run_selfplay


def test_export_replay_stats_reports_required_phase2_fields(tmp_path):
    model = PolicyValueNet.for_xiangqi_v1(seed=5)
    replay, _ = run_selfplay(
        model,
        SelfPlayConfig(games=4, max_moves=80, terminal_enrichment_games=2, terminal_enrichment_max_moves=4),
        seed=5,
    )
    replay_path = tmp_path / "replay.json"
    replay.save(replay_path)

    proc = subprocess.run(
        [sys.executable, "scripts/export_replay_stats.py", "--replay", str(replay_path)],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(proc.stdout)

    required = [
        "num_games",
        "natural_terminations",
        "step_cap_truncations",
        "result_counts",
        "value_non_zero_fraction",
        "value_positive_count",
        "value_zero_count",
        "value_negative_count",
    ]
    for k in required:
        assert k in payload
    assert payload["num_games"] == 6
    assert payload["natural_terminations"] + payload["step_cap_truncations"] == 6
