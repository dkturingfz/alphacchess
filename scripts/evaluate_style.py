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
    classify_style_quality,
    evaluate_style_samples,
    load_style_eval_config,
    load_style_position_samples,
    make_style_eval_payload,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate style reference model (Phase 4 style-reference)")
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--config", default="configs/style_eval_v1.yaml")
    ap.add_argument("--out", default="")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    cfg = load_style_eval_config(args.config)
    model, ckpt_meta = PolicyValueNet.load_checkpoint(args.checkpoint)
    samples = load_style_position_samples(args.dataset)
    metrics = evaluate_style_samples(model, samples, cfg.phase_split)
    quality_zone = classify_style_quality(metrics["global"].top1, cfg.thresholds)

    payload = make_style_eval_payload(
        eval_config_path=args.config,
        model_checkpoint=args.checkpoint,
        checkpoint_metadata=ckpt_meta,
        metrics=metrics,
        quality_zone=quality_zone,
        dataset_path=args.dataset,
        notes=args.notes,
    )
    if args.out:
        Path(args.out).write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
