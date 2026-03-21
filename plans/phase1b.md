# Phase 1b — Style Reference Model

## Goal

Train a **frozen style reference policy** `pi_style` that captures the stylistic tendencies of a target player well enough to define a usable style corridor for later style-constrained RL.

This phase is important, but it must remain independent from the main self-play RL path.
The core project must still work without it.

---

## Scope

Phase 1b begins only after Phase 1 is complete.

This phase focuses on:
- collecting target-player style data
- training a style reference model
- evaluating whether the model truly captures the target player's move tendencies
- deciding whether the style model is strong enough to be used in later KL-constrained RL

This phase does **not** implement style-constrained RL yet.

---

## Data Strategy

### Preferred Training Path

Use this strategy in order:

1. train directly on target-player records if data is sufficient
2. if target-player data is limited:
   - first pretrain on broader public Xiangqi game records
   - then fine-tune on target-player records

### Data Source Requirement

Phase 0 should already have produced `docs/data_source_scouting.md`.

Use that scouting result here to determine:
- which generic data sources are available
- which sources are suitable for broad pretraining
- which target-player sources are available for style fine-tuning

---

## Required Deliverables

### 1. Style Model Training Path

Implement training support for:
- direct target-player style training
- generic-pretrain -> personal-finetune training

This may reuse the same base network family as the Phase 1 policy/value model if appropriate, but the style reference model must ultimately be frozen.

---

### 2. Style Evaluation

Implement `scripts/evaluate_style.py`.

This script must be separate from strength benchmarking.

It must evaluate the model on target-player historical positions and report:

- global top-1 match
- global top-3 match
- opening top-1 / top-3
- middlegame top-1 / top-3
- endgame top-1 / top-3

Optional additional metrics may be added, but the above are required.

---

### 3. Style Evaluation Protocol

Create `docs/style_eval_protocol.md`.

The first version must define the phase split using simple ply ranges:

- opening: ply 1–20
- middlegame: ply 21–60
- endgame: ply 61+

This split is intentionally simple and should be used consistently in later phases for comparability.

---

### 4. Frozen Style Checkpoint

Produce a style reference checkpoint that is explicitly frozen and loadable by later phases.

This checkpoint must be versioned and documented.

---

### 5. Style Recovery Plan

Implement `scripts/run_style_recovery.py`.

This script is required because style model quality may fall into a gray zone.

The recovery plan must support, in order:

1. evaluation/data integrity checks
2. stronger generic-pretrain -> personal-finetune
3. lightweight augmentation:
   - left-right mirror only for v1
4. only then consider increasing model capacity

---

## Style Quality Thresholds

The style reference model must be classified into one of the following zones.

### A. Unusable
- `top-1 < 25%`

Interpretation:
- the style model is not good enough to define a reliable style corridor

Action:
- do not proceed to Phase 2a
- inspect data and evaluation pipeline first

---

### B. Gray Zone
- `25% <= top-1 < 35%`

Interpretation:
- the model has learned something, but is not stable enough to be used directly as the style reference in constrained RL

Action:
- do **not** proceed directly to Phase 2a
- run the full Style Model Recovery Plan

---

### C. Usable
- `top-1 >= 35%`

Interpretation:
- the model is good enough to define a style corridor for Phase 2a

Action:
- allowed to proceed to Phase 2a

---

### D. Preferred
- `top-1 >= 40%`

Interpretation:
- this is the preferred quality level for the style reference model

Action:
- treat this checkpoint as the preferred `pi_style`

---

## Gray Zone Recovery Policy

If the style model lands in the gray zone, do not improvise ad hoc fixes.
Use the following ordered recovery procedure:

1. verify:
   - evaluation split correctness
   - target-player data identity
   - notation parsing correctness
   - FEN reconstruction correctness
   - action encoding alignment
   - legal move masking in evaluation

2. strengthen:
   - generic pretraining scale
   - fine-tuning quality on target-player records

3. apply lightweight augmentation:
   - left-right mirror only

4. only if still in gray zone:
   - increase model capacity
   - rerun training and evaluation

The result after recovery must again be classified using the same thresholds.

---

## Required CLI

- `scripts/train_style_reference.py`
- `scripts/evaluate_style.py`
- `scripts/run_style_recovery.py`

---

## Required Testing

At minimum include:

1. test that style evaluation reads target records correctly
2. test that phase split (opening/middlegame/endgame) is applied correctly
3. test that top-1 / top-3 metrics are computed consistently
4. test that style checkpoints can be frozen and reloaded
5. test that recovery pipeline can run from a previous checkpoint/config

---

## Acceptance Criteria

Phase 1b is complete only if all of the following are true:

1. A frozen style checkpoint is produced.
2. Style evaluation metrics are reported:
   - globally
   - for opening
   - for middlegame
   - for endgame
3. Threshold logic is enforced exactly:
   - `<25%` unusable
   - `25–35%` gray zone, recovery required
   - `>=35%` usable
   - `>=40%` preferred
4. The style checkpoint is loadable by later phases.
5. The style path remains optional and does not break the main RL path.

---

## Non-Goals

Do **not** do any of the following in Phase 1b:

- KL-constrained RL
- search-level style prior mixing
- Pikafish benchmark gating
- large-scale benchmark infrastructure
- UI

---

## Validation Commands

Codex should define concrete commands and run them before completion.

Suggested pattern:
- train style reference
- run style evaluation
- verify phase-split metrics
- if gray zone, run recovery
- reevaluate
- confirm threshold status

If any validation fails:
- stop
- fix
- rerun

---

## Completion Note

At the end of Phase 1b, produce a short implementation note summarizing:
- data sources used
- whether generic pretraining was used
- final style thresholds achieved
- opening/middlegame/endgame metrics
- whether recovery was needed
- which checkpoint is the official frozen `pi_style`
