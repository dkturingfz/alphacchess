# Phase 2 Pure RL File Guide

## Goal

Phase 2 focuses on the pure RL mainline only:

`self-play -> replay -> train -> checkpoint evaluation`

This guide covers the developer-facing files/scripts used to run and validate the Phase 2 path, including the Phase 2.1 extended-run validation close-out.

## Core scripts

### `scripts/train_selfplay.py`

Primary multi-iteration training entrypoint.

Phase 2 defaults are intentionally larger than the old minimal loop:
- `--iterations 6`
- `--games-per-iter 64`
- `--terminal-enrichment-games 8`

It writes stable artifacts under `--out-dir` (default `artifacts/phase2_pure_rl`):
- `replays/iter_XXX.json`
- `checkpoints/iter_XXX.json`
- `iteration_summaries/iter_XXX.json`
- `evaluations/iter_XXX_vs_previous.json`
- `evaluations/iter_XXX_vs_fixed_baseline.json` (if `--baseline-checkpoint` provided)
- `train_summary.json`

### `scripts/export_replay_stats.py`

Loads one replay file and prints explicit quality indicators including:
- `num_games`
- `natural_terminations`
- `step_cap_truncations`
- `result_counts`
- `value_non_zero_fraction`
- value sign counts


### `scripts/summarize_extended_run.py`

Phase 2.1 helper that reads `train_summary.json` from a multi-iteration run and emits a consolidated trend report:
- per-iteration replay-quality trend rows
- checkpoint-vs-previous / optional fixed-baseline trend rows
- aggregate non-zero value supervision statistics
- readiness flags for the next stage decision

### `scripts/evaluate_vs_random.py`

Quick baseline check of one checkpoint against random play.

### `scripts/evaluate_checkpoints.py`

Reproducible internal checkpoint comparison:
- candidate checkpoint vs baseline checkpoint
- fixed seeds and game count
- structured JSON output with score and metadata

## Typical Phase 2 / Phase 2.1 validation flow

```bash
python scripts/train_selfplay.py --iterations 3 --games-per-iter 24 --out-dir artifacts/phase2_smoke
python scripts/export_replay_stats.py --replay artifacts/phase2_smoke/replays/iter_002.json
python scripts/evaluate_vs_random.py --checkpoint artifacts/phase2_smoke/checkpoints/iter_002.json --games 20 --seed 7
python scripts/evaluate_checkpoints.py \
  --candidate artifacts/phase2_smoke/checkpoints/iter_002.json \
  --baseline artifacts/phase2_smoke/checkpoints/iter_000.json \
  --games 12 --seed 7
python scripts/summarize_extended_run.py \
  --train-summary artifacts/phase2_smoke/train_summary.json
```

## Notes

- Phase 2 remains independent of style-constrained RL features.
- Phase 2 remains independent of Pikafish in the training core.
- If replay quality degrades, inspect replay stats first before tuning scale.


## Phase 2.1 note

- Phase 2.1 stays on the pure RL path only (no style KL/search guidance).
- It extends the run length to observe trends across iterations, not one-shot snapshots.
- It remains independent of Pikafish in the training core.


## Phase 3 handoff

After Phase 2.1 trend validation, move to `docs/phase3_file_guide.md` for profiling, stricter readiness gating, and benchmark-preparation workflow.
