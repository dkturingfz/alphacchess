#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> dict[str, object]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="One-command FEN sample asset workflow check")
    parser.add_argument("--benchmark-start-min-unique", type=int, default=4)
    parser.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Only run the validator step (useful for nested smoke tests).",
    )
    args = parser.parse_args()

    validate_cmd = [
        sys.executable,
        "scripts/validate_fen_samples.py",
        "--benchmark-start-min-unique",
        str(args.benchmark_start_min_unique),
    ]
    pytest_cmd = [sys.executable, "-m", "pytest", "-q", "tests/test_fen_sample_assets.py"]

    results = {"validate_fen_samples": _run(validate_cmd)}
    if not args.skip_pytest and os.environ.get("ALPHACCHESS_CHECK_FEN_ASSETS_INNER") != "1":
        results["pytest_fen_sample_assets"] = _run(pytest_cmd)
    ok = all(int(step["returncode"]) == 0 for step in results.values())
    payload = {"status": "ok" if ok else "failed", "steps": results}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
