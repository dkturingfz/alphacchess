#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.phase1_replay import ReplayDataset


def main() -> int:
    ap = argparse.ArgumentParser(description="Export replay dataset stats")
    ap.add_argument("--replay", required=True)
    args = ap.parse_args()

    ds = ReplayDataset.load(args.replay)
    obs, pol, val = ds.as_arrays()
    chosen = [max(range(len(row)), key=lambda i: row[i]) for row in pol] if pol else []
    payload = {
        "replay": str(Path(args.replay)),
        "metadata": ds.metadata,
        "num_samples": len(obs),
        "observation_shape": [len(obs[0]), len(obs[0][0]), len(obs[0][0][0])] if obs else [0, 0, 0],
        "policy_shape": [len(pol), len(pol[0]) if pol else 0],
        "value_mean": (sum(val) / len(val)) if val else 0.0,
        "value_min": min(val) if val else 0.0,
        "value_max": max(val) if val else 0.0,
        "distinct_actions_in_targets": len(set(chosen)),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
