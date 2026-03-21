#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from collections import Counter
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.xiangqi_game import XiangqiGame


def main() -> int:
    rng = random.Random(123)
    game = XiangqiGame()
    state = game.new_initial_state()
    rollout_count = 10
    rollout_step_cap = 128
    rollout_lengths = []
    natural_terminations = 0
    step_cap_hits = 0
    terminal_reason_counts: Counter[str] = Counter()
    terminal_reason_samples = []
    legal_action_count_total = 0
    legal_action_count_observations = 0
    repeated_state_rollouts = 0
    for _ in range(rollout_count):
        st = state.clone()
        steps = 0
        seen_fens = {st.to_fen()}
        repeated_state_detected = False
        while not st.is_terminal() and steps < rollout_step_cap:
            legal = st.legal_actions()
            legal_action_count_total += len(legal)
            legal_action_count_observations += 1
            if not legal:
                break
            st.apply_action(rng.choice(legal))
            steps += 1
            fen = st.to_fen()
            if fen in seen_fens:
                repeated_state_detected = True
            seen_fens.add(fen)
        rollout_lengths.append(steps)
        if repeated_state_detected:
            repeated_state_rollouts += 1
        if st.is_terminal():
            natural_terminations += 1
            reason = st.terminal_reason()
            terminal_reason_counts[reason] += 1
            if len(terminal_reason_samples) < 3:
                terminal_reason_samples.append(reason)
        elif steps >= rollout_step_cap:
            step_cap_hits += 1
            terminal_reason_counts["max_steps"] += 1

    average_rollout_length = sum(rollout_lengths) / len(rollout_lengths) if rollout_lengths else 0.0
    average_legal_actions = (
        legal_action_count_total / legal_action_count_observations if legal_action_count_observations else 0.0
    )
    result = {
        "num_distinct_actions": game.num_distinct_actions(),
        "observation_shape": game.observation_tensor_shape(),
        "rollout_count": rollout_count,
        "rollout_step_cap": rollout_step_cap,
        "rollout_lengths": rollout_lengths,
        "natural_terminations": natural_terminations,
        "step_cap_hits": step_cap_hits,
        "terminal_reason_counts": dict(terminal_reason_counts),
        "average_rollout_length": average_rollout_length,
        "min_rollout_length": min(rollout_lengths) if rollout_lengths else 0,
        "max_rollout_length": max(rollout_lengths) if rollout_lengths else 0,
        "average_legal_actions_per_position": average_legal_actions,
        "repeated_state_rollouts": repeated_state_rollouts,
        "terminal_reason_samples": terminal_reason_samples,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
