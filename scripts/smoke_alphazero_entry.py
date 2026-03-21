#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.smoke import run_alphazero_smoke


def main() -> int:
    out = run_alphazero_smoke(max_steps=64, seed=7)
    print(
        json.dumps(
            {
                "steps": out.steps,
                "step_limit": out.step_limit,
                "terminal": out.terminal,
                "terminated_by": out.terminated_by,
                "terminal_reason": out.terminal_reason,
                "returns": out.returns,
                "metadata": out.metadata,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
