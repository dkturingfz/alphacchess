# Local-only PGNS -> FEN full conversion workflow

Use this when raw PGNS chunks exist locally under `data/import_raw/` and you want a larger conversion run without adding corpora to git.

## Command

```bash
python scripts/build_test_positions_from_games.py \
  --inputs data/import_raw/*.pgns \
  --output artifacts/local_pgns_full_YYYY-MM-DD/positions_raw.jsonl \
  --sample-every-n-plies 12 \
  --emit-start-position \
  --max-games 300 \
  --category-output-dir artifacts/local_pgns_full_YYYY-MM-DD/categories \
  --summary-output artifacts/local_pgns_full_YYYY-MM-DD/conversion_summary.json
```

## Notes

- Conversion replays each move through `XiangqiState` (rules-engine path, not string-only conversion).
- Category split is heuristic:
  - `benchmark_start`: ply 0
  - `opening`: ply 1-20
  - `middlegame`: ply 21-80
  - `endgame`: ply 81+
  - `near_terminal`: terminal positions or legal-move count <= 4
- Keep generated corpora and logs under ignored local-output directories (`artifacts/`, `data/generated/`, `logs/`, or `scratch/`).

## Curate small tracked samples from local corpus

```bash
python scripts/curate_fen_samples.py   --input artifacts/local_pgns_full_YYYY-MM-DD/positions_raw.jsonl   --summary-output artifacts/local_pgns_full_YYYY-MM-DD/fen_curation_summary.json
```

This writes small tracked sample assets to:

- `data/test_positions/samples/`
- `data/benchmark_positions/samples/`

while keeping the full corpus local-only under `artifacts/`.

## Validate all tracked sample assets

```bash
python scripts/validate_fen_samples.py
```

