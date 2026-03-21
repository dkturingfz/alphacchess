from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from .xiangqi_game import decode_action, encode_action, from_square, to_square

FILES = "abcdefghi"


def action_to_iccs(action: int) -> str:
    from_sq, to_sq = decode_action(action)
    fr, fc = from_square(from_sq)
    tr, tc = from_square(to_sq)
    return f"{FILES[fc]}{9-fr}{FILES[tc]}{9-tr}"


def iccs_to_action(move: str) -> int:
    move = move.strip()
    if len(move) != 4:
        raise ValueError(f"Invalid ICCS: {move}")
    fc = FILES.index(move[0])
    fr = 9 - int(move[1])
    tc = FILES.index(move[2])
    tr = 9 - int(move[3])
    return encode_action(to_square(fr, fc), to_square(tr, tc))


class NotationAdapter:
    """Phase 0 notation adapter: FEN + ICCS + plain text moves."""

    def normalize_record(self, record: Dict) -> Dict:
        fen = record["initial_fen"].strip()
        moves = [m.strip() for m in record.get("moves_iccs", []) if m.strip()]
        return {"initial_fen": fen, "moves_iccs": moves}

    def load_plain_text(self, path: str) -> List[Dict]:
        lines = [ln.strip() for ln in Path(path).read_text().splitlines() if ln.strip() and not ln.strip().startswith("#")]
        out = []
        for line in lines:
            if "|" not in line:
                raise ValueError("Expected `FEN | move1 move2 ...` format")
            fen, moves = line.split("|", 1)
            out.append(self.normalize_record({"initial_fen": fen, "moves_iccs": moves.split()}))
        return out

    def load_jsonl(self, path: str) -> List[Dict]:
        out = []
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            out.append(self.normalize_record(rec))
        return out
