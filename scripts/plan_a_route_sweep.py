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

FROZEN_PROTOCOL = {
    "start_fens_file": "data/benchmark_positions/samples/benchmark_start_fens_sample.txt",
    "max_start_positions": 8,
    "games_per_start": 4,
    "max_moves": 60,
    "seeds": "17,29,41,53",
}

KEY_PANEL = [(1, 0), (3, 0), (2, 1)]
MIN_RUNS = 8
MAX_RUNS = 12


@dataclass
class RunRecord:
    run_index: int
    phase: str
    route: str
    run_tag: str
    train_config: dict
    quality: dict
    pair_results: list[dict]
    classification: str
    guardrail_triggered: bool
    guardrail_reasons: list[str]
    continue_next: bool
    continue_reason: list[str]
    next_tuning: dict


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _panel_from_iterations(iterations: list[int]) -> list[tuple[int, int]]:
    available = set(iterations)
    panel: list[tuple[int, int]] = []
    for cand, base in KEY_PANEL:
        if cand in available and base in available and cand > base:
            panel.append((cand, base))
    if len(panel) == len(KEY_PANEL):
        return panel
    if 0 in available:
        latest = max(available)
        if latest > 0 and (latest, 0) not in panel:
            panel.append((latest, 0))
        prev = max(0, latest - 1)
        if latest > prev and (latest, prev) not in panel and prev in available:
            panel.append((latest, prev))
    return panel[:3]


def _quality(summary: dict) -> dict:
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


def _eval_pair(run_dir: Path, cand: int, base: int) -> dict:
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
        "abs_score_minus_0_5": abs(float(agg["candidate_score"]) - 0.5),
        "path": str(out_file),
    }


def _find_pair(pairs: list[dict], cand: int, base: int) -> dict | None:
    for p in pairs:
        if p["pair"] == [cand, base]:
            return p
    return None


def _guardrail(prev: RunRecord | None, pairs: list[dict], quality: dict) -> tuple[bool, list[str]]:
    reasons = []
    p10 = _find_pair(pairs, 1, 0)
    p30 = _find_pair(pairs, 3, 0)
    if p10 and p10["candidate_score"] < 0.40:
        reasons.append("iter_001_vs_iter_000 < 0.40")
    if p30 and p30["candidate_score"] < 0.40:
        reasons.append("iter_003_vs_iter_000 < 0.40")
    if p10 and p30 and p10["candidate_score"] < 0.50 and p30["candidate_score"] < 0.50:
        reasons.append("both_anchor_pairs_below_0.50")
    if prev:
        prev10 = _find_pair(prev.pair_results, 1, 0)
        prev30 = _find_pair(prev.pair_results, 3, 0)
        if prev10 and prev30 and p10 and p30:
            no_lift = p10["candidate_score"] <= prev10["candidate_score"] and p30["candidate_score"] <= prev30["candidate_score"]
            weak_signal = quality["value_non_zero_fraction_mean"] <= prev.quality["value_non_zero_fraction_mean"] + 0.01
            if no_lift and weak_signal:
                reasons.append("anchors_not_lifted_and_signal_not_improved")
    return (len(reasons) > 0), reasons


def _classify(prev: RunRecord | None, quality: dict, pairs: list[dict], guardrail_reasons: list[str]) -> str:
    if prev is None:
        return "baseline"
    p10 = _find_pair(pairs, 1, 0)
    p30 = _find_pair(pairs, 3, 0)
    prev10 = _find_pair(prev.pair_results, 1, 0)
    prev30 = _find_pair(prev.pair_results, 3, 0)
    signal_improved = (
        quality["value_non_zero_fraction_mean"] >= prev.quality["value_non_zero_fraction_mean"] + 0.02
        or quality["truncation_ratio_mean"] <= prev.quality["truncation_ratio_mean"] - 0.06
        or quality["natural_terminations_mean"] >= prev.quality["natural_terminations_mean"] + 1.0
    )
    directional_lift = False
    if p10 and p30 and prev10 and prev30:
        directional_lift = p10["candidate_score"] > prev10["candidate_score"] or p30["candidate_score"] > prev30["candidate_score"]
    if signal_improved and directional_lift and not guardrail_reasons:
        return "true_improvement"
    if signal_improved and (guardrail_reasons or not directional_lift):
        return "fake_improvement"
    return "no_improvement"


def _train(run_dir: Path, cfg: dict, seed: int) -> dict:
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


def _route_score(record: RunRecord) -> float:
    p10 = _find_pair(record.pair_results, 1, 0)
    p30 = _find_pair(record.pair_results, 3, 0)
    p21 = _find_pair(record.pair_results, 2, 1)
    anchor_term = 0.0
    if p10:
        anchor_term += p10["candidate_score"]
    if p30:
        anchor_term += p30["candidate_score"]
    if p21:
        anchor_term += 0.5 * p21["candidate_score"]
    signal = (
        0.8 * record.quality["value_non_zero_fraction_mean"]
        + 0.4 * record.quality["natural_terminations_mean"] / max(1.0, record.train_config["games_per_iter"])
        - 0.5 * record.quality["truncation_ratio_mean"]
    )
    penalty = 0.0
    if record.guardrail_triggered:
        penalty += 0.6
    penalty += mean(p["seed_stddev"] for p in record.pair_results)
    return anchor_term + signal - penalty


def _phase_b_tuning(base_cfg: dict, step: int) -> dict:
    cfg = deepcopy(base_cfg)
    cfg["iterations"] = 4
    cfg["games_per_iter"] = min(10, int(cfg["games_per_iter"]) + 1)
    cfg["max_moves"] = min(100, int(cfg["max_moves"]) + 5)
    cfg["terminal_enrichment_games"] = min(8, int(cfg["terminal_enrichment_games"]) + 1)
    cfg["terminal_enrichment_max_moves"] = min(12, int(cfg["terminal_enrichment_max_moves"]) + 1)
    cfg["epochs"] = min(2, int(cfg["epochs"]))
    cfg["quick_eval_games"] = min(8, int(cfg["quick_eval_games"]) + 1)
    cfg["checkpoint_eval_games"] = min(8, int(cfg["checkpoint_eval_games"]) + 1)
    cfg["checkpoint_eval_max_moves"] = min(80, int(cfg["checkpoint_eval_max_moves"]) + 5)
    return cfg


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase A coarse sweep + Phase B focused breakthrough (pure RL only).")
    parser.add_argument("--seed", type=int, default=20260325)
    parser.add_argument("--phase-b-runs", type=int, default=4)
    parser.add_argument("--out-root", default="")
    args = parser.parse_args()

    if args.phase_b_runs < 2:
        raise ValueError("--phase-b-runs must be >=2")

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    root = Path(args.out_root) if args.out_root else Path("artifacts") / f"local_plan_a_route_sweep_{ts}"
    root.mkdir(parents=True, exist_ok=True)

    routes = {
        "route_1_endgame_density": {
            "iterations": 4,
            "games_per_iter": 4,
            "max_moves": 75,
            "terminal_enrichment_games": 2,
            "terminal_enrichment_max_moves": 8,
            "epochs": 1,
            "batch_size": 64,
            "quick_eval_games": 4,
            "checkpoint_eval_games": 4,
            "checkpoint_eval_max_moves": 70,
        },
        "route_2_eval_denoise": {
            "iterations": 4,
            "games_per_iter": 4,
            "max_moves": 75,
            "terminal_enrichment_games": 2,
            "terminal_enrichment_max_moves": 8,
            "epochs": 1,
            "batch_size": 64,
            "quick_eval_games": 8,
            "checkpoint_eval_games": 8,
            "checkpoint_eval_max_moves": 80,
        },
        "route_3_long_trajectory": {
            "iterations": 4,
            "games_per_iter": 4,
            "max_moves": 80,
            "terminal_enrichment_games": 2,
            "terminal_enrichment_max_moves": 10,
            "epochs": 2,
            "batch_size": 64,
            "quick_eval_games": 4,
            "checkpoint_eval_games": 4,
            "checkpoint_eval_max_moves": 70,
        },
        "route_4_train_density": {
            "iterations": 4,
            "games_per_iter": 5,
            "max_moves": 80,
            "terminal_enrichment_games": 3,
            "terminal_enrichment_max_moves": 10,
            "epochs": 1,
            "batch_size": 64,
            "quick_eval_games": 4,
            "checkpoint_eval_games": 4,
            "checkpoint_eval_max_moves": 70,
        },
    }

    records: list[RunRecord] = []
    run_index = 0
    for route_name, cfg in routes.items():
        run_dir = root / "phase_a" / route_name
        summary = _train(run_dir, cfg, args.seed + run_index * 101)
        quality = _quality(summary)
        panel = _panel_from_iterations([x["iteration"] for x in quality["per_iteration"]])
        pairs = [_eval_pair(run_dir, cand, base) for cand, base in panel]
        prev = records[-1] if records else None
        guardrail_triggered, guardrail_reasons = _guardrail(prev, pairs, quality)
        classification = _classify(prev, quality, pairs, guardrail_reasons)
        records.append(
            RunRecord(
                run_index=run_index,
                phase="phase_a",
                route=route_name,
                run_tag="baseline",
                train_config=cfg,
                quality=quality,
                pair_results=pairs,
                classification=classification,
                guardrail_triggered=guardrail_triggered,
                guardrail_reasons=guardrail_reasons,
                continue_next=True,
                continue_reason=["phase_a_mandatory_4_routes"],
                next_tuning={},
            )
        )
        run_index += 1

    ranked = sorted([r for r in records if r.phase == "phase_a"], key=_route_score, reverse=True)
    selected = ranked[:2]
    phase_b_pool = [s.route for s in selected]

    phase_b_budget = min(MAX_RUNS - run_index, max(2, args.phase_b_runs))
    phase_b_budget = max(2, phase_b_budget)
    phase_b_budget = min(phase_b_budget, MAX_RUNS - run_index)
    if phase_b_budget <= 0:
        raise RuntimeError("No run budget left for phase B")

    if len(phase_b_pool) == 2:
        first_round_routes = phase_b_pool
    else:
        first_round_routes = phase_b_pool[:1]

    phase_b_history: list[RunRecord] = []
    for i, route_name in enumerate(first_round_routes):
        base = next(r for r in selected if r.route == route_name)
        tuned = _phase_b_tuning(base.train_config, step=0)
        run_dir = root / "phase_b" / f"{route_name}_round1"
        summary = _train(run_dir, tuned, args.seed + run_index * 101)
        quality = _quality(summary)
        panel = _panel_from_iterations([x["iteration"] for x in quality["per_iteration"]])
        pairs = [_eval_pair(run_dir, cand, base_i) for cand, base_i in panel]
        prev = records[-1] if records else None
        guardrail_triggered, guardrail_reasons = _guardrail(prev, pairs, quality)
        classification = _classify(prev, quality, pairs, guardrail_reasons)
        rec = RunRecord(
            run_index=run_index,
            phase="phase_b",
            route=route_name,
            run_tag=f"round_{i+1}",
            train_config=tuned,
            quality=quality,
            pair_results=pairs,
            classification=classification,
            guardrail_triggered=guardrail_triggered,
            guardrail_reasons=guardrail_reasons,
            continue_next=True,
            continue_reason=["phase_b_candidate_probe"],
            next_tuning={},
        )
        records.append(rec)
        phase_b_history.append(rec)
        run_index += 1

    best_route = sorted(phase_b_history, key=_route_score, reverse=True)[0].route
    remaining = max(MIN_RUNS - run_index, 0)
    remaining = max(2, remaining)
    remaining = min(remaining, MAX_RUNS - run_index)
    for step in range(remaining):
        prev_route_run = [r for r in records if r.route == best_route][-1]
        tuned = _phase_b_tuning(prev_route_run.train_config, step=step + 1)
        run_dir = root / "phase_b" / f"{best_route}_focus_{step+1}"
        summary = _train(run_dir, tuned, args.seed + run_index * 101)
        quality = _quality(summary)
        panel = _panel_from_iterations([x["iteration"] for x in quality["per_iteration"]])
        pairs = [_eval_pair(run_dir, cand, base_i) for cand, base_i in panel]
        guardrail_triggered, guardrail_reasons = _guardrail(prev_route_run, pairs, quality)
        classification = _classify(prev_route_run, quality, pairs, guardrail_reasons)
        p10 = _find_pair(pairs, 1, 0)
        p30 = _find_pair(pairs, 3, 0)
        pass_anchor = bool(p10 and p30 and p10["candidate_score"] >= 0.50 and p30["candidate_score"] >= 0.50)
        continue_next = not pass_anchor and (run_index + 1 < MAX_RUNS)
        continue_reason = (
            ["anchor_pair_not_both_above_0.50_continue_focus"]
            if continue_next
            else ["stop_condition_1_reached" if pass_anchor else "budget_or_information_limit"]
        )
        rec = RunRecord(
            run_index=run_index,
            phase="phase_b",
            route=best_route,
            run_tag=f"focus_{step+1}",
            train_config=tuned,
            quality=quality,
            pair_results=pairs,
            classification=classification,
            guardrail_triggered=guardrail_triggered,
            guardrail_reasons=guardrail_reasons,
            continue_next=continue_next,
            continue_reason=continue_reason,
            next_tuning={},
        )
        records.append(rec)
        run_index += 1
        if pass_anchor or run_index >= MAX_RUNS or len(records) >= MIN_RUNS:
            # Stop once minimum runs are satisfied and either success or diminishing returns.
            if len(records) >= MIN_RUNS and (pass_anchor or classification != "true_improvement"):
                break

    total_runs = len(records)
    if total_runs < MIN_RUNS:
        raise RuntimeError(f"Total runs {total_runs} is below mandatory minimum {MIN_RUNS}")

    final_phase_b = [r for r in records if r.phase == "phase_b"]
    final_best = sorted(final_phase_b, key=_route_score, reverse=True)[0]
    p10 = _find_pair(final_best.pair_results, 1, 0)
    p30 = _find_pair(final_best.pair_results, 3, 0)
    direction_fixed = bool(p10 and p30 and p10["candidate_score"] >= 0.50 and p30["candidate_score"] >= 0.50)

    report = {
        "schema_version": "plan_a_route_sweep_v1",
        "frozen_protocol": deepcopy(FROZEN_PROTOCOL),
        "constraints": {
            "style_disabled": True,
            "kl_style_disabled": True,
            "search_level_style_guidance_disabled": True,
            "external_engine_disabled": True,
            "fixed_key_panel_required": [list(p) for p in KEY_PANEL],
            "run_limits": {"min_runs": MIN_RUNS, "max_runs": MAX_RUNS},
        },
        "phase_a_routes": list(routes.keys()),
        "phase_b_selected_candidates": phase_b_pool,
        "phase_b_focus_route": final_best.route,
        "directionality_repair_success": direction_fixed,
        "total_runs": total_runs,
        "artifact_root": str(root),
        "runs": [
            {
                "run_index": r.run_index,
                "phase": r.phase,
                "route": r.route,
                "run_tag": r.run_tag,
                "train_config": r.train_config,
                "quality": r.quality,
                "pair_results": r.pair_results,
                "classification": r.classification,
                "guardrail_triggered": r.guardrail_triggered,
                "guardrail_reasons": r.guardrail_reasons,
                "continue_next": r.continue_next,
                "continue_reason": r.continue_reason,
                "next_tuning": r.next_tuning,
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
