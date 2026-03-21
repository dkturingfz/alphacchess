from alphacchess.xiangqi_game import ACTION_SPACE_SIZE, XiangqiGame, XiangqiState


def test_action_space_and_observation_shape():
    game = XiangqiGame()
    state = game.new_initial_state()
    assert game.num_distinct_actions() == ACTION_SPACE_SIZE == 8100
    shape = game.observation_tensor_shape()
    obs = state.observation_tensor()
    assert shape == (15, 10, 9)
    assert len(obs) == 15 and len(obs[0]) == 10 and len(obs[0][0]) == 9


def test_terminal_and_returns_capture_general():
    # Red rook captures black general directly.
    st = XiangqiState.from_fen("4k4/9/9/9/9/9/9/9/4R4/4K4 w")
    legal = set(st.legal_actions())
    # e1->e9 in ICCS coordinates corresponds to rook capturing black general.
    from alphacchess.notation import iccs_to_action

    action = iccs_to_action("e1e9")
    assert action in legal
    st.apply_action(action)
    assert st.is_terminal()
    assert st.returns() == [1.0, -1.0]


def test_random_rollout_no_corruption():
    import random

    rng = random.Random(0)
    st = XiangqiGame().new_initial_state()
    for _ in range(80):
        if st.is_terminal():
            break
        legal = st.legal_actions()
        assert all(0 <= a < 8100 for a in legal)
        st.apply_action(rng.choice(legal))
