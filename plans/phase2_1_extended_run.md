# Phase 2.1 — Extended Pure RL Run

## Goal

Run a longer pure-RL training sequence after Phase 2 to determine whether the current AlphaZero-like Xiangqi pipeline remains healthy and improving over a larger training window.

This phase is not about adding new major architecture.
It is about collecting stronger evidence that the current pure RL path is:

- stable
- non-degenerate
- progressively improving
- ready for later profiling and benchmark work

---

## Scope

Phase 2.1 begins only after:
- Phase 0 is complete
- Phase 1 is complete
- Phase 1.1 hardening is complete
- Phase 2 pure RL scale-up is complete

This phase must remain independent of:
- style modeling
- KL regularization
- search-level style guidance
- Pikafish as a training dependency
- UI

This is an extended-run validation phase for the pure RL path.

---

## Required Deliverables

### 1. Longer pure-RL run
Run a meaningfully longer self-play / train sequence than Phase 2.

This should include:
- more iterations
- more games per iteration
- continued replay/stat tracking
- continued checkpoint outputs

The exact scale can depend on practical runtime limits, but it must be clearly larger than the previous Phase 2 validation run.

---

### 2. Replay-quality trend tracking
Across the run, collect and summarize per-iteration replay quality indicators, including at minimum:

- total games
- natural terminations
- step-cap truncations
- result counts
- value mean
- value_non_zero_fraction
- value_positive_count
- value_zero_count
- value_negative_count

The point is not just to inspect one replay, but to observe whether replay quality remains healthy over time.

---

### 3. Checkpoint progress trend tracking
Continue checkpoint-vs-checkpoint internal evaluation across the extended run.

At minimum, support:
- candidate vs previous checkpoint
- optional candidate vs fixed baseline checkpoint

The goal is to see whether progress is:
- improving
- flat
- unstable
- regressing

---

### 4. Consolidated summary output
Produce an extended-run summary that makes it easy for a human to answer:

- Did replay quality remain healthy?
- Did non-zero value supervision remain present?
- Did checkpoint strength trend upward?
- Is the current pure RL path ready for the next stage?

---

### 5. Documentation update
Update docs minimally but clearly so the repository reflects that an extended-run validation phase exists and what it is for.

Acceptable locations:
- README.md
- docs/phase2_file_guide.md
- or a short new doc if needed

---

## Required CLI / Script Expectations

This phase should reuse as much existing infrastructure as possible.

Expected scripts:
- `scripts/train_selfplay.py`
- `scripts/export_replay_stats.py`
- `scripts/evaluate_checkpoints.py`

If useful, add one lightweight helper such as:
- `scripts/summarize_extended_run.py`

but do not overbuild.

---

## Required Testing

At minimum include:

1. regression test that multi-iteration summaries retain required replay-quality fields
2. regression test that checkpoint comparison remains parseable/structured across iterations
3. regression test that non-zero value supervision metrics remain exposed in the output path

Do not add unnecessary large test complexity.

---

## Acceptance Criteria

Phase 2.1 is complete only when all of the following are true:

1. A longer pure-RL training run has been executed successfully.
2. Replay quality metrics are available across iterations, not just a single run.
3. Non-zero value supervision remains present and measurable across the run.
4. Checkpoint-vs-checkpoint evaluation remains available across the run.
5. A consolidated summary exists that makes the trend interpretable.
6. The phase remains independent of style features and Pikafish training dependence.

---

## Non-Goals

Do **not** do any of the following in Phase 2.1:

- style model training
- KL-constrained RL
- search-level style guidance
- formal Pikafish benchmark gating
- C++ optimization
- distributed training
- UI
- major architectural redesign

---

## Failure Handling

If replay quality degrades during the extended run:
- inspect natural termination rate
- inspect truncation rate
- inspect non-zero value fraction
- inspect source breakdown if still relevant
- inspect whether training scale is exposing instability

If checkpoint performance is noisy or inconsistent:
- do not jump to benchmark conclusions
- first determine whether the issue is:
  - sample size
  - replay instability
  - evaluation variance
  - training instability

This phase exists specifically to make those issues visible.

---

## Validation Commands

Codex should define and run concrete validation commands before declaring completion.

Suggested pattern:
- run an extended multi-iteration pure-RL job
- export or summarize replay-quality metrics across iterations
- run checkpoint-vs-checkpoint comparisons
- produce a final consolidated run summary

If validation fails:
- stop
- fix
- rerun

---

## Completion Note

At the end of Phase 2.1, produce a short implementation note summarizing:

- total scale of the extended run
- replay-quality trends
- non-zero value trends
- checkpoint-vs-checkpoint trend
- whether the pure RL path appears stable enough to proceed to profiling / benchmark work
