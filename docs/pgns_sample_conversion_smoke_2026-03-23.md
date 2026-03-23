# PGNS->FEN tiny sample conversion smoke (2026-03-23)

## Inputs discovered
- `data/import_raw/wxf-41743games_part1.pgns`
- `data/import_raw/wxf-41743games_part2.pgns`

## Tiny conversion attempts
1. Direct raw WXF chunks with converter (`--max-games 3`, `--sample-every-n-plies 40`, `--emit-start-position`)
   - files_seen: 2
   - games_seen: 0
   - games_converted: 0
   - parse_errors: 0
   - emitted_positions: 0

2. Tiny normalized local sample (2 games extracted from part1; only ICCS token shape normalized from `H2-E2` to `h2e2`)
   - files_seen: 1
   - games_seen: 2
   - games_converted: 2
   - parse_errors: 0
   - emitted_positions: 6
   - output: `data/samples/pgns_smoke_positions.jsonl`

## Validation result (`scripts/validate_test_positions.py --fail-on-zero-legal`)
- positions_seen: 6
- valid_fen: 6
- invalid_fen: 0
- zero_legal_moves: 0
- status: ok

## Failure grouping / diagnosis
- Sampled token-shape probe on local WXF chunks (first 800 lines):
  - compact ICCS tokens (`h2e2`): 0
  - hyphen ICCS tokens (`H2-E2`): 1124
- Converter currently only extracts compact ICCS tokens, so direct raw WXF runs emit zero games.

## Judgment
- Not yet healthy for large local-only conversion **from raw WXF chunks**.
- One parser/tokenization fix is needed first: accept hyphenated ICCS move tokens in PGNS movetext.
- After that fix, the downstream FEN emission + validation path looks healthy on the tiny real sample.
