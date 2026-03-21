import pytest

from alphacchess.phase1_replay import ReplayDataset, ReplaySample, make_replay_metadata


def test_replay_roundtrip_and_metadata_validation(tmp_path):
    sample = ReplaySample(
        observation=[[[0.0 for _ in range(9)] for _ in range(10)] for _ in range(15)],
        policy_action=123,
        value_target=1.0,
        player=1,
    )
    ds = ReplayDataset(metadata=make_replay_metadata(), samples=[sample])
    p = tmp_path / "replay.json"
    ds.save(p)

    loaded = ReplayDataset.load(p)
    assert loaded.metadata["action_encoding_version"] == "v1_8100_from_to"
    assert loaded.samples[0].policy_action == 123


def test_replay_metadata_mismatch_raises():
    payload = {
        "metadata": {"action_encoding_version": "bad"},
        "samples": [],
    }
    with pytest.raises(ValueError):
        ReplayDataset.from_json(__import__("json").dumps(payload))
