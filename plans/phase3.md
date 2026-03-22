# Phase 3 — Profiling + Benchmark Preparation

## Goal

After Phase 2.1 extended pure-RL validation, Phase 3 focuses on:

1. profiling the current pure-RL path
2. preparing reproducible benchmark protocol plumbing
3. tightening readiness interpretation before any strong benchmark claim

This phase is a preparation and discipline phase, not a final-strength proclamation phase.

---

## Scope

Phase 3 begins only after:
- Phase 0 / 1 / 1.1 complete
- Phase 2 / 2.1 complete

Current emphasis:
- correctness of protocol and metadata
- reproducibility of benchmark setup
- conservative readiness gating

Out of scope for this phase:
- style-phase advancement
- hard milestone strength claims without longer-run readiness evidence

---

## Required Deliverables

### 1. Profiling report

Use profiling to identify hotspots in:
- `legal_actions()`
- `apply_action()`
- clone/copy paths
- self-play loop overhead

Produce versioned profiling output.

### 2. Benchmark protocol implementation

Provide benchmark workflow driven by a fixed versioned config (`configs/benchmark_pikafish_v1.yaml`) with automatic recording of:
- benchmark config name/hash
- engine name/version
- checkpoint id
- seed

### 3. Dry-run / proxy validation path

Provide `--dry-run` and/or proxy modes that validate protocol wiring and metadata capture even without local engine runtime.

### 4. Readiness interpretation discipline

Document and expose a conservative handoff gate from pure-RL trends to benchmark preparation.

---

## Required CLI

- `scripts/profile_rules.py`
- `scripts/summarize_extended_run.py`
- `scripts/evaluate_vs_pikafish.py`

---

## Acceptance Criteria

Phase 3 is complete only when all are true:

1. Profiling artifacts exist and are reproducible.
2. Benchmark protocol metadata plumbing is implemented and testable.
3. Dry-run/proxy outputs clearly state their non-final-strength nature.
4. Readiness outputs are conservative and documented.
5. Benchmark and style-eval paths remain separate.

---

## Non-Goals

Do **not** in Phase 3:
- claim final benchmark strength from dry-run/proxy outputs
- merge style evaluation into benchmark script
- make Pikafish a training-core dependency
- do C++ rewrites without profiling justification
