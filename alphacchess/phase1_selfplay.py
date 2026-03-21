from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Dict, List, Sequence

from .phase1_model import PIECE_VALUE, PolicyValueNet
from .phase1_replay import ReplayDataset, ReplaySample, make_replay_metadata
from .xiangqi_game import BLACK, RED, XiangqiState, decode_action, from_square


@dataclass
class SelfPlayConfig:
    games: int = 20
    max_moves: int = 200
    exploration_eps: float = 0.20
    policy_temperature: float = 1.0


@dataclass
class SelfPlaySummary:
    games: int
    samples: int
    red_wins: int
    black_wins: int
    draws: int


def _masked_policy_probs(logits: List[float], legal_actions: Sequence[int], temperature: float = 1.0) -> List[float]:
    t = max(temperature, 1e-6)
    legal_vals = [(a, logits[a] / t) for a in legal_actions]
    max_logit = max(v for _, v in legal_vals)
    exps = [(a, math.exp(v - max_logit)) for a, v in legal_vals]
    denom = sum(v for _, v in exps)
    probs = [0.0] * 8100
    for a, ev in exps:
        probs[a] = ev / denom if denom > 0 else 1.0 / len(legal_actions)
    return probs


def _heuristic_probs(state: XiangqiState, legal_actions: Sequence[int]) -> List[float]:
    scores = [0.0] * 8100
    for a in legal_actions:
        _, to_sq = decode_action(a)
        tr, tc = from_square(to_sq)
        target = state.board[tr][tc]
        scores[a] = PIECE_VALUE.get(target, 0.0) + 0.01
    total = sum(scores[a] for a in legal_actions)
    if total <= 0:
        uniform = 1.0 / len(legal_actions)
        for a in legal_actions:
            scores[a] = uniform
        return scores
    for a in legal_actions:
        scores[a] /= total
    return scores


def choose_action(
    state: XiangqiState,
    model: PolicyValueNet,
    rng: random.Random,
    exploration_eps: float,
    temperature: float,
) -> int:
    legal = state.legal_actions()
    if not legal:
        raise ValueError("No legal actions")

    logits, _ = model.forward([state.observation_tensor()])
    model_probs = _masked_policy_probs(logits[0], legal, temperature)
    heuristic_probs = _heuristic_probs(state, legal)
    mixed = [0.0] * 8100
    for a in legal:
        mixed[a] = 0.75 * model_probs[a] + 0.25 * heuristic_probs[a]

    def tactical_score(action: int) -> float:
        from_sq, to_sq = decode_action(action)
        fr, fc = from_square(from_sq)
        tr, tc = from_square(to_sq)
        piece = state.board[fr][fc]
        capture = PIECE_VALUE.get(state.board[tr][tc], 0.0)
        forward = (fr - tr) if piece.isupper() and piece.upper() == "P" else (tr - fr) if piece.islower() and piece.upper() == "P" else 0
        return capture * 8.0 + forward * 0.5

    if rng.random() < exploration_eps:
        action = rng.choice(list(legal))
    else:
        action = max(legal, key=lambda a: mixed[a] + 0.01 * tactical_score(a))

    return action


def run_selfplay(model: PolicyValueNet, cfg: SelfPlayConfig, seed: int = 0) -> tuple[ReplayDataset, SelfPlaySummary]:
    from .xiangqi_game import XiangqiGame

    rng = random.Random(seed)
    game = XiangqiGame()

    all_samples: List[ReplaySample] = []
    red_wins = black_wins = draws = 0

    for _ in range(cfg.games):
        state = game.new_initial_state()
        game_positions: List[Dict] = []
        moves = 0

        while not state.is_terminal() and moves < cfg.max_moves:
            action = choose_action(state, model, rng, cfg.exploration_eps, cfg.policy_temperature)
            game_positions.append(
                {
                    "obs": state.observation_tensor(),
                    "policy_action": action,
                    "player": state.current_player(),
                }
            )
            state.apply_action(action)
            moves += 1

        returns = state.returns() if state.is_terminal() else [0.0, 0.0]
        if returns[0] > returns[1]:
            red_wins += 1
        elif returns[1] > returns[0]:
            black_wins += 1
        else:
            draws += 1

        for p in game_positions:
            player = p["player"]
            v = returns[0] if player == RED else returns[1] if player == BLACK else 0.0
            all_samples.append(
                ReplaySample(
                    observation=p["obs"],
                    policy_action=p["policy_action"],
                    value_target=float(v),
                    player=player,
                )
            )

    return ReplayDataset(metadata=make_replay_metadata(), samples=all_samples), SelfPlaySummary(
        games=cfg.games,
        samples=len(all_samples),
        red_wins=red_wins,
        black_wins=black_wins,
        draws=draws,
    )
