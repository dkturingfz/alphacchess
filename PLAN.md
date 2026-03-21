## Project Overview

Build a Xiangqi reinforcement learning system anchored on an OpenSpiel-compatible game/state interface.

Two goals:
1. A pure AlphaZero-like Xiangqi system.
2. A style-constrained RL extension that preserves a target player's stylistic corridor while improving strength.

## Global Rules

- Follow repository rules in `AGENTS.md`.
- Stay strictly within the current phase boundary.
- Do not implement later-phase features unless required by current-phase acceptance criteria.
- If validation fails, fix first, then continue.
- Core path must not depend on Pikafish.
- Pikafish is optional for warm-start data and benchmark only.

## Phase Order

1. Phase 0 — Foundation  
   See: `plans/phase0.md`

2. Phase 1 — Minimal AlphaZero Loop  
   See: `plans/phase1.md`

3. Phase 1b — Style Reference Model  
   See: `plans/phase1b.md`

4. Phase 2a — KL-Constrained Style RL  
   See: `plans/phase2a.md`

5. Phase 2b — Search-Level Style Guidance (Optional)  
   See: `plans/phase2b.md`

6. Phase 3 — Scale, Profile, Optimize, Benchmark  
   See: `plans/phase3.md`

## Execution Discipline

For any current task:
- read `AGENTS.md`
- read this `PLAN.md`
- read the active phase file under `plans/`
- complete only that phase's scope
- run validations before declaring completion
