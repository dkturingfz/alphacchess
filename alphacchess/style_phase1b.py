from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .notation import iccs_to_action
from .phase1_model import PolicyValueNet
from .versions import VERSION_METADATA
from .xiangqi_game import XiangqiState


@dataclass
class StylePositionSample:
    fen: str
    move_iccs: str
    ply: int
    source: str = "unknown"


@dataclass
class StyleEvalThresholds:
    unusable_lt: float
    gray_zone_gte: float
    gray_zone_lt: float
    usable_gte: float
    preferred_gte: float


@dataclass
class StyleEvalConfig:
    style_eval_name: str
    phase_split: Dict[str, Dict[str, Optional[int]]]
    metrics: List[str]
    thresholds: StyleEvalThresholds
    gray_zone_recovery: Dict[str, bool]


@dataclass
class StyleEvalMetrics:
    sample_count: int
    top1: float
    top3: float


def load_style_eval_config(path: str | Path) -> StyleEvalConfig:
    """Minimal YAML reader for configs/style_eval_v1.yaml without external deps."""
    text = Path(path).read_text()
    stack: List[Tuple[int, Dict]] = []
    root: Dict = {}

    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = line.strip()

        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if not stack:
                raise ValueError("Invalid YAML list placement")
            parent = stack[-1][1]
            parent.setdefault("__list__", []).append(_parse_yaml_scalar(item))
            continue

        if ":" not in stripped:
            raise ValueError(f"Invalid YAML line: {raw}")
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = root if not stack else stack[-1][1]

        if value == "":
            child: Dict = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_yaml_scalar(value)

    metrics = root.get("metrics", {}).get("__list__", [])
    if not isinstance(metrics, list):
        raise ValueError("metrics must be a list")

    thresholds_raw = root["top1_thresholds"]
    thresholds = StyleEvalThresholds(
        unusable_lt=float(thresholds_raw["unusable_lt"]),
        gray_zone_gte=float(thresholds_raw["gray_zone_gte"]),
        gray_zone_lt=float(thresholds_raw["gray_zone_lt"]),
        usable_gte=float(thresholds_raw["usable_gte"]),
        preferred_gte=float(thresholds_raw["preferred_gte"]),
    )

    phase_split: Dict[str, Dict[str, Optional[int]]] = {}
    for phase, cfg in root["phase_split"].items():
        phase_split[phase] = {
            "ply_start": int(cfg["ply_start"]),
            "ply_end": None if cfg["ply_end"] is None else int(cfg["ply_end"]),
        }

    return StyleEvalConfig(
        style_eval_name=str(root["style_eval_name"]),
        phase_split=phase_split,
        metrics=[str(m) for m in metrics],
        thresholds=thresholds,
        gray_zone_recovery={k: bool(v) for k, v in root["gray_zone_recovery"].items()},
    )


def _parse_yaml_scalar(value: str):
    if value in {"null", "Null", "NULL"}:
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.startswith("\"") and value.endswith("\""):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def config_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_style_position_samples(path: str | Path) -> List[StylePositionSample]:
    samples: List[StylePositionSample] = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if "fen" in rec and "move_iccs" in rec and "ply" in rec:
            samples.append(
                StylePositionSample(
                    fen=str(rec["fen"]),
                    move_iccs=str(rec["move_iccs"]),
                    ply=int(rec["ply"]),
                    source=str(rec.get("source", "positions_jsonl")),
                )
            )
            continue
        if "initial_fen" in rec and "moves_iccs" in rec:
            samples.extend(expand_game_record_to_samples(rec))
            continue
        raise ValueError("Unsupported style sample format")
    return samples


def expand_game_record_to_samples(record: Dict) -> List[StylePositionSample]:
    state = XiangqiState.from_fen(record["initial_fen"])
    samples: List[StylePositionSample] = []
    game_id = str(record.get("game_id", "unknown_game"))
    for ply_idx, move_iccs in enumerate(record["moves_iccs"], start=1):
        samples.append(
            StylePositionSample(
                fen=state.to_fen(),
                move_iccs=str(move_iccs),
                ply=ply_idx,
                source=game_id,
            )
        )
        action = iccs_to_action(move_iccs)
        if action not in state.legal_actions():
            raise ValueError(f"Illegal move {move_iccs} at ply={ply_idx} in {game_id}")
        state.apply_action(action)
    return samples


def phase_of_ply(ply: int, phase_split: Dict[str, Dict[str, Optional[int]]]) -> str:
    for phase in ("opening", "middlegame", "endgame"):
        cfg = phase_split.get(phase)
        if not cfg:
            continue
        start = int(cfg["ply_start"])
        end = cfg["ply_end"]
        if ply >= start and (end is None or ply <= int(end)):
            return phase
    raise ValueError(f"No phase rule matched ply={ply}")


def topk_match_for_sample(model: PolicyValueNet, sample: StylePositionSample) -> Tuple[bool, bool]:
    state = XiangqiState.from_fen(sample.fen)
    action = iccs_to_action(sample.move_iccs)
    legal_actions = state.legal_actions()
    if action not in legal_actions:
        raise ValueError(f"Target move {sample.move_iccs} is illegal for sample ply={sample.ply}")

    logits, _ = model.forward([state.observation_tensor()])
    legal_scored = sorted(((logits[0][a], a) for a in legal_actions), reverse=True)
    top1_action = legal_scored[0][1]
    top3_actions = [a for _, a in legal_scored[:3]]
    return top1_action == action, action in top3_actions


def evaluate_style_samples(
    model: PolicyValueNet,
    samples: Iterable[StylePositionSample],
    phase_split: Dict[str, Dict[str, Optional[int]]],
) -> Dict[str, StyleEvalMetrics]:
    by_phase: Dict[str, Dict[str, int]] = {
        "global": {"n": 0, "top1": 0, "top3": 0},
        "opening": {"n": 0, "top1": 0, "top3": 0},
        "middlegame": {"n": 0, "top1": 0, "top3": 0},
        "endgame": {"n": 0, "top1": 0, "top3": 0},
    }

    for sample in samples:
        top1_hit, top3_hit = topk_match_for_sample(model, sample)
        phase = phase_of_ply(sample.ply, phase_split)
        for bucket in ("global", phase):
            by_phase[bucket]["n"] += 1
            by_phase[bucket]["top1"] += 1 if top1_hit else 0
            by_phase[bucket]["top3"] += 1 if top3_hit else 0

    out: Dict[str, StyleEvalMetrics] = {}
    for key, v in by_phase.items():
        n = v["n"]
        out[key] = StyleEvalMetrics(
            sample_count=n,
            top1=(100.0 * v["top1"] / n) if n else 0.0,
            top3=(100.0 * v["top3"] / n) if n else 0.0,
        )
    return out


def classify_style_quality(global_top1: float, thresholds: StyleEvalThresholds) -> str:
    if global_top1 < thresholds.unusable_lt:
        return "unusable"
    if thresholds.gray_zone_gte <= global_top1 < thresholds.gray_zone_lt:
        return "gray"
    if global_top1 >= thresholds.preferred_gte:
        return "preferred"
    if global_top1 >= thresholds.usable_gte:
        return "usable"
    raise ValueError("Threshold configuration is inconsistent")


def mirror_iccs(move_iccs: str) -> str:
    files = "abcdefghi"
    mirror = {c: files[-(i + 1)] for i, c in enumerate(files)}
    return f"{mirror[move_iccs[0]]}{move_iccs[1]}{mirror[move_iccs[2]]}{move_iccs[3]}"


def mirror_fen_lr(fen: str) -> str:
    board_part, side = fen.split()[:2]
    mirrored_ranks: List[str] = []
    for rank in board_part.split("/"):
        expanded: List[str] = []
        for ch in rank:
            if ch.isdigit():
                expanded.extend(["."] * int(ch))
            else:
                expanded.append(ch)
        expanded.reverse()
        compact = []
        run = 0
        for ch in expanded:
            if ch == ".":
                run += 1
            else:
                if run:
                    compact.append(str(run))
                    run = 0
                compact.append(ch)
        if run:
            compact.append(str(run))
        mirrored_ranks.append("".join(compact))
    return f"{'/'.join(mirrored_ranks)} {side}"


def augment_samples_lr_mirror(samples: Iterable[StylePositionSample]) -> List[StylePositionSample]:
    augmented = list(samples)
    for s in samples:
        augmented.append(
            StylePositionSample(
                fen=mirror_fen_lr(s.fen),
                move_iccs=mirror_iccs(s.move_iccs),
                ply=s.ply,
                source=f"{s.source}:lr_mirror",
            )
        )
    return augmented


def build_style_checkpoint_metadata(
    checkpoint_schema_version: str,
    frozen: bool,
    extra: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    metadata = dict(VERSION_METADATA)
    metadata["checkpoint_schema_version"] = checkpoint_schema_version
    metadata["frozen_style_reference"] = "true" if frozen else "false"
    if extra:
        metadata.update({k: str(v) for k, v in extra.items()})
    return metadata


def train_style_policy(
    model: PolicyValueNet,
    samples: List[StylePositionSample],
    epochs: int,
    lr: float,
    batch_size: int,
    value_loss_weight: float = 0.0,
) -> Dict[str, float]:
    if not samples:
        raise ValueError("No training samples provided")

    total_steps = 0
    last_loss = 0.0
    for _ in range(epochs):
        for i in range(0, len(samples), batch_size):
            batch = samples[i : i + batch_size]
            obs = []
            pol = []
            val = []
            for s in batch:
                st = XiangqiState.from_fen(s.fen)
                action = iccs_to_action(s.move_iccs)
                legal = st.legal_actions()
                if action not in legal:
                    raise ValueError(f"Illegal style move {s.move_iccs} for ply={s.ply}")
                target = [0.0] * model.config.policy_size
                target[action] = 1.0
                obs.append(st.observation_tensor())
                pol.append(target)
                val.append(0.0)
            metrics = model.train_batch(obs, pol, val, lr=lr, value_loss_weight=value_loss_weight)
            total_steps += 1
            last_loss = metrics["loss"]
    return {"steps": float(total_steps), "last_loss": float(last_loss)}


def make_style_eval_payload(
    *,
    eval_config_path: str | Path,
    model_checkpoint: str | Path,
    checkpoint_metadata: Dict[str, str],
    metrics: Dict[str, StyleEvalMetrics],
    quality_zone: str,
    dataset_path: str | Path,
    notes: str = "",
) -> Dict:
    payload = {
        "metadata": dict(VERSION_METADATA),
        "style_eval_config_name": load_style_eval_config(eval_config_path).style_eval_name,
        "style_eval_config_hash": config_hash(eval_config_path),
        "checkpoint": str(model_checkpoint),
        "checkpoint_metadata": checkpoint_metadata,
        "dataset_path": str(dataset_path),
        "quality_zone": quality_zone,
        "global_top1": metrics["global"].top1,
        "global_top3": metrics["global"].top3,
        "opening_top1": metrics["opening"].top1,
        "opening_top3": metrics["opening"].top3,
        "middlegame_top1": metrics["middlegame"].top1,
        "middlegame_top3": metrics["middlegame"].top3,
        "endgame_top1": metrics["endgame"].top1,
        "endgame_top3": metrics["endgame"].top3,
        "sample_count_global": metrics["global"].sample_count,
        "sample_count_opening": metrics["opening"].sample_count,
        "sample_count_middlegame": metrics["middlegame"].sample_count,
        "sample_count_endgame": metrics["endgame"].sample_count,
        "notes": notes,
    }
    return payload
