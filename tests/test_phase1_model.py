from alphacchess.phase1_model import PolicyValueNet
from alphacchess.xiangqi_game import XiangqiGame


def test_policy_value_dimensions_match_game_contract():
    game = XiangqiGame()
    model = PolicyValueNet.for_xiangqi_v1(seed=1)
    state = game.new_initial_state()
    obs = [state.observation_tensor()]
    policy_logits, value = model.forward(obs)

    assert (len(obs[0]), len(obs[0][0]), len(obs[0][0][0])) == game.observation_tensor_shape()
    assert len(policy_logits) == 1
    assert len(policy_logits[0]) == game.num_distinct_actions()
    assert len(value) == 1


def test_policy_size_fixed_8100_and_scalar_value_for_batch():
    model = PolicyValueNet.for_xiangqi_v1(seed=2)
    batch = [[[[0.0 for _ in range(9)] for _ in range(10)] for _ in range(15)] for _ in range(4)]
    policy_logits, value = model.forward(batch)
    assert len(policy_logits[0]) == 8100
    assert isinstance(value, list)
    assert len(value) == 4
