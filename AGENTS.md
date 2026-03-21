## Project Identity

This repository implements a Xiangqi (Chinese chess) reinforcement learning system anchored on an OpenSpiel-compatible game/state interface.

The long-term goal is:

1. Build a correct Xiangqi environment and AlphaZero-style self-play/training loop.
2. Add style-constrained reinforcement learning so the model can stay within a target player's stylistic corridor while maximizing strength.
3. Keep the architecture modular enough that the Python rules core can later be replaced by a faster implementation without changing upper-layer training code.

---

## Core Path

The core path of the project is:

OpenSpiel-compatible Xiangqi game/state -> self-play -> training -> evaluation

This core path must work **without** Pikafish.

Pikafish is optional and only serves as:
- warm-start data source
- teacher / reference engine
- benchmark opponent

It must never become a hard dependency for the main RL path.

---

## Architecture Rules

1. **OpenSpiel compatibility is the anchor.**
   - Do not invent a parallel custom environment abstraction unless it is a very thin wrapper over the same Game/State contract.
   - The environment layer should be designed so later OpenSpiel integration or formal registration is straightforward.

2. **Do not depend on `xiangqi.js` in the training/search core.**
   - UI/frontend concerns are separate.
   - The core Xiangqi rules engine must be implemented in Python first.

3. **Keep the core path independent of Pikafish.**
   - Pikafish is optional for Phase 0.
   - Pikafish must not block Phase 1 self-play/training.
   - Pikafish is mainly for warm-start data generation and benchmarking.

4. **Encoding v1 is fixed.**
   - Action encoding: `v1_8100_from_to`
   - Observation encoding: `v1_15planes`

5. **All artifacts must carry version metadata.**
   Every dataset / replay / checkpoint / evaluation output must include:
   - `action_encoding_version`
   - `observation_encoding_version`
   - `dataset_schema_version`
   - `rules_version`

6. **Optimize for correctness before speed in early phases.**
   - Phase 0 and Phase 1 prioritize correctness, compatibility, and testability.
   - Do not prematurely optimize.

7. **Before Phase 3, run profiling first.**
   - Only after profiling confirms hot spots may move generation / state update be rewritten in C++ / pybind11.
   - If such an optimization is done, upper-layer interfaces must remain stable.

8. **Every phase must include:**
   - runnable CLI entrypoints
   - automated tests
   - explicit acceptance criteria

9. **Do not silently expand scope.**
   - Stay strictly within the current phase boundary.
   - If a future-phase concern appears, leave a TODO and document it, but do not implement future-phase features unless absolutely required by current acceptance criteria.

---

## Style-Constrained RL Rules

10. The project must support a **style-constrained RL path** in addition to the pure AlphaZero-like path.

11. The style model is a **frozen reference policy**, not the main evolving policy.

12. Implement style-constrained RL in this order:
   1. loss-level KL regularization
   2. optional search-level prior mixing later

13. Search-level style guidance must remain optional and experimentally isolated from the core training path.

14. Style evaluation must be **phase-aware from the first implementation**:
   - opening
   - middlegame
   - endgame

15. The style reference model must pass minimum quality thresholds before being used in style-constrained RL.

16. If the style reference model falls into the gray zone (`25% <= top-1 < 35%`), do not proceed directly to style-constrained RL. Run the recovery plan first.

17. Beta search for KL-constrained RL must follow a structured plan:
   - coarse sweep first
   - fine sweep second
   - optional schedule experiments only after the baseline is stable

18. Large-scale training / benchmark progression requires **both**:
   - strength gate
   - style-retention gate

---

## Benchmark Rules

19. All milestone-triggering strength evaluations must use a fixed, versioned benchmark config file.

20. Benchmark configs must contain only benchmark semantics, not machine-specific paths.
   - Engine paths must come from local non-versioned config or environment variables.

21. The evaluation script must automatically record:
   - benchmark config name
   - benchmark config hash
   - engine name
   - engine version
   - checkpoint id
   - seed

22. Core benchmark parameters must not be modified within a benchmark version.
   Any change to core benchmark semantics requires creating a new versioned config file.

23. If multiple seeds are required for a milestone benchmark, they must be explicitly listed in the config file.

24. Benchmark configs must use exactly one search termination mode per version.

25. For benchmark v1:
   - automatic resign is disabled
   - automatic draw adjudication is disabled
   - if `max_moves` is reached, the game result is determined by `max_moves_result`
   - in v1, `max_moves_result=draw`

26. Benchmark results are directly comparable only when **both**:
   - benchmark config identity matches
   - engine version matches

---

## Data Rules

27. All normalized notation should converge to a canonical internal representation.

28. Support at least:
   - FEN
   - ICCS
   - one PGN-like or plain-text game format

29. Keep dataset schemas explicit and documented.
   Do not create ambiguous ad hoc dumps.

30. Public Xiangqi data source scouting must be documented early, but data sourcing must not block the main RL path.

---

## Testing Rules

31. Validation failures are stop-and-fix events.
   If a test or smoke check fails:
   - inspect the cause
   - fix the implementation
   - rerun validation
   - repeat until acceptance criteria are satisfied or a true external blocker is reached

32. Do not leave known broken code behind.

33. Before declaring a phase complete, run the full validation sequence end-to-end.

---

## Working Style for Codex

34. Work autonomously.
35. Prefer a robust fallback rather than pausing.
36. Only surface blockers that truly require human intervention.
37. If a blocker is unavoidable, document it precisely and still leave the repository in the best possible completed state short of that blocker.

---

## Current Default Versions

- `action_encoding_version: v1_8100_from_to`
- `observation_encoding_version: v1_15planes`
- `dataset_schema_version: v1`
- `rules_version: v1_python_rules`**
