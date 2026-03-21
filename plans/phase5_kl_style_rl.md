# Phase 2a — KL-Constrained Style RL

## Goal

Train a stronger Xiangqi self-play model while constraining it to remain close to the frozen style reference policy `pi_style`.

This phase introduces style-constrained reinforcement learning via **loss-level KL regularization**.
This is the first and preferred style-constrained RL mechanism.

Search-level style guidance is explicitly out of scope for this phase.

---

## Scope

Phase 2a begins only after:

- Phase 1 is complete
- Phase 1b has produced a usable style reference model
  - minimum requirement: `top-1 >= 35%`

This phase modifies the RL objective, not the search prior.

---

## Core Method

Use a KL-regularized objective of the form:

L = L_base + beta * KL(pi_theta || pi_style)

Where:
- `L_base` is the existing Phase 1 RL objective
- `pi_theta` is the evolving policy
- `pi_style` is the frozen style reference policy
- `beta` controls the strength/style tradeoff

---

## Required Deliverables

### 1. Style-Constrained RL Trainer

Implement a training path that:
- loads the frozen `pi_style`
- computes style regularization
- trains the main evolving model using self-play data
- preserves compatibility with the existing self-play pipeline

This trainer must not mutate `pi_style`.

---

### 2. Structured Beta Search

This phase must not treat `beta` as a casual tuning knob.
Use a structured plan.

#### Coarse Sweep
Run at least the following values:

- `beta = 0.01`
- `beta = 0.1`
- `beta = 1.0`
- `beta = 10.0`

The purpose of the coarse sweep is to locate the tradeoff region.

#### Fine Sweep
After the coarse sweep, select the most informative interval and run a finer search inside it.

The exact fine-grid values may depend on coarse results, but the process must be documented.

---

### 3. Optional Beta Schedule

Only after fixed-beta baselines are stable, allow an optional experiment with a beta schedule.

This is an experimental extension, not a baseline requirement.

Examples:
- linear decay
- cosine decay
- step decay

Do not use schedules before the fixed-beta baseline is validated.

---

### 4. Evaluation Outputs

This phase must produce both:

#### Strength outputs
- relative strength compared with the Phase 1 baseline
- consistent evaluation outputs suitable for later benchmark comparison

#### Style outputs
- global style match metrics
- opening/middlegame/endgame style metrics

#### Tradeoff outputs
- summary of strength vs style retention across beta values

The point of this phase is not only to train, but to map the tradeoff curve.

---

## Required CLI

- `scripts/train_style_constrained_rl.py`
- `scripts/evaluate_style.py`
- `scripts/export_tradeoff_report.py`

If needed, helper scripts may be added, but the above are required.

---

## Required Testing

At minimum include:

1. test that frozen `pi_style` is loaded correctly and remains frozen
2. test that KL term is computed with the correct tensor shapes
3. test that training runs when style regularization is enabled
4. test that beta is actually applied from configuration
5. regression test that style metrics still use the same opening/middlegame/endgame split

---

## Acceptance Criteria

Phase 2a is complete only if all of the following are true:

1. The style-constrained model trains successfully using the self-play pipeline.
2. Relative to pure Phase 1 RL, style similarity is improved.
3. Relative to pure Phase 1 RL, the model still shows strength improvement over the original baseline.
4. A coarse beta sweep has been completed.
5. A fine beta sweep has been completed.
6. All style reports include:
   - global metrics
   - opening metrics
   - middlegame metrics
   - endgame metrics
7. A tradeoff report exists showing the relationship between beta, strength, and style retention.

---

## Non-Goals

Do **not** do any of the following in Phase 2a:

- search-level style prior mixing
- benchmark-trigger gating into large-scale training
- hot-path optimization
- C++ rewrite
- UI

---

## Failure Handling

If KL-constrained RL fails to preserve style:

Check in this order:
1. whether `pi_style` quality is actually above threshold
2. whether frozen checkpoint loading is correct
3. whether KL is computed on the intended policy distribution
4. whether legal-action masking is consistent between `pi_theta` and `pi_style`
5. whether beta is too small

If KL-constrained RL preserves style but destroys strength:

Check:
1. whether beta is too large
2. whether fine sweep explored a meaningful region
3. whether the value / policy balance has been distorted by regularization

Do not jump immediately to search-level mixing; first stabilize the KL path.

---

## Validation Commands

Codex should define and run concrete validation commands before completion.

Suggested pattern:
- run coarse sweep
- run fine sweep
- export strength/style tradeoff
- confirm phase-aware style metrics
- compare against Phase 1 baseline

If validation fails:
- stop
- fix
- rerun

---

## Completion Note

At the end of Phase 2a, produce a short implementation note summarizing:
- frozen style checkpoint used
- coarse beta sweep results
- fine beta sweep results
- best tradeoff checkpoint(s)
- strength delta vs Phase 1
- global and phase-aware style retention
- whether optional beta schedule experiments were attempted
