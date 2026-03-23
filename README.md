# AlphaCChess

基于 OpenSpiel-compatible Game/State 接口的中国象棋强化学习项目。

## 当前状态（2026-03-22）

当前仓库状态与优先级：

- ✅ Phase 0 完成（规则核心、编码、规范化、基础验证）
- ✅ Phase 1 完成（最小 AlphaZero-like 闭环）
- ✅ Phase 1.1 完成（self-play hardening + 非零 value 监督可见性）
- ✅ Phase 2 完成（纯 RL 放大与 checkpoint 进度评测）
- ✅ Phase 2.1 完成（扩展运行与趋势汇总）
- 🟡 Phase 3 已实现首版（profiling + benchmark preparation）
- ⏸️ Phase 4/5/6（风格相关）保留在仓库中，但当前延后，不是下一步主线

> 当前主线优先级是：纯 RL readiness gating、profiling、benchmark 准备；不是风格约束算法推进。

## 关键边界

- 纯 RL 主路径必须独立于 Pikafish。
- Pikafish 仅作为可选 benchmark/teacher/warm-start 工具，不是训练核心依赖。
- 当前 benchmark 输出侧重“协议与元数据可复现性”，不应被解读为最终强棋力结论。

## Phase 顺序（以 `PLAN.md` 为准）

1. Phase 0 — Foundation (`plans/phase0.md`)
2. Phase 1 — Minimal AlphaZero Loop (`plans/phase1.md`)
3. Phase 1.1 — Self-play Hardening / Non-zero Value Supervision (`plans/phase1_1.md`)
4. Phase 2 — Pure RL Scale-Up (`plans/phase2_pure_rl.md`)
5. Phase 2.1 — Extended Pure RL Run (`plans/phase2_1_extended_run.md`)
6. Phase 3 — Profiling + Benchmark Preparation (`plans/phase3.md`)
7. Phase 4 — Style Reference Model (`plans/phase4_style_reference.md`)
8. Phase 5 — KL-Constrained Style RL (`plans/phase5_kl_style_rl.md`)
9. Phase 6 — Search-Level Style Guidance (Optional) (`plans/phase6_search_style_guidance.md`)

## 常用文档

- 总计划：`PLAN.md`
- Phase 2 / 2.1 文件导览：`docs/phase2_file_guide.md`
- Phase 3 文件导览：`docs/phase3_file_guide.md`
- benchmark 协议：`docs/benchmark_protocol.md`
- style eval 协议：`docs/style_eval_protocol.md`
- style 流水线导览（当前延后）：`docs/phase1b_file_guide.md`

## 常用脚本

- 纯 RL 训练：`scripts/train_selfplay.py`
- 回放统计：`scripts/export_replay_stats.py`
- checkpoint 对比：`scripts/evaluate_checkpoints.py`
- 扩展运行汇总：`scripts/summarize_extended_run.py`
- profiling：`scripts/profile_rules.py`
- benchmark 协议评测/干跑：`scripts/evaluate_vs_pikafish.py`
- style 评测：`scripts/evaluate_style.py`

## 快速示例

```bash
python scripts/train_selfplay.py --iterations 3 --games-per-iter 24 --out-dir artifacts/phase2_smoke
python scripts/summarize_extended_run.py --train-summary artifacts/phase2_smoke/train_summary.json
python scripts/evaluate_vs_pikafish.py \
  --checkpoint artifacts/phase2_smoke/checkpoints/iter_002.json \
  --benchmark-config configs/benchmark_pikafish_v1.yaml \
  --dry-run
```



## 本地数据转换（仓库安全）

- PGNS/PGN-like -> FEN 位置抽取脚本：`scripts/build_test_positions_from_games.py`
- FEN 位置校验脚本：`scripts/validate_test_positions.py`

这两个脚本用于**本地**数据准备与检查。完整大规模转换应输出到本地/制品目录（artifact-only），不应将大体量生成数据提交到 git。
