#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.phase1_eval import EvalConfig, evaluate_model_vs_model
from alphacchess.phase1_model import PolicyValueNet
from alphacchess.versions import VERSION_METADATA


class ConfigError(ValueError):
    pass


def _coerce_scalar(raw: str) -> Any:
    lowered = raw.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(raw)
    except ValueError:
        return raw.strip().strip('"').strip("'")


def load_benchmark_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    raw = p.read_text()
    cfg: dict[str, Any] = {}
    lines = raw.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ConfigError(f"invalid line in benchmark config: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            items: list[Any] = []
            while i < len(lines):
                nxt = lines[i].strip()
                if not nxt or nxt.startswith("#"):
                    i += 1
                    continue
                if not nxt.startswith("-"):
                    break
                items.append(_coerce_scalar(nxt[1:].strip()))
                i += 1
            cfg[key] = items
            continue
        cfg[key] = _coerce_scalar(value)
    return cfg


def _validate_config(cfg: dict[str, Any]) -> None:
    required = [
        "engine_name",
        "search_limit_type",
        "games_per_side",
        "evaluation_seeds",
        "swap_colors",
        "resign_enabled",
        "draw_adjudication_enabled",
        "max_moves",
        "max_moves_result",
    ]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ConfigError(f"benchmark config missing required keys: {missing}")
    if cfg["search_limit_type"] != "depth":
        raise ConfigError("benchmark v1 requires search_limit_type=depth")
    if not isinstance(cfg["evaluation_seeds"], list) or not cfg["evaluation_seeds"]:
        raise ConfigError("evaluation_seeds must be a non-empty list")


def _config_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def _checkpoint_id(checkpoint_path: Path, checkpoint_meta: dict[str, Any]) -> str:
    iteration = checkpoint_meta.get("iteration")
    if iteration is not None:
        return f"{checkpoint_path.stem}:iter_{iteration}"
    return checkpoint_path.stem


def _run_proxy_eval(candidate_ckpt: Path, baseline_ckpt: Path, games: int, max_moves: int, seed: int) -> dict[str, Any]:
    candidate_model, candidate_meta = PolicyValueNet.load_checkpoint(candidate_ckpt)
    baseline_model, _ = PolicyValueNet.load_checkpoint(baseline_ckpt)
    result = evaluate_model_vs_model(
        candidate_model,
        baseline_model,
        EvalConfig(games=games, max_moves=max_moves, seed=seed),
    )
    return {
        "candidate_checkpoint_metadata": candidate_meta,
        "games": result.games,
        "candidate_wins": result.candidate_wins,
        "engine_wins": result.baseline_wins,
        "draws": result.draws,
        "candidate_score": result.candidate_score,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 3 strength benchmark preparation vs Pikafish")
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--benchmark-config", default="configs/benchmark_pikafish_v1.yaml")
    ap.add_argument("--engine-path", default="")
    ap.add_argument("--engine-version", default="")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--proxy-baseline-checkpoint", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    cfg_path = Path(args.benchmark_config)
    cfg = load_benchmark_config(cfg_path)
    _validate_config(cfg)

    candidate_path = Path(args.checkpoint)
    _, candidate_meta = PolicyValueNet.load_checkpoint(candidate_path)

    engine_path = args.engine_path or os.environ.get("PIKAFISH_PATH", "")
    engine_version = args.engine_version or os.environ.get("PIKAFISH_VERSION", "unknown")
    selected_seed = args.seed if args.seed is not None else int(cfg["evaluation_seeds"][0])

    payload: dict[str, Any] = {
        "metadata": dict(VERSION_METADATA),
        "benchmark_schema_version": "phase3_strength_benchmark_v1",
        "benchmark_config_name": cfg_path.name,
        "benchmark_config_hash": _config_hash(cfg_path),
        "benchmark_config_path": str(cfg_path),
        "engine_name": str(cfg["engine_name"]),
        "engine_version": engine_version,
        "engine_path_source": "cli" if args.engine_path else "env",
        "checkpoint": str(candidate_path),
        "checkpoint_id": _checkpoint_id(candidate_path, candidate_meta),
        "seed": selected_seed,
        "status": "prepared",
        "notes": [],
        "result": None,
    }

    if args.proxy_baseline_checkpoint:
        baseline_ckpt = Path(args.proxy_baseline_checkpoint)
        games = int(cfg["games_per_side"]) * (2 if cfg.get("swap_colors", False) else 1)
        payload["status"] = "completed_proxy"
        payload["notes"].append("Proxy mode uses checkpoint-vs-checkpoint evaluator to validate benchmark protocol wiring.")
        payload["result"] = _run_proxy_eval(
            candidate_ckpt=candidate_path,
            baseline_ckpt=baseline_ckpt,
            games=games,
            max_moves=int(cfg["max_moves"]),
            seed=selected_seed,
        )
    elif args.dry_run:
        payload["status"] = "dry_run"
        payload["notes"].append("Dry-run validates benchmark metadata and config hashing without engine gameplay.")
    else:
        if not engine_path:
            raise SystemExit(
                "PIKAFISH_PATH is required unless --dry-run or --proxy-baseline-checkpoint is used."
            )
        payload["status"] = "blocked_missing_engine_runtime"
        payload["notes"].append(
            "Engine runtime integration is intentionally deferred in this phase; use --dry-run for protocol checks."
        )

    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
