import json

from alphacchess.dataset import DatasetBuilder
from alphacchess.notation import NotationAdapter
from alphacchess.versions import VERSION_METADATA


def test_fen_iccs_normalization_and_dataset_metadata(tmp_path):
    src = tmp_path / "games.txt"
    src.write_text("4k4/9/9/9/9/9/9/9/4R4/4K4 w | e1e9\n")

    records = NotationAdapter().load_plain_text(str(src))
    payload = DatasetBuilder().build(records)

    assert payload["metadata"]["action_encoding_version"] == VERSION_METADATA["action_encoding_version"]
    assert payload["metadata"]["observation_encoding_version"] == VERSION_METADATA["observation_encoding_version"]
    assert payload["metadata"]["dataset_schema_version"] == VERSION_METADATA["dataset_schema_version"]
    assert payload["metadata"]["rules_version"] == VERSION_METADATA["rules_version"]
    assert payload["records"][0]["moves_iccs"] == ["e1e9"]
    assert payload["records"][0]["result"] == [1.0, -1.0]

    out = tmp_path / "dataset.json"
    out.write_text(json.dumps(payload))
    loaded = json.loads(out.read_text())
    assert "metadata" in loaded and "content_sha256" in loaded["metadata"]
