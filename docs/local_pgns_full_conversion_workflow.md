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
