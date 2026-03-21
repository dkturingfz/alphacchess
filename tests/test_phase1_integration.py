from alphacchess.phase1_eval import EvalConfig, evaluate_vs_random
from alphacchess.phase1_model import PolicyValueNet
from alphacchess.phase1_replay import ReplayDataset
from alphacchess.phase1_selfplay import SelfPlayConfig, run_selfplay
from alphacchess.phase1_train import TrainConfig, train_on_replay


def test_one_iteration_selfplay_train_reload_evaluate(tmp_path):
    model = PolicyValueNet.for_xiangqi_v1(seed=3)
    replay, summary = run_selfplay(
        model,
        SelfPlayConfig(games=4, max_moves=80, terminal_enrichment_games=2, terminal_enrichment_max_moves=4),
        seed=3,
    )
    assert summary.samples > 0
    assert summary.natural_terminations + summary.step_cap_truncations == summary.games
    assert len(replay.games) == summary.games

    replay_path = tmp_path / "replay.json"
    replay.save(replay_path)
    replay2 = ReplayDataset.load(replay_path)
    obs, pol, val = replay2.as_arrays()
    assert any(v != 0.0 for v in val)

    assert (len(obs[0]), len(obs[0][0]), len(obs[0][0][0])) == (15, 10, 9)
    assert len(pol[0]) == 8100
    assert isinstance(val[0], float)

    train_on_replay(model, obs, pol, val, TrainConfig(epochs=1, batch_size=16, lr=1e-3, seed=3))

    ckpt = tmp_path / "model.json"
    metadata = dict(replay2.metadata)
    metadata["checkpoint_schema_version"] = "phase1_checkpoint_v1"
    model.save_checkpoint(ckpt, metadata)

    reloaded, ckpt_meta = PolicyValueNet.load_checkpoint(ckpt)
    assert ckpt_meta["checkpoint_schema_version"] == "phase1_checkpoint_v1"

    p, v = reloaded.forward([replay2.samples[0].observation])
    assert len(p) == 1 and len(p[0]) == 8100
    assert len(v) == 1

    ev = evaluate_vs_random(reloaded, EvalConfig(games=6, max_moves=80, seed=3))
    assert ev.games == 6
