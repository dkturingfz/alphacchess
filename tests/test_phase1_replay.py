import pytest

from alphacchess.phase1_replay import ReplayDataset, ReplayGame, ReplaySample, make_replay_metadata, summarize_replay


def test_replay_roundtrip_and_metadata_validation(tmp_path):
    sample = ReplaySample(
        observation=[[[0.0 for _ in range(9)] for _ in range(10)] for _ in range(15)],
        policy_action=123,
        value_target=1.0,
        player=1,
        game_index=0,
    )
    game = ReplayGame(
        game_index=0,
        moves=1,
        ended_naturally=True,
        hit_step_cap=False,
        terminal_reason="black_general_captured",
        result_label="win",
        red_return=1.0,
        black_return=-1.0,
    )
    ds = ReplayDataset(metadata=make_replay_metadata(), samples=[sample], games=[game])
    p = tmp_path / "replay.json"
    ds.save(p)

    loaded = ReplayDataset.load(p)
    assert loaded.metadata["action_encoding_version"] == "v1_8100_from_to"
    assert loaded.samples[0].policy_action == 123
    assert loaded.games[0].terminal_reason == "black_general_captured"


def test_replay_metadata_mismatch_raises():
    payload = {
        "metadata": {"action_encoding_version": "bad"},
        "samples": [],
    }
    with pytest.raises(ValueError):
        ReplayDataset.from_json(__import__("json").dumps(payload))


def test_replay_summary_distinguishes_terminal_and_truncation():
    obs = [[[0.0 for _ in range(9)] for _ in range(10)] for _ in range(15)]
    ds = ReplayDataset(
        metadata=make_replay_metadata(),
        samples=[
            ReplaySample(observation=obs, policy_action=1, value_target=1.0, player=1, game_index=0),
            ReplaySample(observation=obs, policy_action=2, value_target=-1.0, player=-1, game_index=0),
            ReplaySample(observation=obs, policy_action=3, value_target=0.0, player=1, game_index=1),
        ],
        games=[
            ReplayGame(
                game_index=0,
                moves=1,
                ended_naturally=True,
                hit_step_cap=False,
                terminal_reason="black_general_captured",
                result_label="win",
                red_return=1.0,
                black_return=-1.0,
            ),
            ReplayGame(
                game_index=1,
                moves=80,
                ended_naturally=False,
                hit_step_cap=True,
                terminal_reason="max_moves_truncation",
                result_label="truncated_draw",
                red_return=0.0,
                black_return=0.0,
            ),
        ],
    )

    summary = summarize_replay(ds)
    assert summary["num_games"] == 2
    assert summary["natural_terminations"] == 1
    assert summary["step_cap_truncations"] == 1
    assert summary["result_counts"]["win"] == 1
    assert summary["result_counts"]["truncated_draw"] == 1
    assert summary["value_positive_count"] == 1
    assert summary["value_zero_count"] == 1
    assert summary["value_negative_count"] == 1
