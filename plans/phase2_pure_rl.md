# Phase 2 — Pure RL Scale-Up

## Goal

Strengthen and stabilize the pure AlphaZero-like Xiangqi training path before returning to the deferred style-constrained phases.

This phase intentionally focuses only on the main reinforcement-learning pipeline:

self-play -> replay -> train -> checkpoint evaluation

The purpose is to:
- increase training scale
- improve replay quality monitoring
- make checkpoint-to-checkpoint progress measurable
- build a more trustworthy pure RL baseline for later benchmark and style-constrained work

This phase does **not** include style modeling or style-constrained RL.

---

## Scope

Phase 2 begins only after:
- Phase 0 is complete
- Phase 1 is complete
- Phase 1.1 hardening is complete

This phase must remain independent of:
- style modeling
- KL regularization
- search-level style prior mixing
- Pikafish as a training dependency
- UI

Pikafish may be used later for benchmark, but not as part of the training core in this phase.

---

## Required Deliverables

### 1. Larger self-play scale
Extend the self-play path so it can run at a meaningfully larger scale than Phase 1.

Examples of acceptable improvements:
- more games per iteration
- more iterations
- better replay accumulation
- cleaner run configuration management

Do not overcomplicate this into distributed training yet.

---

### 2. Replay quality monitoring
Improve replay monitoring so training quality can be inspected over time.

Replay / iteration outputs should make it easy to inspect:
- number of games
- natural terminations
- step-cap truncations
- result counts
- value target distribution
- non-zero value fraction
- source breakdown if still relevant

The goal is to ensure replay does not silently degenerate again.

---

### 3. Checkpoint-vs-checkpoint evaluation
Add a simple, reproducible evaluation path for comparing newer checkpoints against earlier checkpoints.

This is not yet the formal benchmark vs Pikafish.
This is an internal progress measure.

Examples:
- latest checkpoint vs previous checkpoint
- latest checkpoint vs fixed baseline checkpoint
- small match runs with controlled seeds

---

### 4. Stable experiment outputs
Training runs should produce stable artifacts and summaries that allow later comparison.

At minimum, preserve:
- checkpoint metadata
- replay metadata
- iteration summaries
- evaluation summaries

---

### 5. Documentation updates
Update the repository docs so Phase 2 exists clearly as the current mainline continuation after Phase 1.1.

Add or update a concise developer-facing file guide for new Phase 2 files and scripts.

---

## Required CLI

At minimum, this phase should provide or complete:

- `scripts/train_selfplay.py` (expanded pure-RL usage)
- `scripts/export_replay_stats.py`
- `scripts/evaluate_vs_random.py`
- a new or updated script for checkpoint-vs-checkpoint comparison, for example:
  - `scripts/evaluate_checkpoints.py`

If naming differs, the functionality must still exist clearly.

---

## Required Testing

At minimum include:

1. regression tests for replay statistics consistency
2. integration test for multi-iteration self-play -> train -> reload
3. test that checkpoint comparison path runs and produces structured output
4. regression test ensuring non-zero value supervision is still present in replay

---

## Acceptance Criteria

Phase 2 is complete only when all of the following are true:

1. The pure RL path runs at a meaningfully larger scale than Phase 1/1.1.
2. Replay statistics remain explicit and trustworthy.
3. Non-zero value supervision remains present and measurable.
4. There is a reproducible checkpoint-vs-checkpoint evaluation path.
5. Repository documentation reflects the existence and role of this Phase 2.
6. The pure RL path remains independent of style-constrained features and Pikafish training dependence.

---

## Non-Goals

Do **not** do any of the following in Phase 2:

- style model training
- KL-constrained RL
- search-level style prior mixing
- formal Pikafish benchmark gating
- C++/pybind11 optimization
- distributed training
- UI

---

## Failure Handling

If replay quality regresses:
- inspect natural termination rate
- inspect truncation rate
- inspect non-zero value fraction
- inspect result distribution
- fix the training/data path before scaling further

If checkpoint-vs-checkpoint evaluation shows no clear improvement:
- inspect replay quality first
- inspect training stability second
- inspect evaluation protocol consistency third

Do not jump to style modeling or benchmark complexity before stabilizing the pure RL baseline.

---

## Validation Commands

Codex should define and run concrete validation commands before completion.

Suggested pattern:
- run a multi-iteration self-play training job
- export replay stats
- run evaluation vs random
- run checkpoint-vs-checkpoint comparison
- verify metadata and summaries

If validation fails:
- stop
- fix
- rerun

---

## Completion Note

At the end of Phase 2, produce a short implementation note summarizing:
- training scale reached
- replay quality statistics
- non-zero value fraction
- checkpoint-vs-checkpoint evaluation results
- any remaining non-blocking TODOs
