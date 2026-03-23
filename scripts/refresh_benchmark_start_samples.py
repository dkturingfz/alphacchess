#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import pstdev


@dataclass(frozen=True)
class Candidate:
    fen: str
    source_ply: int
    source_file: str
    source_game_index: int


def _piece_count(fen: str) -> int:
    board = fen.split()[0]
    return sum(1 for ch in board if ch.isalpha())


def _read_candidates(path: Path, max_source_ply: int) -> list[Candidate]:
    raw: list[Candidate] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        fen = str(rec.get("fen", "")).strip()
        if not fen:
            continue
        source_ply = int(rec.get("source_ply", -1))
        if source_ply < 0 or source_ply > max_source_ply:
            continue
        raw.append(
            Candidate(
                fen=fen,
                source_ply=source_ply,
                source_file=str(rec.get("source_file", "")),
                source_game_index=int(rec.get("source_game_index", -1)),
            )
        )
    return raw


def _dedup_by_fen(records: list[Candidate]) -> list[Candidate]:
    best: dict[str, Candidate] = {}
    for rec in records:
        prev = best.get(rec.fen)
        if prev is None:
            best[rec.fen] = rec
            continue
        if (rec.source_ply, rec.source_file, rec.source_game_index) < (
            prev.source_ply,
            prev.source_file,
            prev.source_game_index,
        ):
            best[rec.fen] = rec
    return sorted(best.values(), key=lambda r: (r.source_ply, _piece_count(r.fen), r.fen))


def _evenly_spaced(records: list[Candidate], count: int) -> list[Candidate]:
    if not records or count <= 0:
        return []
    if len(records) <= count:
        return records
    last = len(records) - 1
    picks: list[Candidate] = []
    used: set[int] = set()
    for i in range(count):
        idx = round(i * last / (count - 1)) if count > 1 else 0
        while idx in used and idx < last:
            idx += 1
        while idx in used and idx > 0:
            idx -= 1
        used.add(idx)
        picks.append(records[idx])
    return picks


def _summary_stats(records: list[Candidate]) -> dict[str, object]:
    if not records:
        return {
            "unique_fens": 0,
            "piece_count": {"min": None, "max": None, "mean": None, "stddev": None, "distinct": []},
            "source_ply": {"min": None, "max": None, "mean": None, "stddev": None, "distinct": []},
        }
    piece_counts = [_piece_count(r.fen) for r in records]
    source_plies = [r.source_ply for r in records]

    def stat(xs: list[int]) -> dict[str, object]:
        return {
            "min": min(xs),
            "max": max(xs),
            "mean": round(sum(xs) / len(xs), 4),
            "stddev": round(pstdev(xs), 4) if len(xs) > 1 else 0.0,
            "distinct": sorted(set(xs)),
        }

    return {
        "unique_fens": len({r.fen for r in records}),
        "piece_count": stat(piece_counts),
        "source_ply": stat(source_plies),
    }


def _write_sample(path: Path, selected: list[Candidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(r.fen for r in selected) + "\n", encoding="utf-8")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministically refresh benchmark_start FEN sample candidates from converted corpus"
    )
    parser.add_argument("--input", required=True, help="Converted corpus JSONL path")
    parser.add_argument(
        "--output-sample",
        default="data/benchmark_positions/samples/benchmark_start_fens_sample.txt",
        help="Tracked benchmark_start sample output",
    )
    parser.add_argument("--selected-count", type=int, default=12)
    parser.add_argument(
        "--max-source-ply",
        type=int,
        default=20,
        help="Use positions at or before this ply as benchmark_start candidate pool",
    )
    parser.add_argument("--manifest-output", default="", help="Optional compact selected manifest JSON")
    parser.add_argument("--summary-output", default="", help="Optional refresh summary JSON")
    parser.add_argument(
        "--candidate-dump-output",
        default="",
        help="Optional local-only JSONL dump of deduplicated candidate pool (keep out of git)",
    )
    args = parser.parse_args()

    source_path = Path(args.input)
    raw_candidates = _read_candidates(source_path, max_source_ply=args.max_source_ply)
    dedup_candidates = _dedup_by_fen(raw_candidates)
    selected = _evenly_spaced(dedup_candidates, args.selected_count)

    if not selected:
        raise ValueError("No benchmark_start candidates found; check --input and --max-source-ply")

    _write_sample(Path(args.output_sample), selected)

    if args.candidate_dump_output:
        dump_path = Path(args.candidate_dump_output)
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        with dump_path.open("w", encoding="utf-8") as fp:
            for row in dedup_candidates:
                fp.write(
                    json.dumps(
                        {
                            "fen": row.fen,
                            "source_ply": row.source_ply,
                            "source_file": row.source_file,
                            "source_game_index": row.source_game_index,
                            "piece_count": _piece_count(row.fen),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    manifest = {
        "source_corpus_path": str(source_path),
        "selection_strategy": (
            "Select all positions with source_ply <= max_source_ply from converted corpus, deduplicate by exact FEN "
            "(keeping earliest provenance), sort by (source_ply, piece_count, fen), then take deterministic evenly "
            "spaced picks."
        ),
        "max_source_ply": args.max_source_ply,
        "selected_count_requested": args.selected_count,
        "selected_count_actual": len(selected),
        "selected": [
            {
                "fen": row.fen,
                "source_ply": row.source_ply,
                "source_file": row.source_file,
                "source_game_index": row.source_game_index,
                "piece_count": _piece_count(row.fen),
            }
            for row in selected
        ],
    }

    summary = {
        "source_corpus_path": str(source_path),
        "total_candidate_count": len(raw_candidates),
        "deduplicated_candidate_count": len(dedup_candidates),
        "selected_sample_count": len(selected),
        "max_source_ply": args.max_source_ply,
        "selection_rationale": manifest["selection_strategy"],
        "deduplicated_diversity": _summary_stats(dedup_candidates),
        "selected_diversity": _summary_stats(selected),
    }

    if args.manifest_output:
        _write_json(Path(args.manifest_output), manifest)
    if args.summary_output:
        _write_json(Path(args.summary_output), summary)

    payload = {"manifest": manifest, "summary": summary}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
