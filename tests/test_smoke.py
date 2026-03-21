from alphacchess.smoke import run_alphazero_smoke


def test_minimal_alphazero_smoke_path():
    out = run_alphazero_smoke(max_steps=8, seed=1)
    assert out.steps > 0
    assert out.step_limit == 8
    assert out.terminated_by in {"natural_terminal", "step_limit", "other_stop_condition", "no_legal_actions_guard"}
    if out.terminal:
        assert out.terminal_reason != "none"
    else:
        assert out.terminal_reason == "none"
    assert set(out.metadata.keys()) >= {
        "action_encoding_version",
        "observation_encoding_version",
        "dataset_schema_version",
        "rules_version",
    }
