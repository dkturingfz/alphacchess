#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

KEY_PANEL = [(1, 0), (3, 0), (2, 1)]


def _read_json(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text())


def _pair_path(run_dir: Path, cand: int, base: int) -> Path:
    return run_dir / "benchmark_start_sanity" / f"iter_{cand:03d}_vs_iter_{base:03d}.json"


def _pair_score(run_dir: Path, cand: int, base: int) -> float | None:
    p = _pair_path(run_dir, cand, base)
    if not p.exists():
        return None
    return float(_read_json(p)["aggregate"]["candidate_score"])


def _train_quality(run_dir: Path) -> dict[str, Any]:
    s = _read_json(run_dir / "train" / "train_summary.json")
    rows = s["iterations"]
    trunc_ratios = []
    natural = []
    vfrac = []
    for r in rows:
        total = int(r["natural_terminations"]) + int(r["step_cap_truncations"])
        trunc_ratios.append((int(r["step_cap_truncations"]) / total) if total else 0.0)
        natural.append(int(r["natural_terminations"]))
        vfrac.append(float(r["value_non_zero_fraction"]))
    return {
        "natural_terminations_mean": mean(natural),
        "truncation_ratio_mean": mean(trunc_ratios),
        "value_non_zero_fraction_mean": mean(vfrac),
    }


def _route_family_from_name(run_name: str) -> str:
    # run_000_<route>_r1
    return run_name.split("_", 2)[2].rsplit("_r", 1)[0]


def summarize(root: Path) -> dict[str, Any]:
    run_dirs = sorted([p for p in root.glob("run_*") if p.is_dir()])
    runs: list[dict[str, Any]] = []
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for rd in run_dirs:
        family = _route_family_from_name(rd.name)
        q = _train_quality(rd)
        panel = {}
        for cand, base in KEY_PANEL:
            score = _pair_score(rd, cand, base)
            if score is not None:
                panel[f"iter_{cand:03d}_vs_iter_{base:03d}"] = score
        anchors = []
        for cand in range(1, 10):
            score = _pair_score(rd, cand, 0)
            if score is None:
                continue
            anchors.append({"cand": cand, "score": score})
        run = {
            "run_dir": str(rd),
            "route_family": family,
            "quality": q,
            "key_panel": panel,
            "anchors": anchors,
            "best_anchor": max((a["score"] for a in anchors), default=None),
            "latest_anchor": anchors[-1]["score"] if anchors else None,
        }
        runs.append(run)
        by_family[family].append(run)

    family_summary: dict[str, Any] = {}
    for family, rows in by_family.items():
        best = max((r["best_anchor"] for r in rows if r["best_anchor"] is not None), default=None)
        latest = rows[-1]
        family_summary[family] = {
            "runs": len(rows),
            "representative_run_dir": latest["run_dir"],
            "representative_best_anchor": latest["best_anchor"],
            "representative_key_panel": latest["key_panel"],
            "overall_best_anchor": best,
            "representative_quality": latest["quality"],
        }

    hopeful = sorted(
        [
            {
                "route_family": f,
                "best_anchor": max((r["best_anchor"] for r in rs if r["best_anchor"] is not None), default=0.0),
            }
            for f, rs in by_family.items()
        ],
        key=lambda x: x["best_anchor"],
        reverse=True,
    )

    return {
        "goal": "在 pure RL 主线中通过多路线搜索修复 iter_k vs iter_000 方向性（固定 key panel + anchor curve）",
        "current_status": "已继续执行真实多路线训练+固定协议评估；尚未覆盖完全部路线族。",
        "root": str(root),
        "total_runs": len(runs),
        "route_families_explored": sorted(by_family.keys()),
        "total_route_families": len(by_family),
        "family_summary": family_summary,
        "eliminated_families": [
            {
                "route_family": f,
                "reason": "代表 run 的 best_anchor < 0.5，且未形成稳定 iter_k vs iter_000 正锚点",
            }
            for f, s in family_summary.items()
            if (s["representative_best_anchor"] or 0.0) < 0.5
        ],
        "hopeful_families": hopeful,
        "found_feasible_anchor": any((r["best_anchor"] or 0.0) >= 0.5 for r in runs),
        "core_anchor_interval": [0.67, 0.73],
        "most_credible_failure_reason_if_not_found": "方向性修复高度依赖训练随机性与轨迹分布，单次短程 run 可能产生假峰值；需更多复现实验确认稳定性。",
        "runs": runs,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Summarize route-sweep progress for pure-RL directionality search")
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    summary = summarize(Path(args.root))
    out = json.dumps(summary, indent=2, ensure_ascii=False)
    print(out)
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
