from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .versions import VERSION_METADATA
from .xiangqi_game import ACTION_SPACE_SIZE

REPLAY_SCHEMA_VERSION = "phase1_replay_v2"


@dataclass
class ReplaySample:
    observation: List[List[List[float]]]
    policy_action: int
    value_target: float
    player: int
    game_index: int


@dataclass
class ReplayGame:
    game_index: int
    moves: int
    ended_naturally: bool
    hit_step_cap: bool
    terminal_reason: str
    result_label: str
    red_return: float
    black_return: float


@dataclass
class ReplayDataset:
    metadata: Dict[str, str]
    samples: List[ReplaySample]
    games: List[ReplayGame]

    def to_json(self) -> str:
        return json.dumps(
            {
                "metadata": dict(self.metadata),
                "samples": [asdict(s) for s in self.samples],
                "games": [asdict(g) for g in self.games],
            }
        )

    @classmethod
    def from_json(cls, raw: str) -> "ReplayDataset":
        payload = json.loads(raw)
        metadata = payload["metadata"]
        _validate_metadata(metadata)
        samples = [ReplaySample(**s) for s in payload["samples"]]
        games = [ReplayGame(**g) for g in payload.get("games", [])]
        return cls(metadata=metadata, samples=samples, games=games)

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


def summarize_replay(ds: ReplayDataset) -> Dict[str, object]:
    obs, pol, val = ds.as_arrays()
    chosen = [max(range(len(row)), key=lambda i: row[i]) for row in pol] if pol else []
    game_counts = {
        "natural_terminations": 0,
        "step_cap_truncations": 0,
        "win": 0,
        "loss": 0,
        "draw": 0,
        "truncated_draw": 0,
    }
    terminal_reason_counts: Dict[str, int] = {}
    for g in ds.games:
        if g.ended_naturally:
            game_counts["natural_terminations"] += 1
        if g.hit_step_cap:
            game_counts["step_cap_truncations"] += 1
        if g.result_label in game_counts:
            game_counts[g.result_label] += 1
        terminal_reason_counts[g.terminal_reason] = terminal_reason_counts.get(g.terminal_reason, 0) + 1

    pos_count = sum(1 for x in val if x > 0)
    zero_count = sum(1 for x in val if x == 0)
    neg_count = sum(1 for x in val if x < 0)
    non_zero_count = len(val) - zero_count

    return {
        "metadata": ds.metadata,
        "num_samples": len(obs),
        "observation_shape": [len(obs[0]), len(obs[0][0]), len(obs[0][0][0])] if obs else [0, 0, 0],
        "policy_shape": [len(pol), len(pol[0]) if pol else 0],
        "value_mean": (sum(val) / len(val)) if val else 0.0,
        "value_min": min(val) if val else 0.0,
        "value_max": max(val) if val else 0.0,
        "value_positive_count": pos_count,
        "value_zero_count": zero_count,
        "value_negative_count": neg_count,
        "value_non_zero_fraction": (non_zero_count / len(val)) if val else 0.0,
        "distinct_actions_in_targets": len(set(chosen)),
        "num_games": len(ds.games),
        "natural_terminations": game_counts["natural_terminations"],
        "step_cap_truncations": game_counts["step_cap_truncations"],
        "result_counts": {
            "win": game_counts["win"],
            "loss": game_counts["loss"],
            "draw": game_counts["draw"],
            "truncated_draw": game_counts["truncated_draw"],
        },
        "terminal_reason_counts": terminal_reason_counts,
    }
