# Xiangqi RL：基于 OpenSpiel 的中国象棋强化学习与风格约束系统

## 项目简介


## 当前开发状态（截至 2026-03-21）

仓库已不再是“仅 Phase 0”。当前实现覆盖：

- **Phase 0**：规则核心、编码契约、规范化与冒烟入口
- **Phase 1**：最小 AlphaZero-like 自对弈/训练/随机基线评测闭环
- **Phase 1.1**：回放与 value 监督质量加固
- **Phase 1b（本次新增）**：风格参考模型训练、风格评测、灰区恢复流程与冻结 checkpoint 输出

如需快速上手 Phase 1b，请先阅读：`docs/phase1b_file_guide.md`。

---

本项目旨在构建一个**中国象棋强化学习系统**，核心分为两条线：

1. **主线：AlphaZero/AlphaGo-like 中国象棋系统**
   - 使用 OpenSpiel-compatible 的游戏接口
   - 通过自我对弈（self-play）进行训练
   - 不依赖外部引擎即可独立完成训练闭环

2. **扩展线：风格约束强化学习（Style-Constrained RL）**
   - 从目标棋手的历史棋谱中学习其个人风格
   - 训练一个冻结的风格参考模型 `π_style`
   - 在自我对弈强化学习中，通过 KL 约束或搜索先验引导，让模型在“风格走廊内”追求更高棋力

简单说：

> 这个项目既想做一个**会变强**的中国象棋 AI，  
> 也想做一个**带有指定棋手风格**的中国象棋 AI。

---

## 设计目标

### 核心目标

- 纯 Python 实现中国象棋规则核心
- 对齐 OpenSpiel 风格的 Game/State 抽象
- 建立最小 AlphaZero-like 训练闭环
- 后续如有性能瓶颈，再局部迁移到 C++/pybind11

### 扩展目标

- 训练个人风格参考模型
- 支持 KL 风格约束强化学习
- 支持搜索层风格引导（可选）
- 支持与 Pikafish 做强度 benchmark

---

## 为什么不直接依赖 Pikafish

Pikafish 是一个很强的中国象棋引擎，但在本项目中的角色始终是：

- 可选热启动数据来源
- 可选 teacher / 分析参考
- benchmark 对手

它**不是主训练路径的核心依赖**。

本项目主线必须始终满足：

> **没有 Pikafish，也能完成规则、训练、自我对弈和评测。**

这样才能保证系统是自己的，而不是“围绕外部强引擎搭壳”。

---

## 项目阶段总览

项目按 Phase 推进：

### Phase 0：地基

实现：

- 纯 Python Xiangqi 规则核心
- OpenSpiel-compatible 接口
- FEN / ICCS / 棋谱规范化
- 最小 AlphaZero 冒烟调用

### Phase 1：最小 AlphaZero 闭环

实现：

- self-play
- replay buffer
- train
- evaluate vs random

### Phase 1b：风格参考模型

实现：

- 目标棋手风格学习
- 风格评测
- 灰区恢复机制

### Phase 2a：KL 风格约束强化

实现：

- `L = L_base + β * KL(πθ || πstyle)`

### Phase 2b：MCTS 风格引导（可选）

实现：

- 搜索先验混合

### Phase 3：放大训练、profiling、优化、benchmark

实现：

- 更大规模训练
- profiling
- 必要时热路径加速
- Pikafish benchmark

### Phase 0 Close-out 状态（历史阶段，已完成）

当前 Phase 0 已经补强并可复现以下验证语义：

- `scripts/validate_xiangqi_game.py` 会输出：
  - `num_distinct_actions=8100`
  - `observation_shape=(15,10,9)`
  - rollout 的数量/步数上限/每条长度
  - `natural_terminations` 与 `step_cap_hits`（区分自然终局 vs 截断）
  - `terminal_reason_counts`（例如 `no_legal_moves`、`black_general_captured`、`max_steps`）
  - 平均/最小/最大 rollout 长度
  - 平均 legal action 数、重复状态观测统计与终局原因样本
- `scripts/smoke_alphazero_entry.py` 会明确给出：
  - `steps`、`step_limit`
  - `terminal`
  - `terminated_by`（`natural_terminal` / `step_limit` / 其他显式停止原因）
  - `terminal_reason`（自然终局时可读；非终局时为 `none`）
  - `returns` 与版本元数据
- 终局回归测试新增了确定性局面，覆盖：
  - 将帅被吃导致终局
  - 无合法着法终局（红方/黑方行棋两侧）
  - 终局时 `legal_actions()` 为空且 `returns()` 符号正确

当前已知限制（Phase 0 范围内记录，不扩 scope）：

- 和棋细则（长将/重复局面裁决）尚未实现为正式规则终局。
- `terminal_reason` 当前聚焦于已实现分支（将帅被吃、无合法着法等）；更多细分原因留待后续 phase。

### Phase 1 回放质量可见性（hardening close-out）

Phase 1 现已显式记录并导出每盘自对弈的结束语义（不是只看 sample 数）：

- 是否自然终局（`ended_naturally`）
- 是否触发步数上限截断（`hit_step_cap`）
- 终局原因（`terminal_reason`，如 `black_general_captured` / `no_legal_moves` / `max_moves_truncation`）
- 对局结果标签（`win` / `loss` / `draw` / `truncated_draw`，以红方视角记录）

`scripts/export_replay_stats.py` 现在会额外输出：

- `num_games`
- `natural_terminations`
- `step_cap_truncations`
- `result_counts`
- `value_non_zero_fraction`
- `value_positive_count` / `value_zero_count` / `value_negative_count`

因此当 `value_mean=min=max=0` 时，可以直接区分两种情况：

1. **正确但监督退化**：回放几乎全是 `truncated_draw`，则 value=0 主要由截断设计导致。  
2. **实现 bug**：如果有自然胜负终局，但 value 分布仍全零，则应优先排查 returns 传播链路（当前已加回归测试保护）。

### Phase 1.1：value 监督去退化（terminal-enrichment + 统计增强）

为解决“自对弈几乎都在 `max_moves` 截断，导致 value target 接近全 0”的问题，Phase 1.1 做了一个**小而明确**的改进：

1. 自对弈动作选择加入“立即终局优先”（若一步可直接获胜，优先选择）。
2. 在不替代主路径的前提下，加入可控的 `terminal_enrichment` 对局源：
   - 使用固定、合法、可复现的近终局 FEN 起点；
   - 只用于补充少量明确胜负标签，保证 value head 可见非零监督；
   - 默认与常规 self-play 同时写入同一 replay，但在 schema 中显式区分来源。
3. replay 统计新增来源维度：
   - `game_source_counts`
   - `value_counts_by_source`

因此可以明确回答：
- 非零 value supervision 是否存在；
- 它主要来自自然终局 self-play 还是来自受控 terminal-enrichment；
- 是否仍被截断局主导。

---

## 仓库结构说明

下面对仓库主要目录与文件做详细解释。

---

# 根目录文件

## `AGENTS.md`

这是**长期规则文件**。

作用：

- 定义项目的核心原则
- 限定架构边界
- 规定 benchmark 和 style eval 的纪律

你应该把它放在仓库根目录。

---

## `PLAN.md`

这是项目的**总览型计划文件**。

作用：

- 描述项目整体目标
- 给出所有 Phase 的顺序
- 指向 `plans/phase*.md` 的详细说明

建议也放在根目录。

---

# `plans/`

这个目录存放分阶段的详细任务定义。

## `plans/phase0.md`

定义 Phase 0：

- 中国象棋规则核心
- OpenSpiel-compatible 设计
- FEN / ICCS / 数据规范化
- AlphaZero 冒烟测试

## `plans/phase1.md`

定义 Phase 1：

- 最小 AlphaZero 闭环
- self-play
- 训练
- 对随机策略评测

## `plans/phase1b.md`

定义风格参考模型阶段：

- 风格模型训练
- top-1 / top-3 评测
- opening / middlegame / endgame 分段统计
- 灰区恢复机制

## `plans/phase2a.md`

定义 KL 风格约束强化阶段：

- β 粗搜
- β 细搜
- strength/style tradeoff

## `plans/phase2b.md`

定义搜索层风格引导阶段（可选）：

- α 调参
- prior mixing

## `plans/phase3.md`

定义放大训练与 benchmark 阶段：

- profiling
- C++ 热路径优化（可选）
- Pikafish benchmark
- 风格评测与棋力评测并行

---

# `configs/`

存放所有版本化配置文件。

## `configs/benchmark_pikafish_v1.yaml`

定义棋力 benchmark 协议的第一版配置。

### 字段解释

#### `engine_name`

引擎身份名。  
当前值：

- `pikafish`

#### `engine_protocol`

与引擎交互时使用的协议。  
当前值：

- `ucci`

#### `search_limit_type`

定义搜索终止方式。  
v1 固定为：

- `depth`

第一版 benchmark 只允许单一终止模式，不允许混用深度和时间控制。

#### `depth`

当 `search_limit_type=depth` 时使用的搜索深度。  
例如：

- `depth: 5`

#### `games_per_side`

每个随机种子、每个执色的局数。  
例如：

- `games_per_side: 20`

如果 `swap_colors=true`，则表示：

- 执红 20 局
- 执黑 20 局

#### `evaluation_seeds`

用于 milestone benchmark 的种子集合。  
例如：

```yaml
evaluation_seeds:
  - 42
  - 137
```

表示一次完整 benchmark 要分别在两个 seed 下独立跑完。

#### `swap_colors`

是否执行执色平衡。  
通常为：

- `true`

#### `resign_enabled`

是否允许自动认输。  
v1 固定：

- `false`

#### `draw_adjudication_enabled`

是否允许自动和棋裁定。  
v1 固定：

- `false`

#### `max_moves`

单局最大步数。  
例如：

- `300`

#### `max_moves_result`

如果走满 `max_moves` 后尚未自然终局，则如何处理结果。  
v1 固定：

- `draw`

---

## `configs/style_eval_v1.yaml`

定义风格评测协议的第一版配置。

### 字段解释

#### `style_eval_name`

风格评测配置名。  
例如：

- `style_eval_v1`

#### `phase_split`

定义阶段切分规则。

##### `opening`

- `ply_start: 1`
- `ply_end: 20`

##### `middlegame`

- `ply_start: 21`
- `ply_end: 60`

##### `endgame`

- `ply_start: 61`
- `ply_end: null`

#### `metrics`

定义要输出哪些风格指标。  
v1 固定：

- `top1`
- `top3`

#### `top1_thresholds`

定义 `Phase 1b` 风格参考模型的质量阈值。

##### `unusable_lt`

全局 top-1 小于这个值时，不可用。  
默认：

- `25.0`

##### `gray_zone_gte` / `gray_zone_lt`

灰区范围。  
默认：

- `25.0 <= top-1 < 35.0`

##### `usable_gte`

达到此值即可进入 KL 风格约束训练。  
默认：

- `35.0`

##### `preferred_gte`

达到此值说明风格模型质量较好。  
默认：

- `40.0`

#### `gray_zone_recovery`

定义灰区恢复机制开关。

##### `verify_data_pipeline`

先检查数据与评测管线是否有误。

##### `strengthen_generic_pretrain_then_personal_finetune`

先加强通用预训练，再做个人微调。

##### `enable_left_right_mirror_augmentation`

允许左右镜像增强。

##### `allow_increase_model_capacity_after_other_steps`

只有前面手段不够时，才允许增大模型容量。

---

## `configs/local_env.yaml`

这是本地环境配置，不应进入 Git。

作用：

- 记录机器相关路径，例如 Pikafish 路径

示例：

```yaml
pikafish_path: /absolute/path/to/pikafish
```

你也可以不用这个文件，改用环境变量：

```bash
export PIKAFISH_PATH=/absolute/path/to/pikafish
```

---

# `docs/`

## `docs/benchmark_protocol.md`

棋力 benchmark 协议文档。

它规定：

- benchmark 配置语义
- benchmark 可比性规则
- `engine_version` 的意义
- `max_moves_result` 的意义
- benchmark 脚本的职责边界

---

## `docs/style_eval_protocol.md`

风格评测协议文档。

它规定：

- top-1 / top-3 的定义
- opening / middlegame / endgame 的切分
- 风格模型的阈值分类
- 灰区恢复流程

---

## `docs/data_source_scouting.md`

Phase 0 产出的数据源调研文档。

作用：

- 摸底公开棋谱来源
- 记录格式
- 记录规模
- 判断哪些来源适合通用预训练，哪些适合个人风格微调

---

# `xiangqi/`

这一层是**中国象棋规则与数据核心**。

## `xiangqi/game.py`

定义 XiangqiGame。

作用：

- 提供 OpenSpiel-compatible 的游戏层定义
- 定义动作空间大小
- 定义 observation shape

## `xiangqi/state.py`

定义 XiangqiState。

作用：

- 存储局面状态
- 生成合法着法
- 执行走子
- 判断终局
- 生成 observation tensor

## `xiangqi/moves.py`

放动作编码与走法辅助逻辑。

典型内容：

- 8100 from-to 编码映射
- move id 与内部走法对象互转

## `xiangqi/notation.py`

处理记谱与局面格式。

典型支持：

- FEN
- ICCS
- 至少一种 PGN-like / 文本格式

## `xiangqi/dataset_builder.py`

负责把原始对局或规范化棋谱转成模型训练或风格评测可读的数据格式。

---

# `rl/`

这一层是主线强化学习核心。

## `rl/model.py`

定义 `PolicyValueNet`。

要求：

- 输入与 observation tensor 一致
- 输出 policy 维度 = 8100
- 输出 value = scalar

## `rl/selfplay.py`

负责自我对弈样本生成。

## `rl/trainer.py`

负责训练主线 RL 模型。

## `rl/replay_buffer.py`

负责 replay 数据读写、缓存和版本管理。

## `rl/evaluator.py`

负责基础对局评测，例如：

- vs random
- 后续可调用 benchmark 层

---

# `style/`

这一层是风格建模与风格约束强化的核心。

## `style/style_model.py`

定义风格参考模型结构。

## `style/style_trainer.py`

负责训练目标棋手风格模型。

## `style/style_metrics.py`

计算 top-1 / top-3 和分阶段风格指标。

## `style/style_recovery.py`

实现灰区恢复逻辑。

---

# `engines/`

## `engines/pikafish_adapter.py`

负责与 Pikafish 通信。

职责：

- 启动子进程
- 发送 UCCI 命令
- 请求 bestmove
- 配合 benchmark 脚本进行对局

注意：
它是**外部工具层**，不是主线强化学习依赖。

---

# `scripts/`

这个目录是实际运行入口。

## `scripts/normalize_games.py`

把原始棋谱规范化。

## `scripts/validate_xiangqi_game.py`

验证规则实现是否正确。

## `scripts/smoke_alphazero_entry.py`

最小 AlphaZero 冒烟调用。

## `scripts/train_selfplay.py`

主线自我对弈 + 训练入口。

## `scripts/evaluate_vs_random.py`

对随机策略评测。

## `scripts/export_replay_stats.py`

导出 replay 数据统计。

## `scripts/generate_pikafish_data.py`

可选，用 Pikafish 生成热启动数据。

## `scripts/train_style_reference.py`

训练风格参考模型。

## `scripts/evaluate_style.py`

风格评测入口。

## `scripts/run_style_recovery.py`

灰区恢复执行入口。

## `scripts/train_style_constrained_rl.py`

KL 风格约束强化学习入口。

## `scripts/evaluate_vs_pikafish.py`

棋力 benchmark 入口。

## `scripts/benchmark_checkpoints.py`

批量 benchmark 多个 checkpoint。

## `scripts/profile_rules.py`

分析规则层热点函数，为是否做 C++ 优化提供依据。

---

# `data/`

用于存放数据与产物。

## `data/raw/`

原始数据：

- 原始棋谱
- 原始文本
- 未规范化导入数据

## `data/normalized/`

规范化后的对局数据。

## `data/replay/`

self-play 产生的 replay 数据。

## `data/style/`

风格建模所用的中间数据与评测输出。

## `data/checkpoints/`

模型权重和 checkpoint。

---

## 运行流程建议

### 第一步：完成 Phase 0

只做：

- 规则核心
- OpenSpiel-compatible 接口
- FEN / ICCS / 数据规范化
- 最小冒烟测试

### 第二步：进入 Phase 1

只做：

- self-play
- train
- replay
- vs random

### 第三步：做 Phase 1b

只做：

- 风格参考模型
- 风格评测
- 灰区恢复

### 第四步：Phase 2a

做 KL 风格约束强化。

### 第五步：Phase 2b（可选）

做搜索层风格引导。

### 第六步：Phase 3

做：

- profiling
- benchmark
- 可选热路径优化

---

## benchmark 与 style eval 的区别

很多人容易混淆，这里特别说明：

### benchmark（棋力评测）

关注：

- 胜率
- 胜平负
- 对 Pikafish 的表现

脚本：

- `evaluate_vs_pikafish.py`

配置：

- `benchmark_pikafish_v1.yaml`

---

### style eval（风格评测）

关注：

- top-1
- top-3
- opening / middlegame / endgame 风格吻合率

脚本：

- `evaluate_style.py`

配置：

- `style_eval_v1.yaml`

两者必须分离。

---

## 这个项目最重要的设计哲学

### 1. 主线必须独立

Pikafish 不能绑住主线。

### 2. benchmark 先求严谨，再求复杂

v1 benchmark 协议故意克制：

- 单一搜索终止模式
- 无默认认输
- 无默认和棋裁定
- 达到最大步数按和棋

### 3. 风格先做可执行基线

第一版风格评测只要求：

- top-1
- top-3
- 分阶段统计

### 4. 先正确，再优化

先把：

- 规则
- 自我对弈
- 训练
- 风格约束
  做对，再决定是否做 C++ 优化。

---

## 最后

如果你按本 README 的结构搭建仓库，再配合：

- `AGENTS.md`
- `PLAN.md`
- `plans/phase*.md`
- 分阶段提示词


# AlphaCChess (Phase 0)

Pure-Python Xiangqi foundation with OpenSpiel-compatible `XiangqiGame`/`XiangqiState` API style.

## Phase 0 CLI

- `scripts/normalize_games.py`
- `scripts/validate_xiangqi_game.py`
- `scripts/smoke_alphazero_entry.py`

## Quickstart

```bash
python -m pytest -q
python scripts/validate_xiangqi_game.py
python scripts/smoke_alphazero_entry.py
```

---

## Phase Status Update (Phase 0 + Phase 1)

- **Phase 0** foundation is in place (Python Xiangqi rules core, OpenSpiel-compatible Game/State contract, validation/smoke path).
- **Phase 1** minimal AlphaZero-like loop is now in place:
  - self-play
  - replay export/load with version validation
  - training + checkpointing
  - reload + evaluation vs random baseline

### Phase 1 scripts

- `scripts/train_selfplay.py`
- `scripts/evaluate_vs_random.py`
- `scripts/export_replay_stats.py`

See `docs/phase1_file_guide.md` for usage and passing criteria.
