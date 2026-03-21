#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str]) -> dict:
    out = subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Phase 1b gray-zone style recovery workflow")
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--target-dataset", required=True)
    ap.add_argument("--config", default="configs/style_eval_v1.yaml")
    ap.add_argument("--generic-pretrain-dataset", default="")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out-dir", default="artifacts/style/recovery")
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--force-recovery", action="store_true", help="Testing/debug: run full sequence even if initial zone is not gray")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sequence: list[dict] = []

    verify = _run(
        [
            sys.executable,
            "scripts/evaluate_style.py",
            "--checkpoint",
            args.checkpoint,
            "--dataset",
            args.target_dataset,
            "--config",
            args.config,
            "--notes",
            "recovery_step1_verify_eval_and_data_integrity",
        ]
    )
    sequence.append({"step": "verify_evaluation_and_data_integrity", "result": verify})

    if verify["quality_zone"] != "gray" and not args.force_recovery:
        payload = {
            "recovery_required": False,
            "reason": f"quality_zone={verify['quality_zone']}, gray-zone policy not triggered",
            "steps": sequence,
            "final": verify,
        }
        (out_dir / "recovery_report.json").write_text(json.dumps(payload, indent=2))
        print(json.dumps(payload, indent=2))
        return 0

    strengthened_ckpt = out_dir / "style_strengthened_frozen.json"
    strengthened_train = _run(
        [
            sys.executable,
            "scripts/train_style_reference.py",
            "--target-dataset",
            args.target_dataset,
            "--generic-pretrain-dataset",
            args.generic_pretrain_dataset,
            "--pretrain-epochs",
            "4",
            "--finetune-epochs",
            "4",
            "--batch-size",
            str(args.batch_size),
            "--lr",
            str(args.lr),
            "--seed",
            str(args.seed),
            "--out-checkpoint",
            str(strengthened_ckpt),
            "--out-report",
            str(out_dir / "strengthened_train_report.json"),
        ]
    )
    sequence.append({"step": "strengthen_generic_pretrain_then_personal_finetune", "result": strengthened_train})

    strengthened_eval = _run(
        [
            sys.executable,
            "scripts/evaluate_style.py",
            "--checkpoint",
            str(strengthened_ckpt),
            "--dataset",
            args.target_dataset,
            "--config",
            args.config,
            "--notes",
            "recovery_step2_after_strengthen",
        ]
    )
    sequence.append({"step": "evaluate_after_strengthen", "result": strengthened_eval})

    if strengthened_eval["quality_zone"] != "gray":
        payload = {
            "recovery_required": True,
            "stopped_at": "step2_strengthen",
            "steps": sequence,
            "final": strengthened_eval,
        }
        (out_dir / "recovery_report.json").write_text(json.dumps(payload, indent=2))
        print(json.dumps(payload, indent=2))
        return 0

    mirrored_ckpt = out_dir / "style_strengthened_mirrored_frozen.json"
    mirrored_train = _run(
        [
            sys.executable,
            "scripts/train_style_reference.py",
            "--target-dataset",
            args.target_dataset,
            "--generic-pretrain-dataset",
            args.generic_pretrain_dataset,
            "--pretrain-epochs",
            "4",
            "--finetune-epochs",
            "4",
            "--augment-lr-mirror",
            "--batch-size",
            str(args.batch_size),
            "--lr",
            str(args.lr),
            "--seed",
            str(args.seed + 1),
            "--out-checkpoint",
            str(mirrored_ckpt),
            "--out-report",
            str(out_dir / "mirrored_train_report.json"),
        ]
    )
    sequence.append({"step": "enable_left_right_mirror_augmentation", "result": mirrored_train})

    mirrored_eval = _run(
        [
            sys.executable,
            "scripts/evaluate_style.py",
            "--checkpoint",
            str(mirrored_ckpt),
            "--dataset",
            args.target_dataset,
            "--config",
            args.config,
            "--notes",
            "recovery_step3_after_lr_mirror_augmentation",
        ]
    )
    sequence.append({"step": "evaluate_after_lr_mirror", "result": mirrored_eval})

    payload = {
        "recovery_required": True,
        "capacity_increase_todo": mirrored_eval["quality_zone"] == "gray",
        "steps": sequence,
        "final": mirrored_eval,
    }
    (out_dir / "recovery_report.json").write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
