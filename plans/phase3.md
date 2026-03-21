# Phase 3 — Scale, Profile, Optimize, Benchmark

## Goal

Scale up the Xiangqi RL system, benchmark it rigorously, and optimize only after profiling identifies true bottlenecks.

This phase is where the project becomes more serious in training scale and evaluation discipline.

It must only begin after the model passes both:
- a strength gate
- a style-retention gate

under the same fixed benchmark protocol.

---

## Entry Gate

A checkpoint may enter Phase 3 only if:

1. it satisfies the required **strength gate**
2. it satisfies the required **style gate**
3. these results are obtained under the same benchmark/evaluation protocol
4. all required seeds for the milestone evaluation pass the gate

The exact thresholds may be project-specific, but they must be quantitative and documented.

---

## Required Deliverables

### 1. Training Scale-Up

Add support for larger experiments:
- increased self-play volume
- increased training iterations
- larger replay buffers
- structured experiment configs

This phase is where the small Phase 1/2 training path becomes a larger-scale training system.

---

### 2. Profiling Gate

Before any optimization or rewrite, run profiling.

At minimum profile:
- `legal_actions()`
- `apply_action()`
- state copy / update
- search overhead

Produce a profiling report identifying the dominant bottlenecks.

No low-level optimization should happen before this report exists.

---

### 3. Optional Hot-Path Acceleration

If profiling confirms that the Python Xiangqi rules core is the main bottleneck, then and only then:

- rewrite only the hot path
  - move generation
  - state update
- use C++ / pybind11 or similar if needed
- preserve upper-layer interfaces
- preserve artifact compatibility

The purpose is performance gain without architectural breakage.

---

### 4. Strength Benchmarking

Implement and use a dedicated strength benchmark path against Pikafish.

This must use:
- a fixed versioned benchmark config
- separate local engine path configuration
- automatic result metadata recording

The benchmark path must remain separate from training logic.

---

### 5. Style Benchmarking

Style evaluation must remain separate from strength benchmarking.

Use the separate style evaluation script and config.
Do not merge the two evaluation paths.

---

## Benchmark Rules in Phase 3

### Strength Benchmark Script
Use:
- `scripts/evaluate_vs_pikafish.py`

This script is responsible only for strength evaluation.

It must automatically record:
- benchmark config name
- benchmark config hash
- engine name
- engine version
- checkpoint id
- seed

### Benchmark Config v1
A benchmark config version such as `configs/benchmark_pikafish_v1.yaml` must define only benchmark semantics.

Recommended benchmark v1 semantics:
- depth-only search limit
- `games_per_side`
- explicit `evaluation_seeds`
- `swap_colors`
- `resign_enabled: false`
- `draw_adjudication_enabled: false`
- `max_moves`
- `max_moves_result: draw`

### Comparability Rule
Strength benchmark results are directly comparable only when:
- benchmark config identity matches
- engine version matches

If Pikafish changes version, previous results are not directly comparable without rerunning the baseline.

---

## Style Evaluation Rules in Phase 3

Use:
- `scripts/evaluate_style.py`
- `configs/style_eval_v1.yaml`

Style metrics must remain phase-aware:
- opening
- middlegame
- endgame

The strength benchmark script must not take on style evaluation duties.

---

## Required CLI

At minimum:

- `scripts/run_experiment.py`
- `scripts/profile_rules.py`
- `scripts/benchmark_checkpoints.py`
- `scripts/evaluate_vs_pikafish.py`
- `scripts/evaluate_style.py`

Additional helper scripts are acceptable if useful.

---

## Required Testing

At minimum include:

1. profiling report generation test or smoke check
2. benchmark config parsing test
3. benchmark metadata recording test
4. test that benchmark and style evaluation paths remain separate
5. if hot-path acceleration is introduced:
   - regression tests showing upper-layer behavior remains unchanged

---

## Acceptance Criteria

Phase 3 is complete only if all of the following are true:

1. A larger-scale training path exists and runs successfully.
2. A profiling report exists.
3. If optimization is introduced, upper-layer interfaces remain unchanged.
4. Strength benchmarking is reproducible and metadata-complete.
5. Style benchmarking remains separate and phase-aware.
6. Artifact versioning remains consistent.
7. Milestone comparisons are made only when both benchmark config identity and engine version match.

---

## Non-Goals

Do **not** do any of the following in Phase 3 unless explicitly required:

- merge strength and style evaluation into one script
- make Pikafish part of the training core
- break compatibility with earlier artifact schemas without versioning
- silently change benchmark semantics within an existing benchmark version

---

## Failure Handling

If Phase 3 benchmark results look inconsistent:
check in this order:
1. benchmark config identity
2. engine version
3. seed handling
4. checkpoint identity
5. color balancing
6. max-move termination handling

If scaling fails due to speed:
- confirm with profiling first
- only then optimize

If optimization changes behavior:
- revert
- restore interface stability
- add regression tests

---

## Validation Commands

Codex should define and run concrete validation commands before completion.

Suggested pattern:
- run scaled experiment
- generate profiling report
- run benchmark against Pikafish under fixed config
- run style evaluation separately
- verify metadata fields in outputs
- compare results only under matching config+engine conditions

If validation fails:
- stop
- fix
- rerun

---

## Completion Note

At the end of Phase 3, produce a short implementation note summarizing:
- the scale of training reached
- profiling conclusions
- whether hot-path acceleration was necessary
- benchmark setup used
- style metrics used
- benchmark comparability conditions
- any remaining TODOs for future research or engineering work
