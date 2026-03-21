from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .versions import VERSION_METADATA
from .xiangqi_game import ACTION_SPACE_SIZE

REPLAY_SCHEMA_VERSION = "phase1_replay_v1"


@dataclass
class ReplaySample:
    observation: List[List[List[float]]]
    policy_action: int
    value_target: float
    player: int


@dataclass
class ReplayDataset:
    metadata: Dict[str, str]
    samples: List[ReplaySample]

    def to_json(self) -> str:
        return json.dumps({"metadata": dict(self.metadata), "samples": [asdict(s) for s in self.samples]})

    @classmethod
    def from_json(cls, raw: str) -> "ReplayDataset":
        payload = json.loads(raw)
        metadata = payload["metadata"]
        _validate_metadata(metadata)
        return cls(metadata=metadata, samples=[ReplaySample(**s) for s in payload["samples"]])

    def save(self, path: str | Path) -> None:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.to_json())

    @classmethod
    def load(cls, path: str | Path) -> "ReplayDataset":
        return cls.from_json(Path(path).read_text())

    def as_arrays(self) -> Tuple[List, List, List[float]]:
        obs = [s.observation for s in self.samples]
        pol = []
        for s in self.samples:
            row = [0.0] * ACTION_SPACE_SIZE
            row[s.policy_action] = 1.0
            pol.append(row)
        val = [float(s.value_target) for s in self.samples]
        return obs, pol, val


def make_replay_metadata() -> Dict[str, str]:
    meta = dict(VERSION_METADATA)
    meta["replay_schema_version"] = REPLAY_SCHEMA_VERSION
    return meta


def _validate_metadata(metadata: Dict[str, str]) -> None:
    expected = make_replay_metadata()
    for k, v in expected.items():
        if metadata.get(k) != v:
            raise ValueError(f"Replay metadata mismatch: {k} expected={v} got={metadata.get(k)}")
