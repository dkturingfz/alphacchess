# Phase 2b — Search-Level Style Guidance (Optional)

## Goal

Optionally add style guidance at the search prior level after the KL-constrained style RL path is stable.

This phase is an **experimental extension**, not part of the core mandatory training path.

---

## Scope

Phase 2b begins only after Phase 2a is stable.

This phase must remain:
- optional
- isolated
- directly comparable to the best Phase 2a baseline

Do not replace the KL-only path.
Do not merge this logic irreversibly into the core RL training path.

---

## Core Method

Use a mixed prior during search:

P_prior(s, a) = alpha * pi_theta(s, a) + (1 - alpha) * pi_style(s, a)

Where:
- `pi_theta` is the current evolving model
- `pi_style` is the frozen style reference policy
- `alpha` controls how much the search prior follows the current model vs the style model

This phase studies whether search-level bias can preserve style more effectively than KL-only training.

---

## Required Deliverables

### 1. Prior Mixing Implementation

Implement search-level style guidance as an optional mechanism.

Requirements:
- keep it switchable
- keep KL-only baseline intact
- allow alpha to be configured

---

### 2. Alpha Sweep

Evaluate several alpha values.

The exact sweep values may be chosen pragmatically, but the sweep must:
- cover a meaningful range
- be documented
- be compared directly to the best Phase 2a KL-only baseline

---

### 3. Comparative Evaluation

For each evaluated alpha setting, report:

#### Strength
- relative to KL-only baseline

#### Style
- global style metrics
- opening/middlegame/endgame style metrics

#### Optional Search Behavior Notes
- if the implementation can conveniently surface useful search-level observations, record them
- do not overbuild this part

---

## Required CLI

Suggested minimum:
- `scripts/train_style_search_guided.py` or equivalent
- `scripts/evaluate_style.py`
- `scripts/export_search_style_comparison.py`

Names may differ, but search-guided training/evaluation must be clearly separated from Phase 2a.

---

## Required Testing

At minimum include:

1. test that prior mixing is disabled when not requested
2. test that prior mixing correctly combines `pi_theta` and `pi_style`
3. test that alpha parameter is actually respected
4. regression test that KL-only path still behaves unchanged when search guidance is off

---

## Acceptance Criteria

Phase 2b is complete only if all of the following are true:

1. Search-level style guidance is implemented as an optional, isolated path.
2. Results are compared against Phase 2a KL-only baselines.
3. Strength and style metrics are reported.
4. Style metrics remain phase-aware:
   - opening
   - middlegame
   - endgame
5. Reproducibility and artifact metadata tracking remain intact.
6. The KL-only path remains available and unchanged as a baseline.

---

## Non-Goals

Do **not** do any of the following in Phase 2b:

- replace KL with search-level guidance as the default
- make search-level guidance mandatory
- perform large-scale benchmark gating
- perform hot-path optimization
- build UI

---

## Failure Handling

If search-level guidance gives no advantage:
- document that KL-only remains the preferred path
- keep the feature optional
- do not force it into the mainline

If search-level guidance improves style but harms strength badly:
- report that tradeoff clearly
- do not silently promote it to the default

This phase is exploratory and comparative.

---

## Validation Commands

Codex should define and run concrete validation commands before completion.

Suggested pattern:
- run alpha sweep
- compare against best Phase 2a checkpoint
- export side-by-side comparison report
- verify phase-aware style metrics

If validation fails:
- stop
- fix
- rerun

---

## Completion Note

At the end of Phase 2b, produce a short implementation note summarizing:
- which Phase 2a baseline was used
- alpha values explored
- whether search-level style guidance improved style retention
- whether it improved or harmed strength
- whether it should remain a purely experimental branch
