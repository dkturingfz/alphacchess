# Phase 1b File Guide

## 目标

Phase 1b 的目标是训练并冻结风格参考策略 `pi_style`，用于后续 style-constrained RL 的风格走廊约束。

> 注意：Phase 1b 只做风格参考模型，不做 KL 约束强化学习本体。

## 当前状态说明（2026-03-21）

- 风格流水线（训练/评测/恢复）已在仓库中实现。
- 当前 demo 规模 style checkpoint 质量不足，按协议仍不可直接用于后续 style-constrained RL 主线推进。
- 现阶段优先级是纯 RL 主线（含 profiling、benchmark 准备与更严格 readiness gating），风格工作暂缓。

---

## 关键脚本

### `scripts/train_style_reference.py`

用途：训练风格参考策略并输出**冻结 checkpoint**。

支持两条路径：

1. 直接目标棋手训练（仅 `--target-dataset`）
2. 通用预训练 -> 个人微调（同时提供 `--generic-pretrain-dataset`）

常用参数：

- `--target-dataset`：目标棋手局面/对局 JSONL
- `--generic-pretrain-dataset`：可选，通用预训练数据 JSONL
- `--augment-lr-mirror`：可选，启用左右镜像增强（v1 允许的轻量增强）
- `--out-checkpoint`：输出冻结 checkpoint
- `--out-report`：训练报告 JSON

---

### `scripts/evaluate_style.py`

用途：按 `configs/style_eval_v1.yaml` 对风格模型做独立评测（与棋力 benchmark 分离）。

输出：

- global top-1 / top-3
- opening top-1 / top-3
- middlegame top-1 / top-3
- endgame top-1 / top-3

并给出质量分区：

- `unusable`
- `gray`
- `usable`
- `preferred`

---

### `scripts/run_style_recovery.py`

用途：当评测结果处于灰区（`25% <= top-1 < 35%`）时，按协议执行恢复序列。

恢复顺序：

1. 先验证评测/数据一致性
2. 强化“通用预训练 -> 个人微调”
3. 启用左右镜像增强
4. 若仍灰区，记录“考虑增大模型容量”的后续 TODO

输出：`recovery_report.json`（包含每一步结果）。

---

## 阈值解释（来自 `configs/style_eval_v1.yaml`）

- `top-1 < 25%` => **unusable**（不可用）
- `25% <= top-1 < 35%` => **gray**（灰区，必须恢复）
- `top-1 >= 35%` => **usable**（可进入 Phase 2a）
- `top-1 >= 40%` => **preferred**（优选风格参考）

---

## 数据格式（JSONL）

每行支持两种结构之一：

1. 局面样本：

```json
{"fen":"...","move_iccs":"a3a4","ply":21,"source":"target_player"}
```

2. 对局记录（脚本会展开为逐 ply 局面）：

```json
{"initial_fen":"...","moves_iccs":["a3a4","a6a5"],"game_id":"g001"}
```

---

## Demo 数据说明

仓库内置 `data/style_demo/` 仅用于流水线验证，不代表真实目标棋手规模数据结论。

当真实目标棋手数据接入时，无需修改主流程，只需替换输入数据集。
