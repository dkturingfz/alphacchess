from alphacchess.notation import action_to_iccs, iccs_to_action
from alphacchess.xiangqi_game import decode_action, encode_action


def test_action_encoding_roundtrip():
    for from_sq in [0, 10, 44, 89]:
        for to_sq in [0, 11, 45, 89]:
            action = encode_action(from_sq, to_sq)
            f2, t2 = decode_action(action)
            assert (f2, t2) == (from_sq, to_sq)


def test_iccs_roundtrip():
    moves = ["a0a1", "e0e1", "i9h9", "b2h2"]
    for mv in moves:
        action = iccs_to_action(mv)
        assert action_to_iccs(action) == mv
