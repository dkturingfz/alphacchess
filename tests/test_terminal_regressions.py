from alphacchess.notation import iccs_to_action
from alphacchess.xiangqi_game import BLACK, RED, XiangqiState


def test_terminal_by_general_capture_reports_reason_and_returns():
    st = XiangqiState.from_fen("4k4/9/9/9/9/9/9/9/4R4/4K4 w")
    action = iccs_to_action("e1e9")
    assert action in st.legal_actions()

    st.apply_action(action)

    assert st.is_terminal()
    assert st.terminal_reason() == "black_general_captured"
    assert st.legal_actions() == []
    assert st.returns() == [1.0, -1.0]


def test_terminal_no_legal_moves_black_to_move_loses():
    # Black to move has no legal move; red wins by terminal no-legal-move semantics.
    st = XiangqiState.from_fen("R3k4/4R4/9/9/9/9/9/9/9/4K4 b")
    assert st.current_player() == BLACK
    assert st.is_terminal()
    assert st.terminal_reason() == "no_legal_moves"
    assert st.legal_actions() == []
    assert st.returns() == [1.0, -1.0]


def test_terminal_no_legal_moves_red_to_move_loses():
    # Red to move has no legal move; black wins by terminal no-legal-move semantics.
    st = XiangqiState.from_fen("r3k4/9/9/9/9/9/9/9/9/r3K4 w")
    assert st.current_player() == RED
    assert st.is_terminal()
    assert st.terminal_reason() == "no_legal_moves"
    assert st.legal_actions() == []
    assert st.returns() == [-1.0, 1.0]
