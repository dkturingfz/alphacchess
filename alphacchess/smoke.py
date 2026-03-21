from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List

from .xiangqi_game import XiangqiGame


@dataclass
class SmokeResult:
    steps: int
    terminal: bool
    returns: List[float]
    metadata: Dict[str, str]


def run_alphazero_smoke(max_steps: int = 64, seed: int = 0) -> SmokeResult:
    random.seed(seed)
    game = XiangqiGame()
    state = game.new_initial_state()
    steps = 0
    while not state.is_terminal() and steps < max_steps:
        legal = state.legal_actions()
        if not legal:
            break
        action = random.choice(legal)
        _obs = state.observation_tensor()  # ensure observation API is exercised
        state.apply_action(action)
        steps += 1

    return SmokeResult(
        steps=steps,
        terminal=state.is_terminal(),
        returns=state.returns(),
        metadata=state.version_metadata(),
    )
