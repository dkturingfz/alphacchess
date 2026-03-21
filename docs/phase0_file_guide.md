# Phase 0 File Guide (Hardening Close-out)

本文档面向开发者，解释 Phase 0 关键文件“为什么存在、怎么运行、输出代表什么”。

## 1) `scripts/validate_xiangqi_game.py`

### 目的

对 OpenSpiel-compatible Xiangqi 环境做结构化健康检查，重点确认：

- 固定动作空间 (`8100`) 与观测形状 (`15x10x9`)。
- 随机 rollout 在既定步数上限下是否可执行。
- rollout 到底是“自然终局”还是“触达步数上限截断”。

### 运行方式

```bash
python scripts/validate_xiangqi_game.py
```

### 输出字段（JSON）

- `num_distinct_actions`: 动作空间大小，应为 `8100`。
- `observation_shape`: 观测张量形状，应为 `[15, 10, 9]`。
- `rollout_count`: rollout 条数。
- `rollout_step_cap`: 每条 rollout 最大步数。
- `rollout_lengths`: 每条 rollout 的实际步数。
- `natural_terminations`: 自然终局条数。
- `step_cap_hits`: 因步数上限截断的条数。
- `terminal_reason_counts`: 终止原因计数（含 `max_steps`）。
- `average_rollout_length` / `min_rollout_length` / `max_rollout_length`。
- `average_legal_actions_per_position`: rollout 过程中平均合法着法数量。
- `repeated_state_rollouts`: 出现过重复局面的 rollout 条数（观测信号，不等同于和棋裁决）。
- `terminal_reason_samples`: 终止原因样本，便于快速人工检查。

### 通过标准（Phase 0）

- 基本结构字段正确（8100 / 15x10x9）。
- 脚本成功完成并能区分自然终局与步数截断。
- 输出不存在“长度都是上限但语义不明”的歧义。

---

## 2) `scripts/smoke_alphazero_entry.py`

### 目的

最小化验证 AlphaZero 入口调用链（状态->观测->合法动作->落子->returns），并明确“为什么停止”。

### 运行方式

```bash
python scripts/smoke_alphazero_entry.py
```

### 输出字段（JSON）

- `steps`: 实际执行步数。
- `step_limit`: 配置步数上限。
- `terminal`: 是否到达自然终局。
- `terminated_by`: 停止类别：
  - `natural_terminal`
  - `step_limit`
  - `no_legal_actions_guard`
  - `other_stop_condition`
- `terminal_reason`:
  - 自然终局时返回规则层原因（如 `black_general_captured`、`no_legal_moves`）
  - 非终局时返回 `none`
- `returns`: OpenSpiel 风格回报（终局时非零，非终局通常 `[0.0, 0.0]`）。
- `metadata`: 版本元数据（action/observation/dataset/rules 版本）。

### 通过标准（Phase 0）

- 脚本成功执行且无接口异常。
- 可以直接看出是自然终局还是步数限制结束。
- 版本元数据完整。

---

## 3) `tests/test_terminal_regressions.py`

### 目的

提供确定性终局回归用例，补强 Phase 0 对 terminal/returns 语义的覆盖。

### 覆盖点

- 将帅被吃后终局：
  - `is_terminal()` 为真
  - `legal_actions()` 为空
  - `returns()` 符号正确
  - `terminal_reason()` 可读
- 无合法着法终局（黑方行棋与红方行棋两个方向）：
  - side-to-move 失败方判定正确
  - 回报符号与胜负方一致

### 运行方式

```bash
pytest tests/test_terminal_regressions.py
```

### 通过标准（Phase 0）

所有回归样例通过，说明核心终局分支在当前实现下可复现且不歧义。

---

## 4) `alphacchess/xiangqi_game.py`（本次 close-out 相关新增语义）

### 新增/强化点

- 状态对象新增 `terminal_reason()`：
  - 非终局返回 `none`
  - 终局返回可读原因（当前实现包括 `black_general_captured`、`red_general_captured`、`no_legal_moves` 等）
- `clone()` 现在保留终局缓存字段，减少验证脚本读取时语义偏差。

### 备注（当前限制）

- 暂未实现长将/重复局面和棋规则裁决；`repeated_state_rollouts` 仅为观测统计。

---

## 5) `alphacchess/smoke.py`（本次 close-out 相关新增语义）

### 新增/强化点

`SmokeResult` 新增：

- `step_limit`
- `terminated_by`
- `terminal_reason`

以支持 CLI 输出对“停止原因”的显式解释。

---

## TODO（非阻塞，留在后续 Phase）

- 将重复局面检测与正式和棋规则衔接（而不仅是观测统计）。
- 细化 `terminal_reason` 枚举（例如将“被将死”与“其他无子可动”进一步区分）。
