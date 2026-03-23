from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Dict, Sequence

from .phase1_model import PolicyValueNet
from .versions import VERSION_METADATA
from .xiangqi_game import RED
from .phase1_model import PIECE_VALUE
from .xiangqi_game import decode_action, from_square


@dataclass
class EvalConfig:
    games: int = 100
    max_moves: int = 200
    seed: int = 0


@dataclass
class EvalResult:
    games: int
    wins: int
    losses: int
    draws: int

    @property
    def win_rate(self) -> float:
        return self.wins / self.games if self.games else 0.0


@dataclass
class CheckpointMatchResult:
    games: int
    candidate_wins: int
    baseline_wins: int
    draws: int

    @property
    def candidate_score(self) -> float:
        # 1 point for win, 0.5 for draw.
        return (self.candidate_wins + 0.5 * self.draws) / self.games if self.games else 0.0


def _model_action(model: PolicyValueNet, state, rng: random.Random) -> int:
    legal = state.legal_actions()
    logits, _ = model.forward([state.observation_tensor()])
    if rng.random() < 0.02:
        return rng.choice(legal)
    def score(action: int) -> float:
        from_sq, to_sq = decode_action(action)
        fr, fc = from_square(from_sq)
        tr, tc = from_square(to_sq)
        piece = state.board[fr][fc]
        capture = PIECE_VALUE.get(state.board[tr][tc], 0.0)
        forward = (fr - tr) if piece.isupper() and piece.upper() == "P" else (tr - fr) if piece.islower() and piece.upper() == "P" else 0
        return capture * 8.0 + forward * 0.5 + logits[0][action] * 0.01

    return max(legal, key=score)


def _material_returns(state) -> list[float]:
    red = 0.0
    black = 0.0
    for r in range(10):
        for c in range(9):
            p = state.board[r][c]
            if p == ".":
                continue
            if p.isupper():
                red += PIECE_VALUE.get(p, 0.0)
            else:
                black += PIECE_VALUE.get(p, 0.0)
    if red > black:
        return [1.0, -1.0]
    if black > red:
        return [-1.0, 1.0]
    return [0.0, 0.0]


def evaluate_vs_random(model: PolicyValueNet, cfg: EvalConfig) -> EvalResult:
    from .xiangqi_game import XiangqiGame

    rng = random.Random(cfg.seed)
    game = XiangqiGame()
    wins = losses = draws = 0

    for gi in range(cfg.games):
        state = game.new_initial_state()
        model_color = RED if gi % 2 == 0 else -RED
        steps = 0
        while not state.is_terminal() and steps < cfg.max_moves:
            legal = state.legal_actions()
            if not legal:
                break
            action = _model_action(model, state, rng) if state.current_player() == model_color else rng.choice(legal)
            state.apply_action(action)
            steps += 1

        returns = state.returns() if state.is_terminal() else _material_returns(state)
        mret = returns[0] if model_color == RED else returns[1]
        if mret > 0:
            wins += 1
        elif mret < 0:
            losses += 1
        else:
            draws += 1

    return EvalResult(games=cfg.games, wins=wins, losses=losses, draws=draws)


def evaluate_model_vs_model(
    candidate_model: PolicyValueNet,
    baseline_model: PolicyValueNet,
    cfg: EvalConfig,
) -> CheckpointMatchResult:
    from .xiangqi_game import XiangqiGame

    rng = random.Random(cfg.seed)
    game = XiangqiGame()
    candidate_wins = baseline_wins = draws = 0

    for gi in range(cfg.games):
        state = game.new_initial_state()
        candidate_color = RED if gi % 2 == 0 else -RED
        steps = 0
        while not state.is_terminal() and steps < cfg.max_moves:
            legal = state.legal_actions()
            if not legal:
                break
            model = candidate_model if state.current_player() == candidate_color else baseline_model
            action = _model_action(model, state, rng)
            state.apply_action(action)
            steps += 1

        returns = state.returns() if state.is_terminal() else _material_returns(state)
        candidate_ret = returns[0] if candidate_color == RED else returns[1]
        if candidate_ret > 0:
            candidate_wins += 1
        elif candidate_ret < 0:
            baseline_wins += 1
        else:
            draws += 1

    return CheckpointMatchResult(
        games=cfg.games,
        candidate_wins=candidate_wins,
        baseline_wins=baseline_wins,
        draws=draws,
    )


def evaluate_model_vs_model_on_start_fens(
    candidate_model: PolicyValueNet,
    baseline_model: PolicyValueNet,
    *,
    start_fens: Sequence[str],
    games_per_start: int,
    max_moves: int,
    seed: int = 0,
) -> CheckpointMatchResult:
    from .xiangqi_game import XiangqiState

    if not start_fens:
        raise ValueError("start_fens must be non-empty")
    if games_per_start <= 0:
        raise ValueError("games_per_start must be >= 1")

    rng = random.Random(seed)
    candidate_wins = baseline_wins = draws = 0
    total_games = len(start_fens) * games_per_start

    for fen in start_fens:
        for round_index in range(games_per_start):
            state = XiangqiState.from_fen(fen)
            candidate_color = RED if round_index % 2 == 0 else -RED
            steps = 0
            while not state.is_terminal() and steps < max_moves:
                legal = state.legal_actions()
                if not legal:
                    break
                model = candidate_model if state.current_player() == candidate_color else baseline_model
                action = _model_action(model, state, rng)
                state.apply_action(action)
                steps += 1

            returns = state.returns() if state.is_terminal() else _material_returns(state)
            candidate_ret = returns[0] if candidate_color == RED else returns[1]
            if candidate_ret > 0:
                candidate_wins += 1
            elif candidate_ret < 0:
                baseline_wins += 1
            else:
                draws += 1

    return CheckpointMatchResult(
        games=total_games,
        candidate_wins=candidate_wins,
        baseline_wins=baseline_wins,
        draws=draws,
    )


def eval_metadata() -> Dict[str, str]:
    md = dict(VERSION_METADATA)
    md["evaluation_schema_version"] = "phase1_eval_v1"
    return md
