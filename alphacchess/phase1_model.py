from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .xiangqi_game import XiangqiGame, decode_action, from_square


PIECE_BY_PLANE = {
    0: "K",
    1: "A",
    2: "B",
    3: "N",
    4: "R",
    5: "C",
    6: "P",
    7: "k",
    8: "a",
    9: "b",
    10: "n",
    11: "r",
    12: "c",
    13: "p",
}

PIECE_VALUE = {
    ".": 0.0,
    "K": 1000.0,
    "A": 2.0,
    "B": 2.0,
    "N": 4.0,
    "R": 9.0,
    "C": 5.0,
    "P": 1.0,
    "k": 1000.0,
    "a": 2.0,
    "b": 2.0,
    "n": 4.0,
    "r": 9.0,
    "c": 5.0,
    "p": 1.0,
}


@dataclass
class ModelConfig:
    input_shape: Tuple[int, int, int]
    policy_size: int


class PolicyValueNet:
    """Phase 1 heuristic-trainable policy/value model (pure Python, no external deps)."""

    def __init__(self, config: ModelConfig, seed: int = 0):
        self.config = config
        self.rng = random.Random(seed)
        self.capture_weight = 4.0
        self.piece_weight = 0.0
        self.forward_weight = 0.3
        self.value_material_weight = 0.04

    @classmethod
    def for_xiangqi_v1(cls, seed: int = 0, hidden_size: int = 0) -> "PolicyValueNet":
        game = XiangqiGame()
        cfg = ModelConfig(
            input_shape=game.observation_tensor_shape(),
            policy_size=game.num_distinct_actions(),
        )
        return cls(cfg, seed=seed)

    def _board_from_obs(self, obs: List[List[List[float]]]) -> tuple[list[list[str]], int]:
        board = [["." for _ in range(9)] for _ in range(10)]
        for plane_idx, piece in PIECE_BY_PLANE.items():
            plane = obs[plane_idx]
            for r in range(10):
                row = plane[r]
                for c in range(9):
                    if row[c] > 0.5:
                        board[r][c] = piece
        stm = 1 if obs[14][0][0] > 0.5 else -1
        return board, stm

    def _action_features(self, board: List[List[str]], stm: int, action: int) -> tuple[float, float, float]:
        from_sq, to_sq = decode_action(action)
        fr, fc = from_square(from_sq)
        tr, tc = from_square(to_sq)
        piece = board[fr][fc]
        if piece == ".":
            return -5.0, 0.0, 0.0
        if (stm == 1 and piece.islower()) or (stm == -1 and piece.isupper()):
            return -5.0, 0.0, 0.0
        target = board[tr][tc]
        capture = PIECE_VALUE[target]
        own_piece = PIECE_VALUE[piece]
        if piece.upper() == "P":
            forward = (fr - tr) if piece.isupper() else (tr - fr)
        else:
            forward = 0.0
        return capture, own_piece, float(forward)

    def _value_from_board(self, board: List[List[str]], stm: int) -> float:
        red = 0.0
        black = 0.0
        for r in range(10):
            for c in range(9):
                p = board[r][c]
                if p == ".":
                    continue
                if p.isupper():
                    red += PIECE_VALUE[p]
                else:
                    black += PIECE_VALUE[p]
        mat = red - black
        if stm == -1:
            mat = -mat
        return math.tanh(mat * self.value_material_weight)

    def forward(self, obs_batch: List[List[List[List[float]]]]) -> tuple[List[List[float]], List[float]]:
        logits_batch: List[List[float]] = []
        values: List[float] = []
        for obs in obs_batch:
            board, stm = self._board_from_obs(obs)
            logits = [-50.0] * self.config.policy_size
            for fr in range(10):
                for fc in range(9):
                    piece = board[fr][fc]
                    if piece == ".":
                        continue
                    if (stm == 1 and piece.islower()) or (stm == -1 and piece.isupper()):
                        continue
                    from_sq = fr * 9 + fc
                    own_piece = PIECE_VALUE[piece]
                    for tr in range(10):
                        for tc in range(9):
                            to_sq = tr * 9 + tc
                            action = from_sq * 90 + to_sq
                            target = board[tr][tc]
                            capture = PIECE_VALUE[target]
                            if piece.upper() == "P":
                                forward = float(fr - tr) if piece.isupper() else float(tr - fr)
                            else:
                                forward = 0.0
                            logits[action] = (
                                self.capture_weight * capture
                                + self.piece_weight * own_piece
                                + self.forward_weight * forward
                            )
            logits_batch.append(logits)
            values.append(self._value_from_board(board, stm))
        return logits_batch, values

    def train_batch(
        self,
        obs: List[List[List[List[float]]]],
        policy_target: List[List[float]],
        value_target: List[float],
        lr: float = 1e-3,
        value_loss_weight: float = 1.0,
    ) -> Dict[str, float]:
        capture_grad = 0.0
        piece_grad = 0.0
        forward_grad = 0.0
        value_grad = 0.0
        policy_loss = 0.0
        value_loss = 0.0

        n = max(len(obs), 1)
        for i in range(len(obs)):
            board, stm = self._board_from_obs(obs[i])
            chosen = max(range(len(policy_target[i])), key=lambda a: policy_target[i][a])
            c, p, f = self._action_features(board, stm, chosen)
            capture_grad += c
            piece_grad += p
            forward_grad += f

            v_pred = self._value_from_board(board, stm)
            v_err = value_target[i] - v_pred
            value_grad += v_err
            value_loss += v_err * v_err
            policy_loss += 0.0 if policy_target[i][chosen] > 0.0 else 1.0

        self.capture_weight += lr * capture_grad / n * 0.01
        self.piece_weight += lr * piece_grad / n * 0.01
        self.forward_weight += lr * forward_grad / n * 0.01
        self.value_material_weight += lr * value_grad / n * 0.01 * value_loss_weight

        return {
            "loss": float(policy_loss / n + value_loss / n),
            "policy_loss": float(policy_loss / n),
            "value_loss": float(value_loss / n),
        }

    def save_checkpoint(self, path: str | Path, metadata: Dict[str, str]) -> None:
        payload = {
            "model_config": {
                "input_shape": list(self.config.input_shape),
                "policy_size": self.config.policy_size,
            },
            "weights": {
                "capture_weight": self.capture_weight,
                "piece_weight": self.piece_weight,
                "forward_weight": self.forward_weight,
                "value_material_weight": self.value_material_weight,
            },
            "metadata": metadata,
        }
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2))

    @classmethod
    def load_checkpoint(cls, path: str | Path) -> tuple["PolicyValueNet", Dict[str, str]]:
        payload = json.loads(Path(path).read_text())
        cfg = payload["model_config"]
        model = cls(ModelConfig(input_shape=tuple(cfg["input_shape"]), policy_size=cfg["policy_size"]))
        weights = payload["weights"]
        model.capture_weight = float(weights["capture_weight"])
        model.piece_weight = float(weights["piece_weight"])
        model.forward_weight = float(weights["forward_weight"])
        model.value_material_weight = float(weights["value_material_weight"])
        return model, payload["metadata"]
