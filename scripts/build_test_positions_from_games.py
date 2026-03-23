#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.notation import iccs_to_action
from alphacchess.xiangqi_game import INITIAL_FEN, XiangqiState

ICCS_MOVE_RE = re.compile(r"\b([a-i][0-9][a-i][0-9])\b", flags=re.IGNORECASE)
FEN_TAG_RE = re.compile(r"\[FEN\s+\"([^\"]+)\"\]", flags=re.IGNORECASE)


@dataclass
class ConversionStats:
    files_seen: int = 0
    games_seen: int = 0
    games_converted: int = 0
    positions_emitted: int = 0
    parse_errors: int = 0


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

        for move in ICCS_MOVE_RE.findall(line):
            current_moves.append(move.lower())

    game = flush()
    if game:
        yield game


def _iter_input_files(inputs: list[str], recursive: bool) -> list[Path]:
    files: list[Path] = []
    for value in inputs:
        path = Path(value)
        if any(ch in value for ch in "*?[]"):
            files.extend(sorted(Path().glob(value)))
        elif path.is_dir():
            pattern = "**/*" if recursive else "*"
            files.extend(sorted(p for p in path.glob(pattern) if p.is_file()))
        elif path.exists():
            files.append(path)
    return files


def _emit_positions(
    state: XiangqiState,
    moves_iccs: list[str],
    emit_start_position: bool,
    sample_every_n_plies: int,
) -> list[str]:
    positions: list[str] = []
    if emit_start_position:
        positions.append(state.to_fen())
    for ply, move in enumerate(moves_iccs, start=1):
        state.apply_action(iccs_to_action(move))
        if sample_every_n_plies <= 1 or ply % sample_every_n_plies == 0:
            positions.append(state.to_fen())
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
    args = parser.parse_args()

    if args.sample_every_n_plies < 1:
        raise ValueError("--sample-every-n-plies must be >= 1")

    files = _iter_input_files(args.inputs, recursive=args.recursive)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    stats = ConversionStats(files_seen=len(files))
    with out_path.open("w", encoding="utf-8") as out_fp:
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
                except Exception:
                    stats.parse_errors += 1
                    continue

                for ply, fen in enumerate(positions):
                    out_fp.write(
                        json.dumps(
                            {
                                "source_file": str(path),
                                "source_game_index": game_idx,
                                "ply_index": ply,
                                "fen": fen,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    stats.positions_emitted += 1
                stats.games_converted += 1

            if args.max_games and stats.games_converted >= args.max_games:
                break

    print(json.dumps(stats.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
