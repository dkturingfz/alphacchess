# Phase 1 — Minimal AlphaZero Loop

## Goal

Build the minimal end-to-end AlphaZero-like loop on top of the completed Phase 0 Xiangqi environment.

This phase exists to prove that the project is truly alive:

self-play -> collect replay -> train -> reload -> evaluate

The goal of Phase 1 is **not** high strength.
The goal is to verify that the full reinforcement-learning loop runs correctly and produces a model that is clearly stronger than a random baseline.

---

## Scope

Phase 1 begins only after Phase 0 is complete and validated.

This phase must remain independent of:
- Pikafish
- style constraints
- UI
- benchmark gating
- large-scale optimization

---

## Required Deliverables

### 1. PolicyValueNet v1

Implement the first trainable neural network used by the RL loop.

Requirements:
- input shape must exactly match `observation_tensor_shape()`
- policy head output dimension must exactly match `num_distinct_actions() == 8100`
- value head output must be a scalar
- architecture should remain compatible with later AlphaZero-style self-play and evaluation code

Notes:
- Keep the architecture simple and robust
- Do not over-optimize or over-complicate
- Prefer stable, debuggable implementation

---

### 2. Self-Play Loop v1

Implement a minimal self-play pipeline.

Requirements:
- small scale only
- use the Phase 0 Xiangqi environment
- generate per-position replay/training records
- store, reload, and validate replay data

Replay examples should contain at least:
- encoded observation or recoverable state reference
- policy target
- value target
- metadata/version fields

---

### 3. Trainer v1

Implement a trainer that:
- consumes replay/self-play data
- trains the policy/value model
- writes checkpoints
- logs basic training metrics

Checkpoint outputs must include metadata linking them to:
- encoding versions
- rules version
- dataset schema version

---

### 4. Evaluator v1

Implement an evaluator that compares the trained model against a random baseline.

This evaluator is only for the minimal success criterion of the RL loop.
It is not a benchmark against Pikafish.

---

## Required CLI

The following scripts must exist and be runnable:

- `scripts/train_selfplay.py`
- `scripts/evaluate_vs_random.py`
- `scripts/export_replay_stats.py`

Optional helper scripts may be added if useful, but these three are required.

---

## Required Testing

At minimum, include:

1. unit test for model input/output dimensions
2. integration test for one full loop:
   - self-play
   - replay write
   - replay read
   - train
   - reload
   - evaluate
3. replay serialization/deserialization regression test
4. test that policy output always aligns with action-space size = 8100
5. test that value output is scalar and wired correctly

---

## Acceptance Criteria

Phase 1 is complete only if all of the following are true:

1. Several full iterations of:
   self-play -> train -> reload model -> evaluate
   complete successfully.

2. The trained model beats a random policy baseline with:
   - **win rate > 90% over 100 games**

3. Policy output dimension remains exactly 8100.

4. Value head remains scalar.

5. Replay data is readable, version-validated, and does not silently mismatch encoding versions.

6. The Phase 1 path has **no hidden dependence on Pikafish**.

---

## Non-Goals

Do **not** do any of the following in Phase 1 unless absolutely necessary for the acceptance criteria:

- style modeling
- KL regularization
- MCTS style prior mixing
- UI
- benchmark against Pikafish
- large-scale training
- performance optimization
- C++ acceleration

---

## Failure Handling

If the model fails to exceed 90% win rate against random after the loop is implemented:

Treat this as a likely correctness/debugging issue first, not a training-scale issue.

Inspect in this order:
1. legal action masking
2. action encoding / decoding alignment
3. replay target correctness
4. reward / returns sign convention
5. value-target wiring
6. observation encoding consistency
7. checkpoint reload correctness

Do not jump to large-scale training or architecture changes before checking the pipeline.

---

## Validation Commands

Codex should define and run concrete validation commands before declaring completion.

Suggested pattern:
- run unit tests
- run one short integration pipeline
- run 100-game evaluation vs random
- export replay stats
- verify version metadata in produced artifacts

If any validation fails:
- stop
- fix
- rerun
- repeat until acceptance criteria are satisfied

---

## Completion Note

At the end of Phase 1, produce a short implementation note summarizing:
- what was built
- what training/evaluation path was implemented
- what validations were run
- exact win rate vs random over 100 games
- any non-blocking TODOs left for later phases
