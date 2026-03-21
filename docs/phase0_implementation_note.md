# Phase 0 Implementation Note

## What Was Built

- Pure-Python Xiangqi environment with OpenSpiel-style game/state APIs:
  - fixed action space (`8100` from-to)
  - fixed observation planes (`15`)
  - legal move generation
  - state transition
  - terminal detection and returns
- Notation adapter with FEN + ICCS + plain-text game import (`FEN | moves`).
- Dataset builder producing schema-v1 normalized records.
- Mandatory version metadata attached to all dataset artifacts.
- Required CLI scripts for normalization, environment validation, and AlphaZero-smoke path.
- Automated tests for legality/terminal regression, action roundtrip, notation normalization, and smoke chain.
- Public data source scouting document.

## Validations Run

- Unit/regression tests under `tests/`.
- CLI validation rollouts.
- CLI smoke AlphaZero call-chain execution.

## Pass Status

All Phase 0 validations pass in the current repository state.

## Non-Blocking TODOs

- Add richer draw rules (repetition/perpetual checks) in later phase.
- Add additional real-world plain-text/PGN-like dialect adapters.
- Expand regression suite with curated historical edge positions.
