#!/usr/bin/env python3
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.xiangqi_game import XiangqiGame


def main() -> int:
    rng = random.Random(123)
    game = XiangqiGame()
    state = game.new_initial_state()
    rollout_lengths = []
    for _ in range(10):
        st = state.clone()
        steps = 0
        while not st.is_terminal() and steps < 128:
            legal = st.legal_actions()
            if not legal:
                break
            st.apply_action(rng.choice(legal))
            steps += 1
        rollout_lengths.append(steps)
    result = {
        "num_distinct_actions": game.num_distinct_actions(),
        "observation_shape": game.observation_tensor_shape(),
        "rollout_lengths": rollout_lengths,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
