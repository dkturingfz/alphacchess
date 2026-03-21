from alphacchess.smoke import run_alphazero_smoke


def test_minimal_alphazero_smoke_path():
    out = run_alphazero_smoke(max_steps=8, seed=1)
    assert out.steps > 0
    assert set(out.metadata.keys()) >= {
        "action_encoding_version",
        "observation_encoding_version",
        "dataset_schema_version",
        "rules_version",
    }
