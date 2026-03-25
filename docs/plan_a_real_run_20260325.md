# Plan A real execution note (2026-03-25)

This note records completion of the real Plan A route sweep using the existing executor:

- Command: `python scripts/plan_a_route_sweep.py --seed 20260325`
- Artifact root: `artifacts/local_plan_a_route_sweep_20260325_084905`
- Machine-local report: `artifacts/local_plan_a_route_sweep_20260325_084905/plan_a_route_sweep_report.json`

## Constraints respected

- Frozen benchmark_start sanity protocol was unchanged:
  - `start_fens_file = data/benchmark_positions/samples/benchmark_start_fens_sample.txt`
  - `max_start_positions = 8`
  - `games_per_start = 4`
  - `max_moves = 60`
  - `seeds = 17,29,41,53`
- No style path enabled.
- No external engine enabled.
- This is exploratory internal sanity evidence only, not a formal benchmark claim.

## Outcome snapshot

- Phase A routes executed: 4/4
- Phase B selected candidates: `route_2_eval_denoise`, `route_1_endgame_density`
- Phase B focus route: `route_1_endgame_density`
- Total runs executed: 8 (minimum run budget satisfied)
- Directionality repair success flag: `false`

## Follow-up intent

- Keep artifacts local-only and iterate pure-RL training stabilization before any formal internal benchmark preparation.
