#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

FROZEN_PROTOCOL = {
    "start_fens_file": "data/benchmark_positions/samples/benchmark_start_fens_sample.txt",
    "max_start_positions": 8,
    "games_per_start": 4,
    "max_moves": 60,
    "seeds": "17,29,41,53",
}

KEY_PANEL = [(1, 0), (3, 0), (2, 1)]


@dataclass
class RunRecord:
    run_index: int
    route_family: str
    route_goal: str
    route_non_overlap_reason: str
    run_dir: str
    train_config: dict[str, Any]
    quality: dict[str, Any]
    key_panel_results: list[dict[str, Any]]
    anchor_curve_vs_iter000: list[dict[str, Any]]
    representative_adjacent: list[dict[str, Any]]
    representative_large_span: list[dict[str, Any]]
    classification: str
    route_status: str
    next_plan: str


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _quality(summary: dict[str, Any]) -> dict[str, Any]:
    rows = summary["iterations"]
    per_iter = []
    checkpoint_scores = []
    for row in rows:
        total = row["natural_terminations"] + row["step_cap_truncations"]
        trunc_ratio = (row["step_cap_truncations"] / total) if total else 0.0
        cprev = row.get("checkpoint_eval_vs_previous")
        cscore = cprev.get("candidate_score") if cprev else None
        if cscore is not None:
            checkpoint_scores.append(float(cscore))
        per_iter.append(
            {
                "iteration": int(row["iteration"]),
                "natural_terminations": int(row["natural_terminations"]),
                "truncation_ratio": trunc_ratio,
                "value_non_zero_fraction": float(row["value_non_zero_fraction"]),
                "checkpoint_eval_vs_previous": cscore,
                "quick_eval_win_rate": float(row["quick_eval_win_rate"]),
            }
        )
    return {
        "per_iteration": per_iter,
        "natural_terminations_mean": mean(i["natural_terminations"] for i in per_iter),
        "truncation_ratio_mean": mean(i["truncation_ratio"] for i in per_iter),
        "value_non_zero_fraction_mean": mean(i["value_non_zero_fraction"] for i in per_iter),
        "quick_eval_win_rate_mean": mean(i["quick_eval_win_rate"] for i in per_iter),
        "checkpoint_eval_vs_previous_mean": mean(checkpoint_scores) if checkpoint_scores else None,
    }


def _train(run_dir: Path, cfg: dict[str, Any], seed: int) -> dict[str, Any]:
    out = run_dir / "train"
    _run(
        [
            "python",
            "scripts/train_selfplay.py",
            "--iterations",
            str(cfg["iterations"]),
            "--games-per-iter",
            str(cfg["games_per_iter"]),
            "--max-moves",
            str(cfg["max_moves"]),
            "--terminal-enrichment-games",
            str(cfg["terminal_enrichment_games"]),
            "--terminal-enrichment-max-moves",
            str(cfg["terminal_enrichment_max_moves"]),
            "--epochs",
            str(cfg["epochs"]),
            "--batch-size",
            str(cfg["batch_size"]),
            "--quick-eval-games",
            str(cfg["quick_eval_games"]),
            "--checkpoint-eval-games",
            str(cfg["checkpoint_eval_games"]),
            "--checkpoint-eval-max-moves",
            str(cfg["checkpoint_eval_max_moves"]),
            "--seed",
            str(seed),
            "--out-dir",
            str(out),
        ]
    )
    return _read_json(out / "train_summary.json")


def _eval_pair(run_dir: Path, cand: int, base: int) -> dict[str, Any]:
    out_file = run_dir / "benchmark_start_sanity" / f"iter_{cand:03d}_vs_iter_{base:03d}.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "python",
            "scripts/run_benchmark_start_sanity.py",
            "--candidate",
            str(run_dir / "train" / "checkpoints" / f"iter_{cand:03d}.json"),
            "--baseline",
            str(run_dir / "train" / "checkpoints" / f"iter_{base:03d}.json"),
            "--start-fens",
            FROZEN_PROTOCOL["start_fens_file"],
            "--max-start-positions",
            str(FROZEN_PROTOCOL["max_start_positions"]),
            "--games-per-start",
            str(FROZEN_PROTOCOL["games_per_start"]),
            "--max-moves",
            str(FROZEN_PROTOCOL["max_moves"]),
            "--seeds",
            FROZEN_PROTOCOL["seeds"],
            "--out",
            str(out_file),
        ]
    )
    payload = _read_json(out_file)
    agg = payload["aggregate"]
    return {
        "pair": [cand, base],
        "candidate_score": float(agg["candidate_score"]),
        "seed_stddev": float(agg["candidate_score_stddev_across_seeds"]),
        "games": int(agg["games"]),
        "games_expected": int(agg["games_expected"]),
        "path": str(out_file),
    }


def _find_pair(rows: list[dict[str, Any]], cand: int, base: int) -> dict[str, Any] | None:
    for row in rows:
        if row["pair"] == [cand, base]:
            return row
    return None


def _compute_pairs(iterations: list[int]) -> list[tuple[int, int]]:
    its = sorted(iterations)
    pairs: list[tuple[int, int]] = []

    for cand, base in KEY_PANEL:
        if cand in its and base in its and cand > base:
            pairs.append((cand, base))

    for it in its:
        if it > 0 and (it, 0) not in pairs:
            pairs.append((it, 0))

    latest = max(its) if its else 0
    for cand, base in [(latest, latest - 1), (latest - 1, latest - 2)]:
        if cand > base >= 0 and cand in its and base in its and (cand, base) not in pairs:
            pairs.append((cand, base))

    for cand, base in [(latest, latest - 2), (latest, max(0, latest - 3))]:
        if cand > base >= 0 and cand in its and base in its and (cand, base) not in pairs:
            pairs.append((cand, base))

    return pairs


def _anchor_curve(all_pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = [p for p in all_pairs if p["pair"][1] == 0 and p["pair"][0] > 0]
    return sorted(out, key=lambda x: x["pair"][0])


def _classify(prev: RunRecord | None, quality: dict[str, Any], anchors: list[dict[str, Any]], key_panel: list[dict[str, Any]]) -> str:
    if prev is None:
        return "no_improvement"

    signal_improved = (
        quality["value_non_zero_fraction_mean"] >= prev.quality["value_non_zero_fraction_mean"] + 0.02
        or quality["truncation_ratio_mean"] <= prev.quality["truncation_ratio_mean"] - 0.05
        or quality["natural_terminations_mean"] >= prev.quality["natural_terminations_mean"] + 1.0
    )

    anchor_mean = mean(x["candidate_score"] for x in anchors) if anchors else 0.0
    prev_anchor_mean = mean(x["candidate_score"] for x in prev.anchor_curve_vs_iter000) if prev.anchor_curve_vs_iter000 else 0.0
    directional_improved = anchor_mean >= prev_anchor_mean + 0.02

    p10 = _find_pair(key_panel, 1, 0)
    p30 = _find_pair(key_panel, 3, 0)
    long_negative = (p10 and p10["candidate_score"] < 0.5) and (p30 and p30["candidate_score"] < 0.5)

    if signal_improved and directional_improved and not long_negative:
        return "true_improvement"
    if signal_improved and (not directional_improved or long_negative):
        return "fake_improvement"
    return "no_improvement"


def _route_status(classification: str, anchors: list[dict[str, Any]], no_gain_streak: int) -> str:
    if classification == "true_improvement":
        return "继续深入"
    best_anchor = max((x["candidate_score"] for x in anchors), default=0.0)
    if best_anchor >= 0.5:
        return "暂时保留"
    if no_gain_streak >= 2:
        return "淘汰"
    return "暂时保留"


def _success_condition(records: list[RunRecord]) -> tuple[bool, str]:
    if len(records) < 2:
        return False, ""
    latest = records[-1]
    anchors = latest.anchor_curve_vs_iter000
    over = [x for x in anchors if x["candidate_score"] >= 0.5]
    if len(over) >= 2:
        recent = records[-2:] if len(records) >= 2 else records
        stable = all(max((a["candidate_score"] for a in r.anchor_curve_vs_iter000), default=0.0) >= 0.5 for r in recent)
        if stable:
            return True, "A_stable_positive_anchor"

    if len(anchors) >= 3:
        scores = [x["candidate_score"] for x in anchors]
        if scores[-1] >= scores[0] + 0.08 and mean(scores[-2:]) >= 0.49:
            return True, "C_trend_up"

    return False, ""


def _failure_condition(records: list[RunRecord], min_runs: int, min_families: int) -> tuple[bool, str]:
    if len(records) < min_runs:
        return False, ""
    families = {r.route_family for r in records}
    if len(families) < min_families:
        return False, ""

    tail = records[-3:]
    if len(tail) < 3:
        return False, ""
    weak = all(r.classification in {"fake_improvement", "no_improvement"} for r in tail)
    anchor_ceiling = max(max((a["candidate_score"] for a in r.anchor_curve_vs_iter000), default=0.0) for r in tail)
    if weak and anchor_ceiling < 0.5:
        return True, "information_gain_exhausted"
    return False, ""


def _next_config(base: dict[str, Any], route_family: str, round_idx: int) -> dict[str, Any]:
    cfg = deepcopy(base)
    if route_family == "endgame_density_first":
        cfg["terminal_enrichment_games"] = min(10, cfg["terminal_enrichment_games"] + 1)
        cfg["terminal_enrichment_max_moves"] = min(12, cfg["terminal_enrichment_max_moves"] + 1)
        cfg["games_per_iter"] = min(6, cfg["games_per_iter"] + (1 if round_idx % 2 == 1 else 0))
    elif route_family == "eval_denoise_first":
        cfg["quick_eval_games"] = min(12, cfg["quick_eval_games"] + 2)
        cfg["checkpoint_eval_games"] = min(12, cfg["checkpoint_eval_games"] + 2)
        cfg["checkpoint_eval_max_moves"] = min(90, cfg["checkpoint_eval_max_moves"] + 5)
    elif route_family == "long_trajectory_first":
        cfg["max_moves"] = min(70, cfg["max_moves"] + 5)
        cfg["checkpoint_eval_max_moves"] = min(90, cfg["checkpoint_eval_max_moves"] + 5)
    elif route_family == "training_density_first":
        cfg["epochs"] = min(3, cfg["epochs"] + 1)
        cfg["games_per_iter"] = min(10, cfg["games_per_iter"] + 1)
    elif route_family == "conservative_update_first":
        cfg["epochs"] = max(1, cfg["epochs"])
        cfg["batch_size"] = min(256, cfg["batch_size"] * 2)
        cfg["games_per_iter"] = min(8, cfg["games_per_iter"] + 1)
    elif route_family == "directionality_repair_first":
        cfg["iterations"] = 5
        cfg["games_per_iter"] = min(10, cfg["games_per_iter"] + 1)
        cfg["terminal_enrichment_games"] = min(10, cfg["terminal_enrichment_games"] + 1)
        cfg["checkpoint_eval_games"] = min(12, cfg["checkpoint_eval_games"] + 2)
    return cfg


def main() -> int:
    parser = argparse.ArgumentParser(description="Dynamic pure-RL feasibility/anchor search under frozen benchmark_start protocol")
    parser.add_argument("--seed", type=int, default=20260325)
    parser.add_argument("--min-runs", type=int, default=5)
    parser.add_argument("--max-runs", type=int, default=6)
    parser.add_argument("--out-root", default="")
    args = parser.parse_args()

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    root = Path(args.out_root) if args.out_root else Path("artifacts") / f"local_plan_a_route_sweep_{ts}"
    root.mkdir(parents=True, exist_ok=True)

    route_families = [
        {
            "name": "endgame_density_first",
            "goal": "提高终局监督密度，缓解长期截断造成的信号稀释",
            "non_overlap_reason": "核心调的是 terminal_enrichment 族，与评估去噪/长轨迹路线不同",
            "config": {
                "iterations": 3,
                "games_per_iter": 3,
                "max_moves": 55,
                "terminal_enrichment_games": 3,
                "terminal_enrichment_max_moves": 9,
                "epochs": 1,
                "batch_size": 64,
                "quick_eval_games": 2,
                "checkpoint_eval_games": 2,
                "checkpoint_eval_max_moves": 60,
            },
        },
        {
            "name": "eval_denoise_first",
            "goal": "降低评估采样噪声，先识别真假提升",
            "non_overlap_reason": "优先增加评估采样与对局长度，不直接加训练密度",
            "config": {
                "iterations": 3,
                "games_per_iter": 3,
                "max_moves": 55,
                "terminal_enrichment_games": 2,
                "terminal_enrichment_max_moves": 8,
                "epochs": 1,
                "batch_size": 64,
                "quick_eval_games": 4,
                "checkpoint_eval_games": 4,
                "checkpoint_eval_max_moves": 60,
            },
        },
        {
            "name": "long_trajectory_first",
            "goal": "拉长轨迹，减少早停导致的方向性误导",
            "non_overlap_reason": "直接拉高 max_moves 族，与终局强化不同",
            "config": {
                "iterations": 3,
                "games_per_iter": 3,
                "max_moves": 65,
                "terminal_enrichment_games": 2,
                "terminal_enrichment_max_moves": 10,
                "epochs": 1,
                "batch_size": 64,
                "quick_eval_games": 2,
                "checkpoint_eval_games": 2,
                "checkpoint_eval_max_moves": 60,
            },
        },
        {
            "name": "training_density_first",
            "goal": "提高每轮训练有效更新步数，验证是否存在欠训练",
            "non_overlap_reason": "以 epochs/games_per_iter 为主轴，不改变终局分布策略",
            "config": {
                "iterations": 3,
                "games_per_iter": 4,
                "max_moves": 55,
                "terminal_enrichment_games": 3,
                "terminal_enrichment_max_moves": 9,
                "epochs": 2,
                "batch_size": 64,
                "quick_eval_games": 2,
                "checkpoint_eval_games": 2,
                "checkpoint_eval_max_moves": 60,
            },
        },
        {
            "name": "conservative_update_first",
            "goal": "更保守更新，减少震荡导致的方向回落",
            "non_overlap_reason": "通过更大 batch + 低 epochs 稳定梯度，不追求训练强度",
            "config": {
                "iterations": 3,
                "games_per_iter": 3,
                "max_moves": 55,
                "terminal_enrichment_games": 2,
                "terminal_enrichment_max_moves": 8,
                "epochs": 1,
                "batch_size": 128,
                "quick_eval_games": 2,
                "checkpoint_eval_games": 2,
                "checkpoint_eval_max_moves": 60,
            },
        },
        {
            "name": "directionality_repair_first",
            "goal": "直接针对 iter_k vs iter_000 方向修复，拉高跨迭代锚点评估密度",
            "non_overlap_reason": "增加迭代深度与锚点评估密度，区别于单纯信号质量提升",
            "config": {
                "iterations": 3,
                "games_per_iter": 4,
                "max_moves": 60,
                "terminal_enrichment_games": 4,
                "terminal_enrichment_max_moves": 10,
                "epochs": 2,
                "batch_size": 64,
                "quick_eval_games": 4,
                "checkpoint_eval_games": 4,
                "checkpoint_eval_max_moves": 60,
            },
        },
    ]

    records: list[RunRecord] = []
    route_round_count: dict[str, int] = {r["name"]: 0 for r in route_families}

    run_index = 0
    route_cursor = 0
    while run_index < args.max_runs:
        if route_cursor < len(route_families):
            route = route_families[route_cursor]
            route_cursor += 1
        else:
            # Focus on the best available route, unless it has been repeatedly unproductive.
            ranked = sorted(
                records,
                key=lambda r: (
                    mean(a["candidate_score"] for a in r.anchor_curve_vs_iter000) if r.anchor_curve_vs_iter000 else 0.0,
                    r.quality["value_non_zero_fraction_mean"],
                ),
                reverse=True,
            )
            route = next(r for r in route_families if r["name"] == ranked[0].route_family)

        round_idx = route_round_count[route["name"]]
        route_round_count[route["name"]] += 1
        cfg = _next_config(route["config"], route["name"], round_idx)

        run_dir = root / f"run_{run_index:03d}_{route['name']}_r{round_idx+1}"
        summary = _train(run_dir, cfg, args.seed + run_index * 97)
        quality = _quality(summary)
        iterations = [x["iteration"] for x in quality["per_iteration"]]
        pairs = [_eval_pair(run_dir, cand, base) for cand, base in _compute_pairs(iterations)]

        key_panel = [p for p in pairs if tuple(p["pair"]) in KEY_PANEL]
        anchors = _anchor_curve(pairs)
        adjacent = [p for p in pairs if p["pair"][0] - p["pair"][1] == 1][:3]
        large_span = [p for p in pairs if p["pair"][0] - p["pair"][1] >= 2][:3]

        prev = records[-1] if records else None
        classification = _classify(prev, quality, anchors, key_panel)

        # Determine route status and next plan.
        same_route_hist = [r for r in records if r.route_family == route["name"]]
        no_gain_streak = 0
        for r in reversed(same_route_hist):
            if r.classification in {"no_improvement", "fake_improvement"}:
                no_gain_streak += 1
            else:
                break

        status = _route_status(classification, anchors, no_gain_streak)
        if status == "继续深入":
            next_plan = "继续当前路线并做小步调参，目标确认非假峰值"
        elif status == "暂时保留":
            next_plan = "保留路线但优先测试其他路线族以增加信息增益"
        else:
            next_plan = "该路线连续无增益且未形成锚点，切换到新路线族"

        records.append(
            RunRecord(
                run_index=run_index,
                route_family=route["name"],
                route_goal=route["goal"],
                route_non_overlap_reason=route["non_overlap_reason"],
                run_dir=str(run_dir),
                train_config=cfg,
                quality=quality,
                key_panel_results=key_panel,
                anchor_curve_vs_iter000=anchors,
                representative_adjacent=adjacent,
                representative_large_span=large_span,
                classification=classification,
                route_status=status,
                next_plan=next_plan,
            )
        )

        success, success_reason = _success_condition(records)
        if success and len(records) >= 2:
            break

        failed, fail_reason = _failure_condition(records, min_runs=args.min_runs, min_families=5)
        if failed:
            break

        run_index += 1

    final_success, success_reason = _success_condition(records)
    final_fail, fail_reason = _failure_condition(records, min_runs=args.min_runs, min_families=5)

    report = {
        "schema_version": "plan_a_route_sweep_v2_dynamic",
        "frozen_protocol": deepcopy(FROZEN_PROTOCOL),
        "constraints": {
            "style_disabled": True,
            "kl_style_disabled": True,
            "search_level_style_guidance_disabled": True,
            "external_engine_disabled": True,
            "large_outputs_local_only": True,
        },
        "search_stop": {
            "success": final_success,
            "success_reason": success_reason if final_success else None,
            "failure": final_fail,
            "failure_reason": fail_reason if final_fail else None,
            "total_runs": len(records),
            "route_families_explored": sorted(list({r.route_family for r in records})),
        },
        "runs": [
            {
                "run_index": r.run_index,
                "route_family": r.route_family,
                "route_goal": r.route_goal,
                "route_non_overlap_reason": r.route_non_overlap_reason,
                "run_dir": r.run_dir,
                "train_config": r.train_config,
                "quality": r.quality,
                "key_panel_results": r.key_panel_results,
                "anchor_curve_vs_iter000": r.anchor_curve_vs_iter000,
                "representative_adjacent": r.representative_adjacent,
                "representative_large_span": r.representative_large_span,
                "classification": r.classification,
                "route_status": r.route_status,
                "next_plan": r.next_plan,
            }
            for r in records
        ],
    }

    report_path = root / "plan_a_route_sweep_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
