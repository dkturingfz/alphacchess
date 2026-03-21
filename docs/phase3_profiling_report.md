# Phase 3 Profiling Report (Sample Run)

Generated from `scripts/profile_rules.py` on 2026-03-21.

## Hotspot ranking
1. selfplay_loop: 16.2277s
2. checkpoint_eval: 3.7050s
3. apply_action: 1.1289s
4. legal_actions: 0.3635s
5. replay_serialization: 0.1520s
6. clone: 0.0006s

## Interpretation

- This run is a deterministic small-scale profile for ranking hotspots in the current Python mainline.
- It is suitable for deciding whether optimization work is justified, but not for publishing throughput claims.
- Current recommendation: keep architecture stable and prioritize benchmark protocol readiness; revisit optimization only if repeated profiles show persistent same bottlenecks.
