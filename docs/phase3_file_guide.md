# Phase 3 File Guide (Profiling + Benchmark Preparation)

## Scope in current Phase 3

Current Phase 3 is **not** a final strength-claim phase. It focuses on:

1. profiling the pure RL mainline
2. tightening readiness heuristics for quality drift
3. preparing reproducible strength benchmark protocol outputs
4. keeping strength benchmark and style evaluation strictly separate

## Core scripts

### `scripts/profile_rules.py`

Pure-Python hotspot profiling entrypoint for the current RL path.

Profiles at least these components:
- `legal_actions`
- `apply_action`
- `clone`
- self-play loop overhead
- replay serialization path
- checkpoint-vs-checkpoint evaluation path

Example:

```bash
python scripts/profile_rules.py --out artifacts/phase3/profile_report.json
```

Output includes:
- `hotspot_ranking`
- per-component top cumulative-time functions
- stable schema version (`phase3_profile_v1`)

### `scripts/summarize_extended_run.py`

Extended-run summarizer with stricter readiness logic.

New readiness output contains:
- graded status: `pass` / `caution` / `fail`
- per-check thresholds and values
- conservative `ready_for_next_stage` gate (`True` only when grade is `pass`)

Checks cover:
- minimum non-zero value supervision
- maximum truncation rate
- natural termination visibility
- checkpoint progress visibility
- minimum run length

Example:

```bash
python scripts/summarize_extended_run.py --train-summary artifacts/phase2_pure_rl/train_summary.json
```

### `scripts/evaluate_vs_pikafish.py`

Strength benchmark preparation/evaluation protocol script.

Protocol behavior:
- benchmark semantics come from versioned config (`configs/benchmark_pikafish_v1.yaml`)
- engine path comes from CLI/env (`--engine-path` or `PIKAFISH_PATH`), not from versioned config
- result output auto-records:
  - `benchmark_config_name`
  - `benchmark_config_hash`
  - `engine_name`
  - `engine_version`
  - `checkpoint_id`
  - `seed`

Recommended phase-3 usage for reproducibility plumbing:

```bash
python scripts/evaluate_vs_pikafish.py \
  --checkpoint artifacts/phase2_pure_rl/checkpoints/iter_002.json \
  --benchmark-config configs/benchmark_pikafish_v1.yaml \
  --engine-version "$PIKAFISH_VERSION" \
  --dry-run \
  --out artifacts/phase3/benchmark_dry_run.json
```

If local engine path is not configured, `--dry-run` still validates benchmark metadata and hashing.

Important interpretation:
- `--dry-run` and proxy outputs validate protocol wiring, schema, metadata recording, and reproducibility plumbing.
- They do **not** establish final model strength against a real engine runtime.

## Separation discipline

- Strength benchmark path: `scripts/evaluate_vs_pikafish.py`
- Style evaluation path: `scripts/evaluate_style.py`

Do not merge these paths in Phase 3.

## Current limitations

- Engine-runtime gameplay integration against Pikafish is still local-environment dependent.
- Current phase does not make strong benchmark-strength claims.
- Any optimization should be deferred unless repeatedly justified by profiling outputs.

## Meaning of "conditionally ready"

In the current repository state, "ready"/"conditionally ready" means:
- profiling + protocol preparation can proceed,
- benchmark outputs are reproducible at metadata/procedure level,
- and pure-RL readiness checks are currently acceptable.

It does **not** mean:
- milestone-grade strength conclusions are already established.
