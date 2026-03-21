from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .versions import VERSION_METADATA

BOARD_RANKS = 10
BOARD_FILES = 9
ACTION_SPACE_SIZE = BOARD_RANKS * BOARD_FILES * BOARD_RANKS * BOARD_FILES

RED = 1
BLACK = -1

PIECE_TO_PLANE = {
    "K": 0,
    "A": 1,
    "B": 2,
    "N": 3,
    "R": 4,
    "C": 5,
    "P": 6,
    "k": 7,
    "a": 8,
    "b": 9,
    "n": 10,
    "r": 11,
    "c": 12,
    "p": 13,
}

INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w"


def to_square(r: int, c: int) -> int:
    return r * BOARD_FILES + c


def from_square(sq: int) -> Tuple[int, int]:
    return sq // BOARD_FILES, sq % BOARD_FILES


def encode_action(from_sq: int, to_sq: int) -> int:
    return from_sq * 90 + to_sq


def decode_action(action: int) -> Tuple[int, int]:
    return action // 90, action % 90


def color_of(piece: str) -> int:
    return RED if piece.isupper() else BLACK


def in_palace(color: int, r: int, c: int) -> bool:
    if c < 3 or c > 5:
        return False
    if color == RED:
        return 7 <= r <= 9
    return 0 <= r <= 2


def crossed_river(color: int, r: int) -> bool:
    return r <= 4 if color == RED else r >= 5


@dataclass
class Move:
    from_sq: int
    to_sq: int


class XiangqiGame:
    def new_initial_state(self) -> "XiangqiState":
        return XiangqiState.from_fen(INITIAL_FEN)

    def num_distinct_actions(self) -> int:
        return ACTION_SPACE_SIZE

    def observation_tensor_shape(self) -> Tuple[int, int, int]:
        return (15, BOARD_RANKS, BOARD_FILES)


class XiangqiState:
    def __init__(self, board: List[List[str]], current_player: int, move_number: int = 0):
        self.board = board
        self._current_player = current_player
        self.move_number = move_number
        self._winner: Optional[int] = None
        self._terminal_reason: Optional[str] = None

    @classmethod
    def from_fen(cls, fen: str) -> "XiangqiState":
        board_part, side = fen.strip().split()[:2]
        ranks = board_part.split("/")
        if len(ranks) != BOARD_RANKS:
            raise ValueError("Invalid FEN rank count")
        board: List[List[str]] = []
        for rank in ranks:
            row: List[str] = []
            for ch in rank:
                if ch.isdigit():
                    row.extend(["."] * int(ch))
                else:
                    row.append(ch)
            if len(row) != BOARD_FILES:
                raise ValueError("Invalid FEN row width")
            board.append(row)
        current = RED if side.lower().startswith("w") else BLACK
        st = cls(board, current)
        st._recompute_winner()
        return st

    def clone(self) -> "XiangqiState":
        cloned = XiangqiState([row[:] for row in self.board], self._current_player, self.move_number)
        cloned._winner = self._winner
        cloned._terminal_reason = self._terminal_reason
        return cloned

    def current_player(self) -> int:
        return self._current_player

    def is_terminal(self) -> bool:
        if self._winner is not None:
            return True
        if not self.legal_actions():
            self._winner = -self._current_player
            self._terminal_reason = "no_legal_moves"
            return True
        return False

    def returns(self) -> List[float]:
        if not self.is_terminal():
            return [0.0, 0.0]
        if self._winner == RED:
            return [1.0, -1.0]
        if self._winner == BLACK:
            return [-1.0, 1.0]
        return [0.0, 0.0]

    def terminal_reason(self) -> str:
        if not self.is_terminal():
            return "none"
        return self._terminal_reason or "unknown"

    def observation_tensor(self) -> List[List[List[int]]]:
        planes = [[[0 for _ in range(BOARD_FILES)] for _ in range(BOARD_RANKS)] for _ in range(15)]
        for r in range(BOARD_RANKS):
            for c in range(BOARD_FILES):
                piece = self.board[r][c]
                if piece in PIECE_TO_PLANE:
                    planes[PIECE_TO_PLANE[piece]][r][c] = 1
        stm_value = 1 if self._current_player == RED else 0
        for r in range(BOARD_RANKS):
            for c in range(BOARD_FILES):
                planes[14][r][c] = stm_value
        return planes

    def legal_actions(self) -> List[int]:
        actions: List[int] = []
        for r in range(BOARD_RANKS):
            for c in range(BOARD_FILES):
                piece = self.board[r][c]
                if piece == "." or color_of(piece) != self._current_player:
                    continue
                from_sq = to_square(r, c)
                for nr, nc in self._pseudo_piece_moves(r, c, piece):
                    captured = self.board[nr][nc]
                    self.board[nr][nc] = piece
                    self.board[r][c] = "."
                    ok = not self._is_in_check(self._current_player)
                    self.board[r][c] = piece
                    self.board[nr][nc] = captured
                    if ok:
                        actions.append(encode_action(from_sq, to_square(nr, nc)))
        return sorted(set(actions))

    def apply_action(self, action: int) -> None:
        from_sq, to_sq = decode_action(action)
        fr, fc = from_square(from_sq)
        tr, tc = from_square(to_sq)
        piece = self.board[fr][fc]
        if piece == ".":
            raise ValueError("No piece at source")
        if color_of(piece) != self._current_player:
            raise ValueError("Wrong side piece")
        legal = set(self.legal_actions())
        if action not in legal:
            raise ValueError(f"Illegal action {action}")
        self.board[tr][tc] = piece
        self.board[fr][fc] = "."
        self._current_player = -self._current_player
        self.move_number += 1
        self._recompute_winner()

    def _locate_general(self, color: int) -> Optional[Tuple[int, int]]:
        target = "K" if color == RED else "k"
        for r in range(BOARD_RANKS):
            for c in range(BOARD_FILES):
                if self.board[r][c] == target:
                    return r, c
        return None

    def _recompute_winner(self) -> None:
        red_g = self._locate_general(RED)
        black_g = self._locate_general(BLACK)
        if red_g is None and black_g is None:
            self._winner = 0
            self._terminal_reason = "both_generals_missing"
        elif red_g is None:
            self._winner = BLACK
            self._terminal_reason = "red_general_captured"
        elif black_g is None:
            self._winner = RED
            self._terminal_reason = "black_general_captured"
        else:
            self._winner = None
            self._terminal_reason = None

    def _is_in_check(self, color: int) -> bool:
        g = self._locate_general(color)
        if g is None:
            return True
        gr, gc = g
        for r in range(BOARD_RANKS):
            for c in range(BOARD_FILES):
                piece = self.board[r][c]
                if piece == "." or color_of(piece) == color:
                    continue
                for nr, nc in self._pseudo_piece_moves(r, c, piece, attacks_only=True):
                    if nr == gr and nc == gc:
                        return True
        # flying general rule
        other = self._locate_general(-color)
        if other and other[1] == gc:
            step = 1 if other[0] > gr else -1
            rr = gr + step
            blocked = False
            while rr != other[0]:
                if self.board[rr][gc] != ".":
                    blocked = True
                    break
                rr += step
            if not blocked:
                return True
        return False

    def _pseudo_piece_moves(self, r: int, c: int, piece: str, attacks_only: bool = False) -> List[Tuple[int, int]]:
        color = color_of(piece)
        out: List[Tuple[int, int]] = []

        def add(nr: int, nc: int):
            if 0 <= nr < BOARD_RANKS and 0 <= nc < BOARD_FILES:
                target = self.board[nr][nc]
                if target == "." or color_of(target) != color:
                    out.append((nr, nc))

        kind = piece.upper()
        if kind == "K":
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if in_palace(color, nr, nc):
                    add(nr, nc)
            # flying general capture
            step = -1 if color == RED else 1
            rr = r + step
            while 0 <= rr < BOARD_RANKS:
                target = self.board[rr][c]
                if target != ".":
                    if target.upper() == "K" and color_of(target) != color:
                        out.append((rr, c))
                    break
                rr += step
        elif kind == "A":
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nr, nc = r + dr, c + dc
                if in_palace(color, nr, nc):
                    add(nr, nc)
        elif kind == "B":
            for dr, dc in [(-2, -2), (-2, 2), (2, -2), (2, 2)]:
                nr, nc = r + dr, c + dc
                eye_r, eye_c = r + dr // 2, c + dc // 2
                if not (0 <= nr < BOARD_RANKS and 0 <= nc < BOARD_FILES):
                    continue
                if self.board[eye_r][eye_c] != ".":
                    continue
                if color == RED and nr < 5:
                    continue
                if color == BLACK and nr > 4:
                    continue
                add(nr, nc)
        elif kind == "N":
            for dr, dc, lr, lc in [
                (-2, -1, -1, 0), (-2, 1, -1, 0), (2, -1, 1, 0), (2, 1, 1, 0),
                (-1, -2, 0, -1), (1, -2, 0, -1), (-1, 2, 0, 1), (1, 2, 0, 1),
            ]:
                leg_r, leg_c = r + lr, c + lc
                if not (0 <= leg_r < BOARD_RANKS and 0 <= leg_c < BOARD_FILES):
                    continue
                if self.board[leg_r][leg_c] != ".":
                    continue
                nr, nc = r + dr, c + dc
                add(nr, nc)
        elif kind == "R":
            out.extend(self._ray_moves(r, c, color, cannon=False))
        elif kind == "C":
            out.extend(self._ray_moves(r, c, color, cannon=True))
        elif kind == "P":
            dr = -1 if color == RED else 1
            add(r + dr, c)
            if crossed_river(color, r):
                add(r, c - 1)
                add(r, c + 1)
        return out

    def _ray_moves(self, r: int, c: int, color: int, cannon: bool) -> List[Tuple[int, int]]:
        out: List[Tuple[int, int]] = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            jumped = False
            while 0 <= nr < BOARD_RANKS and 0 <= nc < BOARD_FILES:
                target = self.board[nr][nc]
                if not cannon:
                    if target == ".":
                        out.append((nr, nc))
                    else:
                        if color_of(target) != color:
                            out.append((nr, nc))
                        break
                else:
                    if not jumped:
                        if target == ".":
                            out.append((nr, nc))
                        else:
                            jumped = True
                    else:
                        if target != ".":
                            if color_of(target) != color:
                                out.append((nr, nc))
                            break
                nr += dr
                nc += dc
        return out

    def to_fen(self) -> str:
        ranks = []
        for r in range(BOARD_RANKS):
            empties = 0
            out = ""
            for c in range(BOARD_FILES):
                piece = self.board[r][c]
                if piece == ".":
                    empties += 1
                else:
                    if empties:
                        out += str(empties)
                        empties = 0
                    out += piece
            if empties:
                out += str(empties)
            ranks.append(out)
        side = "w" if self._current_player == RED else "b"
        return f"{'/'.join(ranks)} {side}"

    def version_metadata(self) -> Dict[str, str]:
        return dict(VERSION_METADATA)
