# Phase 1.1 — Self-play Hardening / Non-zero Value Supervision

## Goal

Strengthen the Phase 1 pure RL loop so that self-play no longer produces almost entirely truncation-dominated replay with degenerate all-zero value targets.

This phase exists to make the Phase 1 training signal materially more trustworthy before scaling the pure RL path further.

The key outcome is:

- self-play produces a meaningful number of natural terminal games
- replay statistics explicitly distinguish natural terminations from truncations
- replay contains a measurable fraction of non-zero value targets
- the value head is exposed to real win/loss supervision rather than almost exclusively zero targets

---

## Context

Phase 1 established a minimal AlphaZero-like loop:

self-play -> replay -> train -> reload -> evaluate

However, the first working Phase 1 implementation revealed a quality problem:

- self-play was heavily dominated by `max-moves` truncation
- replay results were mostly or entirely truncated draws
- value targets collapsed to all zeros

Phase 1.1 is the hardening pass that resolves this training-signal problem.

---

## Scope

Phase 1.1 begins only after Phase 1 is complete.

This phase must remain independent of:

- style modeling
- KL-constrained RL
- search-level style guidance
- Pikafish as a training dependency
- UI
- large-scale benchmark gating

This is still a pure-RL quality-improvement phase.

---

## Required Deliverables

### 1. Self-play termination visibility

The self-play path must explicitly distinguish between:

- natural terminal games
- step-cap truncations

Per iteration and/or per replay export, the repository should expose at least:

- number of games
- number of naturally terminated games
- number of step-cap truncated games
- terminal reason counts where available

---

### 2. Replay result distribution visibility

Replay export must explicitly surface the distribution of game outcomes.

At minimum, replay statistics must make visible:

- win count
- loss count
- draw count
- truncated-draw count

This is required so a human can determine whether replay quality is healthy or degenerate.

---

### 3. Non-zero value supervision

Replay data must contain a measurable fraction of non-zero value targets.

At minimum, replay statistics must expose:

- value mean
- value min
- value max
- count of positive value targets
- count of zero value targets
- count of negative value targets
- fraction of non-zero value targets

The value-learning path must no longer be “effectively all zero”.

---

### 4. Auxiliary terminal-enrichment mechanism (allowed, but secondary)

If needed, a small and well-documented terminal-enrichment mechanism may be used to improve early replay quality.

Rules for such a mechanism:
- it must be explicitly identified in replay metadata
- it must remain auxiliary
- it must not replace the main self-play path
- it must be visible in replay statistics

If present, replay statistics should expose source breakdowns such as:
- selfplay
- terminal_enrichment

---

### 5. Tests protecting the non-zero value path

This phase must add or strengthen tests that verify:

1. terminal returns propagate correctly into replay labels
2. replay serialization preserves game/result/source metadata
3. replay statistics can distinguish:
   - natural terminations
   - truncations
   - non-zero vs zero value distributions
4. at least one deterministic or semi-deterministic path exists in tests that yields non-zero value labels through the pipeline

---

### 6. Documentation updates

Documentation must be updated so a human reader can understand:

- what changed in Phase 1.1
- why Phase 1 replay was previously degenerate
- how replay quality is now measured
- how to interpret natural terminations, truncations, and non-zero value fractions
- whether any terminal-enrichment mechanism exists and what role it plays

At minimum, update:
- `README.md`
- `docs/phase1_file_guide.md` (or equivalent)

---

## Recommended CLI / Script Expectations

Phase 1.1 continues using the Phase 1 script surface, but with improved output semantics.

Key scripts:

- `scripts/train_selfplay.py`
- `scripts/export_replay_stats.py`
- `scripts/evaluate_vs_random.py`

Expected new or improved outputs:
- self-play summary includes natural terminations and truncations
- replay stats include value distribution and result counts
- if replay sources differ, source breakdown is visible

---

## Acceptance Criteria

Phase 1.1 is complete only when all of the following are true:

1. The repository clearly reports whether self-play games end naturally or by hitting the move cap.
2. Replay statistics clearly expose game-result distribution.
3. Replay statistics clearly expose whether value targets are all zero, mixed, or non-zero in a measurable fraction.
4. Replay contains a meaningful non-zero value fraction.
5. Terminal return propagation is covered by regression tests.
6. Documentation clearly explains the updated replay/value semantics.
7. The resulting repository state makes it straightforward for a human to decide whether the pure RL path is healthy enough to proceed.

---

## Non-Goals

Do **not** do any of the following in Phase 1.1:

- style model training
- KL-constrained RL
- search-level style prior mixing
- formal Pikafish benchmark gating
- C++ optimization
- distributed training
- UI

---

## Failure Handling

If replay is still dominated by truncation:
- inspect move-selection behavior
- inspect progression pressure in self-play
- inspect step-cap settings
- inspect whether terminal-enrichment is needed or improperly overwhelming the main path

If value targets are still all zero:
- inspect terminal result propagation
- inspect replay labeling
- inspect whether all games are still effectively truncated draws

Do not proceed to later phases until replay/value supervision is explicit and non-degenerate.

---

## Validation Commands

Codex should define and run concrete validation commands before declaring completion.

Suggested pattern:
- run targeted replay/termination tests
- run a small self-play/training job
- export replay stats
- confirm natural termination and non-zero value visibility
- confirm documentation matches actual outputs

If validation fails:
- stop
- fix
- rerun

---

## Completion Note

At the end of Phase 1.1, produce a short implementation note summarizing:

- what changed in self-play and replay semantics
- how many games terminate naturally vs truncate
- the non-zero value fraction
- whether terminal-enrichment is used
- any remaining non-blocking TODOs
