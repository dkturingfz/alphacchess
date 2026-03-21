from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Dict, List

from .phase1_model import PolicyValueNet


@dataclass
class TrainConfig:
    epochs: int = 4
    batch_size: int = 64
    lr: float = 1e-3
    seed: int = 0


@dataclass
class TrainSummary:
    steps: int
    metrics: List[Dict[str, float]]


def train_on_replay(
    model: PolicyValueNet,
    obs: List,
    policy_target: List,
    value_target: List[float],
    cfg: TrainConfig,
) -> TrainSummary:
    rng = random.Random(cfg.seed)
    n = len(obs)
    order = list(range(n))
    metrics: List[Dict[str, float]] = []
    steps = 0

    for _ in range(cfg.epochs):
        rng.shuffle(order)
        for start in range(0, n, cfg.batch_size):
            idx = order[start : start + cfg.batch_size]
            batch_obs = [obs[i] for i in idx]
            batch_pol = [policy_target[i] for i in idx]
            batch_val = [value_target[i] for i in idx]
            metrics.append(model.train_batch(batch_obs, batch_pol, batch_val, lr=cfg.lr))
            steps += 1

    return TrainSummary(steps=steps, metrics=metrics)
