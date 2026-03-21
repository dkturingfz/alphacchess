from alphacchess.phase1_model import PolicyValueNet
from alphacchess.phase1_selfplay import SelfPlayConfig, run_selfplay
from alphacchess.xiangqi_game import XiangqiGame, XiangqiState


def test_selfplay_propagates_terminal_returns_into_value_targets(monkeypatch):
    # Red can capture black general in one move from the initial synthetic position.
    forced_start = "4k4/9/9/9/9/9/9/9/4R4/4K4 w"

    def fake_new_initial_state(self):
        return XiangqiState.from_fen(forced_start)

    monkeypatch.setattr(XiangqiGame, "new_initial_state", fake_new_initial_state)

    model = PolicyValueNet.for_xiangqi_v1(seed=7)
    replay, summary = run_selfplay(model, SelfPlayConfig(games=1, max_moves=8, exploration_eps=0.0), seed=7)

    assert summary.games == 1
    assert summary.natural_terminations == 1
    assert summary.step_cap_truncations == 0

    assert len(replay.games) == 1
    game = replay.games[0]
    assert game.ended_naturally is True
    assert game.hit_step_cap is False
    assert game.terminal_reason == "black_general_captured"
    assert game.result_label == "win"

    # The game contains one position from red-to-move, and should receive +1 target.
    assert len(replay.samples) == 1
    assert replay.samples[0].value_target == 1.0
