# Phase 0 — Foundation

## Goal

Build a correct, OpenSpiel-compatible pure-Python Xiangqi MVP and validate that it can survive a minimal AlphaZero-compatible smoke path.

## Required Deliverables

1. XiangqiGame / XiangqiState
   - pure Python
   - OpenSpiel-compatible interface/signature style
   - fixed action space size = 8100
   - observation tensor = 15 planes
   - legal move generation
   - state transition
   - terminal detection
   - returns calculation

2. NotationAdapter
   - FEN
   - ICCS
   - at least one PGN-like / plain-text import format
   - canonical internal normalization

3. DatasetBuilder
   - normalized game records
   - schema-versioned output
   - metadata:
     - action_encoding_version
     - observation_encoding_version
     - dataset_schema_version
     - rules_version

4. Public Data Source Scouting
   - create `docs/data_source_scouting.md`
   - record public Xiangqi data candidates, formats, approximate scale, acquisition method, and future suitability

5. Optional PikafishAdapter
   - only if practical
   - minimal subprocess/UCCI communication
   - bestmove query or scripted play validation
   - must not block Phase 0 success

## Required CLI

- `scripts/normalize_games.py`
- `scripts/validate_xiangqi_game.py`
- `scripts/smoke_alphazero_entry.py`

## Acceptance Criteria

1. Random rollouts complete without illegal state corruption.
2. `num_distinct_actions() == 8100`
3. `observation_tensor_shape()` matches actual tensor size.
4. `returns()` is correct on terminal states.
5. Regression positions pass legality / terminal tests.
6. A minimal AlphaZero-compatible smoke path runs at least one call chain / iteration without interface errors.
7. All generated data artifacts include version metadata.
8. `docs/data_source_scouting.md` is completed.

## Non-Goals

- performance optimization
- full training
- UI
- benchmark framework completion
- dependence on Pikafish

## Validation Commands

Codex should define and run concrete validation commands before declaring completion.
If any validation fails, fix first and rerun.
