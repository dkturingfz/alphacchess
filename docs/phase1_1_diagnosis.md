# Phase 1.1 Diagnostic Note: Why Self-Play Was Truncation-Dominated

## Observed issue

Recent hardening runs showed replay dominated by `truncated_draw` and `value_target=0`.

## Primary causes identified

1. **Weak early policy signal + residual randomness**
   - Untrained policy logits are effectively noise.
   - Self-play still includes random exploration (`exploration_eps`), so many games wander.

2. **Terminal states are sparse from the standard initial position under weak play**
   - Without strong tactical pressure, many games avoid immediate decisive exchanges.

3. **Fixed move cap turns uncertainty into draw-heavy labels**
   - When no natural terminal occurs before `max_moves`, outcomes are forced to truncated draws.
   - This collapses value supervision toward zero.

## Phase 1.1 response (narrow scope)

- Keep the main self-play path unchanged in architecture.
- Add immediate-terminal move preference in action selection.
- Add an explicit, controlled `terminal_enrichment` game source to inject legitimate non-zero win/loss labels.
- Track source-level replay statistics so supervision provenance is transparent.

## Why this is legitimate

- `terminal_enrichment` uses legal Xiangqi positions and the same game/state/return pipeline.
- It supplements (does not replace) normal self-play.
- It directly addresses the Phase 1.1 objective: ensure value head sees non-zero supervision while baseline self-play remains weak.
