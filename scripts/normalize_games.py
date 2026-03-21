#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.dataset import DatasetBuilder
from alphacchess.notation import NotationAdapter


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize Xiangqi game records into schema-v1 dataset")
    parser.add_argument("--input", required=True, help="Input file (.txt as `FEN | moves`, or .jsonl)")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    adapter = NotationAdapter()
    if args.input.endswith(".jsonl"):
        records = adapter.load_jsonl(args.input)
    else:
        records = adapter.load_plain_text(args.input)

    payload = DatasetBuilder().build_to_path(records, args.output)
    print(json.dumps({"records": len(payload["records"]), "metadata": payload["metadata"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
