# Phase 1 File Guide (Minimal AlphaZero-like Loop)

This guide documents the concrete Phase 1 files added for the minimal loop:

self-play -> replay -> train -> reload -> evaluate

## Core Python modules

- `alphacchess/phase1_model.py`
  - `PolicyValueNet` v1 implementation.
  - Contract:
    - input shape matches `(15, 10, 9)`
    - policy head size is exactly `8100`
    - value head output is scalar
  - Supports checkpoint save/load with version metadata.

- `alphacchess/phase1_selfplay.py`
  - Small-scale self-play loop.
  - Produces replay samples with observation, selected policy action, and value target.
  - Phase 1.1 adds a controlled terminal-enrichment path (optional, default enabled by training CLI):
    - game source: `terminal_enrichment`
    - deterministic near-terminal start positions
    - explicit non-zero win/loss supervision injection for value head
  - Also adds immediate-terminal move preference in action selection (without changing overall architecture).
  - Also records per-game termination semantics:
    - `ended_naturally`
    - `hit_step_cap`
    - `terminal_reason`
    - `result_label` (`win` / `loss` / `draw` / `truncated_draw`, red-perspective)
    - `game_source` (`selfplay` / `terminal_enrichment`)

- `alphacchess/phase1_replay.py`
  - Replay dataset schema and metadata validation.
  - Replay schema version is now `phase1_replay_v3` (strictly validated).
  - Stores two payloads:
    - `samples`: per-position supervision records
    - `games`: per-game semantic summaries (termination/result metadata)
  - Phase 1.1 adds explicit source labels:
    - `ReplaySample.sample_source`
    - `ReplayGame.game_source`
  - Ensures replay includes version metadata:
    - `action_encoding_version`
    - `observation_encoding_version`
    - `dataset_schema_version`
    - `rules_version`
    - `replay_schema_version`

- `alphacchess/phase1_train.py`
  - Trainer v1 over replay data.
  - Runs mini-batch updates and returns training metrics.

- `alphacchess/phase1_eval.py`
  - Evaluator v1 against random baseline.
  - Produces deterministic/reproducible outputs with seed.

## Required CLI scripts

- `scripts/train_selfplay.py`
  - Runs several iterations of:
    1. self-play generation
    2. replay write
    3. training
    4. checkpoint write
    5. quick eval vs random
  - Example:
    ```bash
    python scripts/train_selfplay.py \
      --iterations 3 \
      --games-per-iter 8 \
      --max-moves 80 \
      --epochs 2 \
      --batch-size 32 \
      --lr 0.002 \
      --seed 11 \
      --out-dir artifacts/phase1
    ```
  - Passing result: script completes and writes `train_summary.json`, replay files, and checkpoints.

- `scripts/evaluate_vs_random.py`
  - Loads checkpoint and evaluates vs random.
  - Example:
    ```bash
    python scripts/evaluate_vs_random.py \
      --checkpoint artifacts/phase1/checkpoints/iter_002.json \
      --games 100 \
      --max-moves 120 \
      --seed 11 \
      --out artifacts/phase1/eval_100.json
    ```
  - Passing result: JSON output shows `win_rate > 0.90` over 100 games.

- `scripts/export_replay_stats.py`
  - Reads replay and exports stats + metadata.
  - Example:
    ```bash
    python scripts/export_replay_stats.py --replay artifacts/phase1/replays/iter_002.json
    ```
  - Passing result: metadata is version-valid and policy shape confirms action-space alignment (`8100`).
  - Hardening output now includes replay-quality diagnostics:
    - `num_games`
    - `natural_terminations`
    - `step_cap_truncations`
    - `result_counts`
    - `terminal_reason_counts`
    - `game_source_counts`
    - `value_counts_by_source`
    - `value_non_zero_fraction`
    - `value_positive_count` / `value_zero_count` / `value_negative_count`

## How to interpret replay stats (Phase 1 close-out semantics)

- If `step_cap_truncations` is high and `result_counts.truncated_draw` dominates, then replay is truncation-heavy and value targets will mostly be `0`.
- If `natural_terminations` contains wins/losses, then at least some non-zero value supervision should appear.
- If non-zero supervision mainly comes from `value_counts_by_source.terminal_enrichment`, this is expected in early Phase 1.1 and should be interpreted as a controlled fallback while baseline self-play is still weak.
- `value_non_zero_fraction` is the fastest single indicator for whether value learning is seeing terminal supervision beyond draws.
- `terminal_reason_counts` helps verify whether natural terminal rules are actually being hit (e.g., `black_general_captured`, `no_legal_moves`) or whether the loop mostly exits via `max_moves_truncation`.

## Schema/version note

- Replay schema extension from `phase1_replay_v2` to `phase1_replay_v3` is intentional for Phase 1.1 source tracking.
- Strict metadata validation remains enabled; mismatched schema version will fail fast at load time.

## Artifact layout

By default, Phase 1 artifacts are written under `artifacts/phase1/`:

- `artifacts/phase1/replays/iter_XXX.json`
- `artifacts/phase1/checkpoints/iter_XXX.json`
- `artifacts/phase1/train_summary.json`
- `artifacts/phase1/eval_100.json` (when requested)

These artifacts preserve Phase 1 version metadata for compatibility checks.
