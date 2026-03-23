#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CATEGORIES = ["opening", "middlegame", "endgame", "near_terminal", "benchmark_start"]


@dataclass(frozen=True)
class FenRecord:
    fen: str
    category: str
    source_ply: int


def _read_records(path: Path) -> list[FenRecord]:
    records: list[FenRecord] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        fen = str(rec["fen"]).strip()
        category = str(rec["category"]).strip()
        source_ply = int(rec.get("source_ply", -1))
        records.append(FenRecord(fen=fen, category=category, source_ply=source_ply))
    return records


def _piece_count(fen: str) -> int:
    board = fen.split()[0]
    return sum(1 for ch in board if ch.isalpha())


def _dedup(records: Iterable[FenRecord]) -> list[FenRecord]:
    seen: set[str] = set()
    out: list[FenRecord] = []
    for rec in records:
        if rec.fen in seen:
            continue
        seen.add(rec.fen)
        out.append(rec)
    return out


def _evenly_spaced(records: list[FenRecord], count: int) -> list[FenRecord]:
    if count <= 0 or not records:
        return []
    if len(records) <= count:
        return records

    ranked = sorted(
        records,
        key=lambda r: (
            _piece_count(r.fen),
            r.source_ply,
            r.fen,
        ),
    )
    last = len(ranked) - 1
    picks: list[FenRecord] = []
    seen_idx: set[int] = set()
    for i in range(count):
        idx = round(i * last / (count - 1)) if count > 1 else 0
        while idx in seen_idx and idx < last:
            idx += 1
        while idx in seen_idx and idx > 0:
            idx -= 1
        seen_idx.add(idx)
        picks.append(ranked[idx])
    return picks


def _write_lines(path: Path, fens: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(fens) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Curate small tracked FEN samples from a local JSONL corpus")
    parser.add_argument("--input", required=True, help="Input JSONL from build_test_positions_from_games.py")
    parser.add_argument("--sample-dir", default="data/test_positions/samples", help="Tracked sample dir")
    parser.add_argument(
        "--benchmark-sample-dir",
        default="data/benchmark_positions/samples",
        help="Tracked benchmark-start sample dir",
    )
    parser.add_argument("--summary-output", default="", help="Optional summary JSON output path")
    parser.add_argument("--opening-count", type=int, default=24)
    parser.add_argument("--middlegame-count", type=int, default=24)
    parser.add_argument("--endgame-count", type=int, default=24)
    parser.add_argument("--near-terminal-count", type=int, default=24)
    parser.add_argument("--benchmark-start-count", type=int, default=24)
    parser.add_argument("--regression-count", type=int, default=48)
    args = parser.parse_args()

    records = _read_records(Path(args.input))
    unique_all = _dedup(records)
    duplicates = len(records) - len(unique_all)

    per_category_total = {name: 0 for name in CATEGORIES}
    per_category_unique = {name: 0 for name in CATEGORIES}

    by_cat: dict[str, list[FenRecord]] = {name: [] for name in CATEGORIES}
    for rec in records:
        if rec.category in by_cat:
            per_category_total[rec.category] += 1
            by_cat[rec.category].append(rec)

    by_cat_unique = {name: _dedup(items) for name, items in by_cat.items()}
    for name, items in by_cat_unique.items():
        per_category_unique[name] = len(items)

    cat_counts = {
        "opening": args.opening_count,
        "middlegame": args.middlegame_count,
        "endgame": args.endgame_count,
        "near_terminal": args.near_terminal_count,
        "benchmark_start": args.benchmark_start_count,
    }

    sampled_by_cat = {
        name: _evenly_spaced(by_cat_unique[name], cat_counts[name]) for name in CATEGORIES
    }

    sample_dir = Path(args.sample_dir)
    benchmark_dir = Path(args.benchmark_sample_dir)

    _write_lines(sample_dir / "opening_fens_sample.txt", [r.fen for r in sampled_by_cat["opening"]])
    _write_lines(sample_dir / "middlegame_fens_sample.txt", [r.fen for r in sampled_by_cat["middlegame"]])
    _write_lines(sample_dir / "endgame_fens_sample.txt", [r.fen for r in sampled_by_cat["endgame"]])
    _write_lines(sample_dir / "near_terminal_fens_sample.txt", [r.fen for r in sampled_by_cat["near_terminal"]])
    _write_lines(
        benchmark_dir / "benchmark_start_fens_sample.txt",
        [r.fen for r in sampled_by_cat["benchmark_start"]],
    )

    regression_pool = []
    for cat in ["opening", "middlegame", "endgame", "near_terminal"]:
        regression_pool.extend(sampled_by_cat[cat])
    regression = _evenly_spaced(_dedup(regression_pool), args.regression_count)
    _write_lines(sample_dir / "regression_fens_sample.txt", [r.fen for r in regression])

    payload = {
        "positions_total": len(records),
        "unique_fens": len(unique_all),
        "duplicate_fens": duplicates,
        "per_category_total": per_category_total,
        "per_category_unique": per_category_unique,
        "sample_sizes": {
            "opening": len(sampled_by_cat["opening"]),
            "middlegame": len(sampled_by_cat["middlegame"]),
            "endgame": len(sampled_by_cat["endgame"]),
            "near_terminal": len(sampled_by_cat["near_terminal"]),
            "benchmark_start": len(sampled_by_cat["benchmark_start"]),
            "regression": len(regression),
        },
        "sampling_strategy": "Per-category dedup by FEN then deterministic evenly-spaced picks over (piece_count, source_ply, fen).",
    }

    if args.summary_output:
        summary_path = Path(args.summary_output)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
