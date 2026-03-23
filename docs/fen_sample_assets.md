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

## Benchmark-start sample purpose

`data/benchmark_positions/samples/benchmark_start_fens_sample.txt` is a **small exploratory pool** for:
- controlled comparison starts
- smoke-level benchmark wiring checks

It is **not** the final official benchmark suite.

## Git vs local-only boundary

Tracked in git:
- curated sample text files
- curation/validation scripts
- tests/docs

Local-only (ignored):
- full converted corpora under `artifacts/`
- large conversion summaries/logs/manifests

## Current limitations

- Current 300-game run yields only one unique `benchmark_start` FEN (all games start from the standard initial position), so the tracked benchmark-start sample pool currently contains one line.
- These assets are for regression and benchmark preparation; not for final strength claims.
