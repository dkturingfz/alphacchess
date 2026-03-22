# Phase 4 — Style Reference Model

## Goal

Train and freeze a usable style reference policy `pi_style`, then evaluate it with a phase-aware protocol before any style-constrained RL is attempted.

This phase establishes quality gates for style modeling. It does **not** include KL-constrained RL training itself.

---

## Scope

Phase 4 begins only after:
- Phase 0 complete
- Phase 1 complete
- Phase 1.1 complete
- Phase 2 complete
- Phase 2.1 complete
- Phase 3 profiling + benchmark preparation workflow is in place

Current repository priority remains pure-RL readiness and benchmark preparation; this style phase is currently deferred.

---

## Required Deliverables

### 1. Frozen style reference training path

Provide a training path that outputs a **frozen** style reference checkpoint:
- optional generic pretrain
- target-player fine-tune
- reproducible report output

### 2. Phase-aware style evaluation

Evaluate with `configs/style_eval_v1.yaml` and report:
- global top-1 / top-3
- opening top-1 / top-3
- middlegame top-1 / top-3
- endgame top-1 / top-3

### 3. Quality threshold enforcement

Enforce threshold bands:
- `top-1 < 25%` => `unusable`
- `25% <= top-1 < 35%` => `gray`
- `top-1 >= 35%` => `usable`
- `top-1 >= 40%` => `preferred`

### 4. Gray-zone recovery workflow

If `gray`, run structured recovery in order:
1. verify data/eval pipeline
2. strengthen generic-pretrain -> target fine-tune path
3. optional left-right mirror augmentation
4. only then consider larger model capacity

---

## Required CLI

- `scripts/train_style_reference.py`
- `scripts/evaluate_style.py`
- `scripts/run_style_recovery.py`

---

## Acceptance Criteria

Phase 4 is complete only when all of the following are true:

1. A frozen style-reference checkpoint is produced with metadata.
2. Phase-aware style metrics are reported.
3. Quality band classification is explicit (`unusable`/`gray`/`usable`/`preferred`).
4. Gray-zone recovery workflow is runnable and reportable.
5. Documentation clearly states whether the current checkpoint is usable or deferred.

---

## Non-Goals

Do **not** do any of the following in Phase 4:
- KL-constrained RL
- search-level style guidance
- benchmark-strength claims
- training-core redesign
- making Pikafish part of the RL training core

---

## Validation Commands

Codex should define and run concrete validation commands before completion.

Suggested pattern:
- train style reference checkpoint
- run style evaluation
- if gray, run recovery workflow
- archive evaluation + recovery reports with version metadata
