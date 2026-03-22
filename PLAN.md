## Project Overview

Build a Xiangqi reinforcement learning system anchored on an OpenSpiel-compatible game/state interface.

Two long-term goals:

1. A pure AlphaZero-like Xiangqi system.
2. A style-constrained RL extension that preserves a target player's stylistic corridor while improving strength.

---

## Global Rules

- Follow repository rules in `AGENTS.md`.
- Stay strictly within the current phase boundary.
- Do not implement later-phase features unless required by current-phase acceptance criteria.
- If validation fails, fix first, then continue.
- The core path must not depend on Pikafish.
- Pikafish is optional for warm-start data and benchmark only.
- Current priority after Phase 1.1 is to strengthen and scale the pure RL path before returning to the deferred style-constrained phases.

---

## Phase Order

### 1. Phase 0 — Foundation
See: `plans/phase0.md`

### 2. Phase 1 — Minimal AlphaZero Loop
See: `plans/phase1.md`

### 3. Phase 1.1 — Self-play Hardening / Non-zero Value Supervision
Goal:
- improve self-play terminal diversity
- reduce truncation-dominated replay
- ensure replay contains measurable non-zero value supervision

See: `plans/phase1_1.md`

### 4. Phase 2 — Pure RL Scale-Up
Goal:
- strengthen and stabilize the pure AlphaZero-like training path
- scale self-play / replay / training
- add checkpoint-vs-checkpoint internal evaluation
- keep the mainline independent of style-constrained features

See: `plans/phase2_pure_rl.md`

### 5. Phase 2.1 — Extended Pure RL Run
Goal:
- run a longer pure-RL training sequence
- collect stronger replay-quality trend evidence
- observe checkpoint-vs-checkpoint progress across more iterations
- determine whether the pure RL path is stable enough for profiling / benchmark preparation

See: `plans/phase2_1_extended_run.md`

### 6. Phase 3 — Profiling + Benchmark Preparation
Goal:
- profile bottlenecks in the pure RL path
- prepare a reproducible benchmark path
- tighten readiness heuristics
- keep benchmark and style evaluation separate
- avoid making strong final benchmark claims before readiness checks are consistently satisfied

See: `plans/phase3.md`

### 7. Phase 4 — Style Reference Model
Goal:
- train a frozen style reference policy `pi_style`
- evaluate style quality globally and by phase
- enforce unusable / gray / usable / preferred thresholds

See: `plans/phase4_style_reference.md`

### 8. Phase 5 — KL-Constrained Style RL
Goal:
- add loss-level KL regularization against `pi_style`
- explore the strength/style tradeoff with structured beta search

See: `plans/phase5_kl_style_rl.md`

### 9. Phase 6 — Search-Level Style Guidance (Optional)
Goal:
- optionally mix style priors into search
- compare against the best KL-only baseline
- keep this path experimental and isolated

See: `plans/phase6_search_style_guidance.md`

---

## Execution Discipline

For any current task:

- read `AGENTS.md`
- read this `PLAN.md`
- read the active phase file under `plans/`
- complete only that phase's scope
- run validations before declaring completion
- do not skip ahead to style-constrained phases while the pure RL mainline is still being stabilized
- do not interpret benchmark-preparation artifacts as final benchmark claims unless stricter readiness checks are consistently satisfied
