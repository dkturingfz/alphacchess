#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alphacchess.phase1_model import PolicyValueNet
from alphacchess.style_phase1b import (
    augment_samples_lr_mirror,
    build_style_checkpoint_metadata,
    load_style_position_samples,
    train_style_policy,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Train frozen style reference policy (Phase 4 style-reference)")
    ap.add_argument("--target-dataset", required=True, help="JSONL target-player positions or games")
    ap.add_argument("--generic-pretrain-dataset", default="", help="Optional JSONL generic data")
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--pretrain-epochs", type=int, default=2)
    ap.add_argument("--finetune-epochs", type=int, default=2)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--augment-lr-mirror", action="store_true")
    ap.add_argument("--out-checkpoint", default="artifacts/style/pi_style_frozen.json")
    ap.add_argument("--out-report", default="artifacts/style/train_style_report.json")
    args = ap.parse_args()

    target_samples = load_style_position_samples(args.target_dataset)
    if args.augment_lr_mirror:
        target_samples = augment_samples_lr_mirror(target_samples)

    model = PolicyValueNet.for_xiangqi_v1(seed=args.seed)

    training_path = "direct_target"
    pretrain_stats = None
    if args.generic_pretrain_dataset:
        generic_samples = load_style_position_samples(args.generic_pretrain_dataset)
        pretrain_stats = train_style_policy(
            model,
            generic_samples,
            epochs=args.pretrain_epochs,
            lr=args.lr,
            batch_size=args.batch_size,
        )
        finetune_stats = train_style_policy(
            model,
            target_samples,
            epochs=args.finetune_epochs,
            lr=args.lr,
            batch_size=args.batch_size,
        )
        training_path = "generic_pretrain_then_personal_finetune"
        train_stats = {"pretrain": pretrain_stats, "finetune": finetune_stats}
    else:
        direct_stats = train_style_policy(
            model,
            target_samples,
            epochs=args.epochs,
            lr=args.lr,
            batch_size=args.batch_size,
        )
        train_stats = {"direct": direct_stats}

    ckpt_meta = build_style_checkpoint_metadata(
        checkpoint_schema_version="phase1b_style_reference_v1",
        frozen=True,
        extra={
            "style_training_path": training_path,
            "target_dataset": args.target_dataset,
            "generic_pretrain_dataset": args.generic_pretrain_dataset or "none",
            "augment_left_right_mirror": "true" if args.augment_lr_mirror else "false",
        },
    )

    out_ckpt = Path(args.out_checkpoint)
    out_ckpt.parent.mkdir(parents=True, exist_ok=True)
    model.save_checkpoint(out_ckpt, ckpt_meta)

    report = {
        "checkpoint": str(out_ckpt),
        "checkpoint_metadata": ckpt_meta,
        "target_sample_count": len(target_samples),
        "training_path": training_path,
        "stats": train_stats,
    }
    out_report = Path(args.out_report)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
