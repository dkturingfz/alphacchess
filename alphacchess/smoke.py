from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List

from .xiangqi_game import XiangqiGame


@dataclass
class SmokeResult:
    steps: int
    step_limit: int
    terminal: bool
    terminated_by: str
    terminal_reason: str
    returns: List[float]
    metadata: Dict[str, str]


def run_alphazero_smoke(max_steps: int = 64, seed: int = 0) -> SmokeResult:
    random.seed(seed)
    game = XiangqiGame()
    state = game.new_initial_state()
    steps = 0
    terminated_by = "unknown"
    while not state.is_terminal() and steps < max_steps:
        legal = state.legal_actions()
        if not legal:
            terminated_by = "no_legal_actions_guard"
            break
        action = random.choice(legal)
        _obs = state.observation_tensor()  # ensure observation API is exercised
        state.apply_action(action)
        steps += 1

    terminal = state.is_terminal()
    if terminal:
        terminated_by = "natural_terminal"
    elif steps >= max_steps:
        terminated_by = "step_limit"
    elif terminated_by == "unknown":
        terminated_by = "other_stop_condition"

    return SmokeResult(
        steps=steps,
        step_limit=max_steps,
        terminal=terminal,
        terminated_by=terminated_by,
        terminal_reason=state.terminal_reason() if terminal else "none",
        returns=state.returns(),
        metadata=state.version_metadata(),
    )
