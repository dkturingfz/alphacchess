#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.phase1_replay import ReplayDataset, summarize_replay


def main() -> int:
    ap = argparse.ArgumentParser(description="Export replay dataset stats")
    ap.add_argument("--replay", required=True)
    args = ap.parse_args()

    ds = ReplayDataset.load(args.replay)
    payload = {"replay": str(Path(args.replay))}
    payload.update(summarize_replay(ds))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
