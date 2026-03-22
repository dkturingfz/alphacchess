# Phase 6 — Search-Level Style Guidance (Optional)

## Goal

Optionally add style guidance at the search prior level **after** the Phase 5 KL-constrained path is stable.

This phase is experimental and optional.

---

## Scope

Phase 6 begins only after Phase 5 is stable.

This phase must remain:
- optional
- isolated
- directly comparable to the best Phase 5 KL-only baseline

Do not replace the KL-only path.

---

## Core Method

Use a mixed prior during search:

P_prior(s, a) = alpha * pi_theta(s, a) + (1 - alpha) * pi_style(s, a)

Where:
- `pi_theta` is the current evolving model
- `pi_style` is the frozen style reference policy
- `alpha` controls model-vs-style prior weight

---

## Required Deliverables

### 1. Optional prior-mixing path

Implement search-level style guidance as switchable behavior.

### 2. Alpha sweep

Evaluate a documented alpha range and compare against best Phase 5 baseline.

### 3. Comparative evaluation

Report:
- strength vs KL-only baseline
- style metrics (global + opening/middlegame/endgame)

---

## Required CLI

Suggested minimum:
- `scripts/train_style_search_guided.py` (or equivalent)
- `scripts/evaluate_style.py`
- `scripts/export_search_style_comparison.py`

---

## Acceptance Criteria

Phase 6 is complete only if:
1. Optional search-level guidance is implemented and isolated.
2. Results are compared against Phase 5 KL-only baseline.
3. Strength + style metrics are both reported.
4. KL-only baseline path remains unchanged and available.

---

## Non-Goals

Do **not** in Phase 6:
- make search guidance default or mandatory
- treat this phase as required for pure-RL progression
- merge strength/style evaluation scripts
