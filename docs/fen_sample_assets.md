# Curated FEN sample assets (2026-03-23)

This repository tracks **small, deduplicated** FEN sample sets derived from local PGNS->FEN conversion output.

## Tracked sample files

- `data/test_positions/samples/opening_fens_sample.txt`
- `data/test_positions/samples/middlegame_fens_sample.txt`
- `data/test_positions/samples/endgame_fens_sample.txt`
- `data/test_positions/samples/near_terminal_fens_sample.txt`
- `data/test_positions/samples/regression_fens_sample.txt`
- `data/benchmark_positions/samples/benchmark_start_fens_sample.txt`

## Source and derivation

- Local source corpus path used in this run:
  - `artifacts/local_pgns_full_2026-03-23/positions_raw.jsonl` (local-only, ignored)
- Upstream conversion command:
  - `python scripts/build_test_positions_from_games.py ... --max-games 300 --sample-every-n-plies 12 --emit-start-position`
- Curation command:
  - `python scripts/curate_fen_samples.py --input artifacts/local_pgns_full_2026-03-23/positions_raw.jsonl --summary-output artifacts/local_pgns_full_2026-03-23/fen_curation_summary.json`

## Sampling strategy (compact)

1. Deduplicate by exact FEN per category.
2. Deterministically select evenly spaced samples over `(piece_count, source_ply, fen)` ordering.
3. Keep files small and reviewable for repository tracking.
4. Build a mixed `regression_fens_sample.txt` from the opening/middlegame/endgame/near-terminal curated samples.

## Validation

Validate all tracked sample sets in one command:

```bash
python scripts/validate_fen_samples.py
```

This performs:
- FEN parse/readability checks
- legal move generation sanity checks
- near-terminal rule checks (near-terminal samples must be terminal or have <= 4 legal moves)
- benchmark-start diversity floor checks (at least 4 unique benchmark-start FENs by default)

For a one-command workflow check (validator + pytest module):

```bash
python scripts/check_fen_assets.py
```

Top-level unified entry (CI-friendly):

```bash
make validate
```

`make validate` currently routes to `scripts/check_fen_assets.py`.

## Benchmark-start sample purpose

`data/benchmark_positions/samples/benchmark_start_fens_sample.txt` is a **small exploratory pool** for:
- controlled comparison starts
- smoke-level benchmark wiring checks

To keep this file useful and not trivially repetitive, it intentionally includes:
- the standard initial Xiangqi position
- a few curated early-game starts from the tracked opening sample assets

It is **not** the final official benchmark suite.

For a more statistically stable internal checkpoint sanity pass on this pool (no external engine runtime):

```bash
python scripts/run_benchmark_start_sanity.py \
  --candidate <candidate_checkpoint.json> \
  --baseline <baseline_checkpoint.json> \
  --max-start-positions 8 \
  --games-per-start 4 \
  --seeds 17,29,41,53
```

This script is exploratory sanity evidence only and must **not** be treated as a final benchmark-strength claim.

## Trustworthy local rerun recipe (checkpoint source + sanity check)

If a prior note references a checkpoint path that is not present locally (for example `artifacts/benchmark_start_unattended_2026-03-23/...` on a fresh clone), do **not** reuse that path directly.
First generate a small local training run, then run sanity check against the generated checkpoints.

Verified minimal sequence (PowerShell-safe quoting shown where useful):

```powershell
python scripts/train_selfplay.py `
  --iterations 3 `
  --games-per-iter 4 `
  --max-moves 40 `
  --terminal-enrichment-games 2 `
  --terminal-enrichment-max-moves 6 `
  --epochs 1 `
  --batch-size 64 `
  --quick-eval-games 4 `
  --checkpoint-eval-games 4 `
  --checkpoint-eval-max-moves 60 `
  --seed 123 `
  --out-dir artifacts/local_benchmark_start_repair_2026-03-23/train_small
```

Expected checkpoint outputs:

- `artifacts/local_benchmark_start_repair_2026-03-23/train_small/checkpoints/iter_000.json`
- `artifacts/local_benchmark_start_repair_2026-03-23/train_small/checkpoints/iter_001.json`
- `artifacts/local_benchmark_start_repair_2026-03-23/train_small/checkpoints/iter_002.json`

Then run benchmark_start sanity check on real local files:

```powershell
python scripts/run_benchmark_start_sanity.py `
  --candidate artifacts/local_benchmark_start_repair_2026-03-23/train_small/checkpoints/iter_002.json `
  --baseline artifacts/local_benchmark_start_repair_2026-03-23/train_small/checkpoints/iter_000.json `
  --start-fens data/benchmark_positions/samples/benchmark_start_fens_sample.txt `
  --max-start-positions 4 `
  --games-per-start 2 `
  --max-moves 60 `
  --seeds "17,29" `
  --out artifacts/local_benchmark_start_repair_2026-03-23/benchmark_start_sanity/iter002_vs_iter000.json
```

Expected sanity output:

- `artifacts/local_benchmark_start_repair_2026-03-23/benchmark_start_sanity/iter002_vs_iter000.json`

## Reproducible benchmark_start refresh (local converted corpus -> tracked sample)

Use the local converted corpus JSONL as deterministic input and keep large candidate pools local-only:

```bash
python scripts/refresh_benchmark_start_samples.py \
  --input artifacts/<run>/positions_raw.jsonl \
  --selected-count 12 \
  --max-source-ply 20 \
  --manifest-output artifacts/<run>/benchmark_start_refresh/manifest.json \
  --summary-output artifacts/<run>/benchmark_start_refresh/summary.json \
  --candidate-dump-output artifacts/<run>/benchmark_start_refresh/candidate_pool.jsonl
```

Refresh script outputs include:
- source corpus path
- total candidate count
- deduplicated candidate count
- selected sample count
- diversity stats (piece-count and source-ply spread)
- deterministic selection strategy text

## Git vs local-only boundary

Tracked in git:
- curated sample text files
- curation/validation scripts
- tests/docs

Local-only (ignored):
- full converted corpora under `artifacts/`
- large conversion summaries/logs/manifests

## Current limitations

- These assets are for regression and benchmark preparation; not for final strength claims.
