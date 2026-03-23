#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.notation import iccs_to_action
from alphacchess.xiangqi_game import INITIAL_FEN, XiangqiState

# Supported ICCS movetext token shapes:
# - compact:    h2e2
# - hyphenated: h2-e2 (optional surrounding spaces around "-")
ICCS_MOVE_RE = re.compile(
    r"\b([a-i][0-9])(?:\s*-\s*([a-i][0-9])|([a-i][0-9]))\b",
    flags=re.IGNORECASE,
)
FEN_TAG_RE = re.compile(r"\[FEN\s+\"([^\"]+)\"\]", flags=re.IGNORECASE)


@dataclass
class ConversionStats:
    files_seen: int = 0
    games_seen: int = 0
    games_converted: int = 0
    positions_emitted: int = 0
    parse_errors: int = 0


def _categorize_position(*, ply: int, legal_count: int, is_terminal: bool) -> str:
    if ply == 0:
        return "benchmark_start"
    if is_terminal or legal_count <= 4:
        return "near_terminal"
    if ply <= 20:
        return "opening"
    if ply <= 80:
        return "middlegame"
    return "endgame"


def _extract_iccs_moves(line: str) -> list[str]:
    moves: list[str] = []
    for src, dst_hyphen, dst_compact in ICCS_MOVE_RE.findall(line):
        dst = dst_hyphen or dst_compact
        moves.append(f"{src}{dst}".lower())
    return moves


def _extract_games(lines: list[str]) -> Iterable[tuple[str, list[str]]]:
    current_fen = INITIAL_FEN
    current_moves: list[str] = []

    def flush() -> tuple[str, list[str]] | None:
        nonlocal current_moves, current_fen
        if not current_moves:
            return None
        game = (current_fen, current_moves)
        current_moves = []
        current_fen = INITIAL_FEN
        return game

    for raw in lines:
        line = raw.strip()
        if not line:
            game = flush()
            if game:
                yield game
            continue

        fen_match = FEN_TAG_RE.search(line)
        if fen_match:
            current_fen = fen_match.group(1).strip()
            continue

        lowered = line.lower()
        if line.startswith("["):
            continue
        if lowered in {"1-0", "0-1", "1/2-1/2", "*"}:
            game = flush()
            if game:
                yield game
            continue

        current_moves.extend(_extract_iccs_moves(line))

    game = flush()
    if game:
        yield game


def _iter_input_files(inputs: list[str], recursive: bool) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for value in inputs:
        path = Path(value).expanduser()
        path_str = str(path)
        if glob.has_magic(path_str):
            matches = sorted(Path(p) for p in glob.glob(path_str, recursive=recursive))
            candidates = [p for p in matches if p.is_file()]
        elif path.is_dir():
            pattern = "**/*" if recursive else "*"
            candidates = sorted(p for p in path.glob(pattern) if p.is_file())
        elif path.exists():
            candidates = [path]
        else:
            candidates = []

        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(candidate)
    return files


def _emit_positions(
    state: XiangqiState,
    moves_iccs: list[str],
    emit_start_position: bool,
    sample_every_n_plies: int,
) -> list[tuple[int, str, int, bool]]:
    positions: list[tuple[int, str, int, bool]] = []
    if emit_start_position:
        legal = len(state.legal_actions())
        positions.append((0, state.to_fen(), legal, state.is_terminal()))
    for ply, move in enumerate(moves_iccs, start=1):
        state.apply_action(iccs_to_action(move))
        if sample_every_n_plies <= 1 or ply % sample_every_n_plies == 0:
            legal = len(state.legal_actions())
            positions.append((ply, state.to_fen(), legal, state.is_terminal()))
    return positions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build local test FEN positions from PGNS/PGN-like files using the Xiangqi rules engine"
    )
    parser.add_argument("--inputs", nargs="+", required=True, help="Input file(s), dirs, or glob(s)")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--recursive", action="store_true", help="Recursively scan input directories")
    parser.add_argument("--sample-every-n-plies", type=int, default=1, help="Emit every N plies (default: 1)")
    parser.add_argument("--max-games", type=int, default=0, help="Optional conversion cap for smoke runs")
    parser.add_argument("--emit-start-position", action="store_true", help="Also emit each game's start FEN")
    parser.add_argument(
        "--category-output-dir",
        default="",
        help="Optional directory for category-split JSONL outputs",
    )
    parser.add_argument("--summary-output", default="", help="Optional summary JSON output path")
    args = parser.parse_args()

    if args.sample_every_n_plies < 1:
        raise ValueError("--sample-every-n-plies must be >= 1")

    files = _iter_input_files(args.inputs, recursive=args.recursive)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    stats = ConversionStats(files_seen=len(files))
    failure_reasons: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()

    category_fps: dict[str, object] = {}
    if args.category_output_dir:
        category_dir = Path(args.category_output_dir)
        category_dir.mkdir(parents=True, exist_ok=True)
        for name in ["opening", "middlegame", "endgame", "near_terminal", "benchmark_start"]:
            category_fps[name] = (category_dir / f"{name}.jsonl").open("w", encoding="utf-8")

    with out_path.open("w", encoding="utf-8") as out_fp:
        try:
            for path in files:
                lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
                for game_idx, (start_fen, moves_iccs) in enumerate(_extract_games(lines), start=1):
                    stats.games_seen += 1
                    if args.max_games and stats.games_converted >= args.max_games:
                        break

                    try:
                        state = XiangqiState.from_fen(start_fen)
                        positions = _emit_positions(
                            state=state,
                            moves_iccs=moves_iccs,
                            emit_start_position=args.emit_start_position,
                            sample_every_n_plies=args.sample_every_n_plies,
                        )
                    except Exception as exc:
                        stats.parse_errors += 1
                        failure_reasons[f"{type(exc).__name__}: {exc}"] += 1
                        continue

                    for source_ply, fen, legal_count, is_terminal in positions:
                        category = _categorize_position(
                            ply=source_ply,
                            legal_count=legal_count,
                            is_terminal=is_terminal,
                        )
                        rec = {
                            "source_file": str(path),
                            "source_game_index": game_idx,
                            "source_ply": source_ply,
                            "fen": fen,
                            "category": category,
                        }
                        line = json.dumps(rec, ensure_ascii=False) + "\n"
                        out_fp.write(line)
                        if category in category_fps:
                            category_fps[category].write(line)
                        category_counts[category] += 1
                        stats.positions_emitted += 1
                    stats.games_converted += 1

                if args.max_games and stats.games_converted >= args.max_games:
                    break
        finally:
            for fp in category_fps.values():
                fp.close()

    payload = {
        **stats.__dict__,
        "failure_reasons": dict(sorted(failure_reasons.items(), key=lambda kv: kv[1], reverse=True)),
        "category_counts": dict(sorted(category_counts.items())),
    }
    if args.summary_output:
        summary_path = Path(args.summary_output)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
