# Unattended Pure-RL Validation Session (2026-03-22)

## Scope

This unattended session focused on the pure RL mainline only (no Pikafish runtime dependency, no style-phase expansion).

Main artifact root:
- `artifacts/unattended_pure_rl_20260322/`

## What was re-audited first

- Re-read `AGENTS.md`, `PLAN.md`, and current phase docs.
- Re-ran key pure-RL validation tests:
  - `tests/test_phase2_extended_run.py`
  - `tests/test_phase2_checkpoint_eval.py`
  - `tests/test_phase3_profile_and_benchmark.py`
- Re-ran key command paths end-to-end on a precheck run:
  - `scripts/train_selfplay.py`
  - `scripts/export_replay_stats.py`
  - `scripts/evaluate_checkpoints.py`
  - `scripts/summarize_extended_run.py`

No script/doc inconsistency requiring code fix was found during precheck.

## Main longer run

Command profile:
- 5 iterations
- 30 self-play games/iteration + 8 terminal-enrichment games/iteration
- 24 checkpoint-vs-previous games/iteration (where applicable)

Output directory:
- `artifacts/unattended_pure_rl_20260322/main_run/`

Key outcomes from `extended_summary.json`:
- iterations: 5
- total_games: 190
- min_value_non_zero_fraction: 0.1163
- max_step_cap_truncation_rate: 0.6579
- readiness_grade: `caution`

Primary caution source:
- truncation control exceeded pass threshold (0.6579 > 0.6)

## Longer checkpoint-vs-checkpoint evaluations

Additional 64-game comparisons were run and archived:
- `iter_001` vs `iter_000`: candidate_score = 0.5391
- `iter_004` vs `iter_000`: candidate_score = 0.5469
- `iter_004` vs `iter_003`: candidate_score = 0.5703

These support mild positive internal strength signal, but do not remove replay-truncation caution by themselves.

## Automatic branch decision and one conservative adjustment

Branch selected: **Case B (CAUTION)**.

Single conservative adjustment:
- Increased terminal enrichment from 8 to 12 games/iteration (and enrichment max moves 8 -> 10).

Adjusted pass output:
- `artifacts/unattended_pure_rl_20260322/followup_adjusted/`

Follow-up summary:
- max_step_cap_truncation_rate improved to 0.5952 (now pass on truncation check)
- readiness remains `caution` due checkpoint-progress-visibility ratio at 0.6667 in this shorter 3-iteration follow-up

Interpretation:
- Caution **improved** on replay truncation dimension.
- Overall readiness remains conservative caution, not full pass.

## Profiling rerun

A larger profiling run was executed:
- `artifacts/unattended_pure_rl_20260322/profile/profile_report_large.json`

Hotspot ordering remained broadly stable vs `docs/phase3_profile_report.json`:
- top components continue to be dominated by `selfplay_loop`, `apply_action`, `legal_actions`, and `checkpoint_eval`.

Comparison artifact:
- `artifacts/unattended_pure_rl_20260322/profile/hotspot_comparison.json`

## Session artifacts checklist

Included under `artifacts/unattended_pure_rl_20260322/`:
- train run outputs (precheck, main_run, followup_adjusted)
- replay-quality trend outputs (`main_run/replay_stats_trend.json`)
- checkpoint trend outputs (`main_run/checkpoint_vs_previous_trend.json`, `main_run/checkpoint_long_evals.json`)
- extended summaries (`main_run/extended_summary.json`, `followup_adjusted/extended_summary.json`)
- profiling outputs (`profile/`)
- metadata discipline spot-check (`metadata_check.json`)

