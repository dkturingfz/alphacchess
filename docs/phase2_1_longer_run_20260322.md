# Phase 2.1 Longer Pure-RL Trend Run (2026-03-22)

## Run command
```bash
python scripts/train_selfplay.py --iterations 4 --games-per-iter 24 --max-moves 80 --terminal-enrichment-games 6 --terminal-enrichment-max-moves 6 --epochs 2 --batch-size 128 --quick-eval-games 12 --checkpoint-eval-games 12 --checkpoint-eval-max-moves 100 --seed 20260322 --out-dir artifacts/phase2_1_longer_run
```

## Replay-quality trend (per iteration)
| iter | total_games | natural_terminations | step_cap_truncations | value_mean | value_pos | value_zero | value_neg | value_non_zero_fraction |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 30 | 18 | 12 | 0.007798 | 360 | 960 | 347 | 0.424115 |
| 1 | 30 | 13 | 17 | 0.004082 | 181 | 1360 | 174 | 0.206997 |
| 2 | 30 | 9 | 21 | 0.003205 | 99 | 1680 | 93 | 0.102564 |
| 3 | 30 | 9 | 21 | 0.003786 | 88 | 1680 | 81 | 0.091401 |

## Checkpoint-vs-previous trend
| iter | games | candidate_wins | baseline_wins | draws | candidate_score |
|---:|---:|---:|---:|---:|---:|
| 1 | 12 | 11 | 1 | 0 | 0.916667 |
| 2 | 12 | 4 | 7 | 1 | 0.375000 |
| 3 | 12 | 7 | 4 | 1 | 0.625000 |

## Optional long-horizon checkpoint check (final vs iter_000)
```json
{
  "metadata": {
    "action_encoding_version": "v1_8100_from_to",
    "observation_encoding_version": "v1_15planes",
    "dataset_schema_version": "v1",
    "rules_version": "v1_python_rules",
    "evaluation_schema_version": "phase1_eval_v1"
  },
  "evaluation_type": "checkpoint_vs_checkpoint",
  "candidate_checkpoint": "artifacts/phase2_1_longer_run/checkpoints/iter_003.json",
  "baseline_checkpoint": "artifacts/phase2_1_longer_run/checkpoints/iter_000.json",
  "candidate_checkpoint_metadata": {
    "action_encoding_version": "v1_8100_from_to",
    "observation_encoding_version": "v1_15planes",
    "dataset_schema_version": "v1",
    "rules_version": "v1_python_rules",
    "checkpoint_schema_version": "phase1_checkpoint_v1",
    "iteration": "3"
  },
  "baseline_checkpoint_metadata": {
    "action_encoding_version": "v1_8100_from_to",
    "observation_encoding_version": "v1_15planes",
    "dataset_schema_version": "v1",
    "rules_version": "v1_python_rules",
    "checkpoint_schema_version": "phase1_checkpoint_v1",
    "iteration": "0"
  },
  "games": 16,
  "candidate_wins": 13,
  "baseline_wins": 3,
  "draws": 0,
  "candidate_score": 0.8125
}
```

## Extended summary readiness output
```json
{
  "aggregate": {
    "iterations": 4,
    "total_games": 120,
    "min_value_non_zero_fraction": 0.0914007571660357,
    "max_value_non_zero_fraction": 0.4241151769646071,
    "avg_value_non_zero_fraction": 0.20626928031071257,
    "max_step_cap_truncation_rate": 0.7,
    "avg_step_cap_truncation_rate": 0.5916666666666666,
    "iterations_with_natural_terminations": 4,
    "iterations_with_checkpoint_eval_vs_previous": 3
  },
  "readiness": {
    "replay_quality_healthy": true,
    "non_zero_value_supervision_present": true,
    "checkpoint_progress_visible": true,
    "readiness_grade": "caution",
    "checks": {
      "non_zero_value_supervision": {
        "value": 0.0914007571660357,
        "status": "pass",
        "pass_threshold": 0.02,
        "caution_threshold": 0.01
      },
      "truncation_control": {
        "value": 0.7,
        "status": "caution",
        "pass_threshold": 0.6,
        "caution_threshold": 0.75
      },
      "natural_termination_visibility": {
        "value": 1.0,
        "status": "pass",
        "pass_threshold": 0.9,
        "caution_threshold": 0.75
      },
      "checkpoint_progress_visibility": {
        "value": 0.75,
        "status": "pass",
        "pass_threshold": 0.75,
        "caution_threshold": 0.5
      },
      "sufficient_iterations": {
        "value": 4,
        "status": "pass",
        "pass_threshold": 3,
        "caution_threshold": 2
      }
    },
    "thresholds": {
      "min_non_zero_value_fraction": 0.02,
      "caution_non_zero_value_fraction": 0.01,
      "max_truncation_rate": 0.6,
      "caution_truncation_rate": 0.75,
      "min_natural_termination_ratio": 0.9,
      "caution_natural_termination_ratio": 0.75,
      "min_checkpoint_eval_ratio": 0.75,
      "caution_checkpoint_eval_ratio": 0.5,
      "min_iterations": 3
    },
    "ready_for_next_stage": false
  }
}
```

## Artifacts
- artifacts/phase2_1_longer_run_summary/train_summary_stdout.json
- artifacts/phase2_1_longer_run_summary/train_summary.json
- artifacts/phase2_1_longer_run_summary/replay_stats_trend_stdout.json
- artifacts/phase2_1_longer_run_summary/replay_stats_trend.json
- artifacts/phase2_1_longer_run_summary/checkpoint_vs_previous_trend_stdout.json
- artifacts/phase2_1_longer_run_summary/checkpoint_vs_previous_trend.json
- artifacts/phase2_1_longer_run_summary/checkpoint_final_vs_iter000_stdout.json
- artifacts/phase2_1_longer_run_summary/checkpoint_final_vs_iter000.json
- artifacts/phase2_1_longer_run_summary/extended_summary_stdout.json
- artifacts/phase2_1_longer_run_summary/extended_summary.json