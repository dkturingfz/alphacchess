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

For a small internal checkpoint sanity pass on this pool (no external engine runtime):

```bash
python scripts/run_benchmark_start_sanity.py \
  --candidate <candidate_checkpoint.json> \
  --baseline <baseline_checkpoint.json> \
  --max-start-positions 5 \
  --games-per-start 2 \
  --seeds 17,29
```

This script is exploratory sanity evidence only and must **not** be treated as a final benchmark-strength claim.

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
