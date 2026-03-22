# Phase 5 — KL-Constrained Style RL

## Goal

Train a stronger Xiangqi self-play model while constraining it to remain close to the frozen style reference policy `pi_style`.

This phase introduces style-constrained reinforcement learning via **loss-level KL regularization**.
Search-level style guidance is explicitly out of scope for this phase.

---

## Scope

Phase 5 begins only after:

- Phase 4 has produced a usable style reference model
  - minimum requirement: `top-1 >= 35%`

This phase modifies the RL objective, not the search prior.

---

## Core Method

Use a KL-regularized objective of the form:

L = L_base + beta * KL(pi_theta || pi_style)

Where:
- `L_base` is the existing pure-RL objective
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

### 2. Structured Beta Search

Use a structured plan.

#### Coarse Sweep
Run at least:
- `beta = 0.01`
- `beta = 0.1`
- `beta = 1.0`
- `beta = 10.0`

#### Fine Sweep
After coarse sweep, run a finer search in the most informative interval.

### 3. Optional Beta Schedule

Only after fixed-beta baselines are stable, allow optional schedule experiments.

### 4. Evaluation Outputs

Produce:
- strength outputs
- style outputs (global + opening/middlegame/endgame)
- strength-vs-style tradeoff summary

---

## Required CLI

- `scripts/train_style_constrained_rl.py`
- `scripts/evaluate_style.py`
- `scripts/export_tradeoff_report.py`

---

## Acceptance Criteria

Phase 5 is complete only if:
1. KL-constrained model trains successfully.
2. Style similarity improves relative to pure-RL baseline.
3. Strength does not collapse versus baseline.
4. Coarse + fine beta sweeps are complete.
5. Tradeoff report is generated.

---

## Non-Goals

Do **not** in Phase 5:
- search-level style prior mixing
- benchmark-trigger large-scale progression claims
- hot-path optimization
- UI work
