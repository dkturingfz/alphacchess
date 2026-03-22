# Benchmark Protocol

## 目的

本文档定义本项目中**棋力评测（strength benchmark）**的统一协议，目标是：

1. 消除评测语义歧义
2. 保证跨时间、跨实验、跨 checkpoint 的可复现性
3. 明确哪些 benchmark 结果可以直接比较，哪些不可以

本协议只适用于**棋力评测**，不适用于风格评测。  
风格评测请见 `docs/style_eval_protocol.md`。

## 当前状态说明（2026-03-22）

仓库已实现 benchmark 协议与 dry-run 准备链路（配置版本化、配置哈希记录、结果元数据落盘）。  
但**强 benchmark 结论**应仅在更严格 readiness 检查（含纯 RL 长窗口稳定性）被持续满足后再做正式宣称。

---

## 适用范围

本协议适用于：

- `scripts/evaluate_vs_pikafish.py`
- `scripts/benchmark_checkpoints.py`
- 所有用于 milestone / phase trigger 的棋力评测
- 所有需要写入 benchmark 结果文件的对局评测

---

## 核心原则

### 1. benchmark 配置必须版本化
棋力评测必须使用固定、版本化的 benchmark 配置文件，例如：

- `configs/benchmark_pikafish_v1.yaml`

同一个 benchmark 版本内，不允许随意修改核心语义参数。  
如果核心参数变化，必须新建版本，例如：

- `benchmark_pikafish_v2.yaml`

---

### 2. benchmark 配置只描述“评测语义”
版本化 benchmark 配置文件只能描述：

- 使用哪个引擎身份
- 搜索终止方式
- 搜索深度或时间控制
- 局数定义
- 种子集合
- 执色切换规则
- 认输/和棋裁定开关
- 最大步数与最大步数后的结果

**不得**把机器相关字段写入版本化 benchmark 配置，例如：

- `engine_path`
- 本地绝对路径
- 用户名目录
- 临时目录

这些必须来自：
- 环境变量，例如 `PIKAFISH_PATH`
- 或 `configs/local_env.yaml`（不进入版本控制）

---

### 3. benchmark 结果只有在“双重一致”时才可比
两份棋力 benchmark 结果，只有在以下两项都相同时，才视为可直接横向比较：

1. `benchmark_config_identity`
   - 至少包括 benchmark 配置文件名与配置 hash
2. `engine_version`
   - 例如 Pikafish 的版本号或构建版本

如果引擎版本变化，即使 benchmark 配置没有变化，结果也**不能**直接横向比较，除非重新跑基线。

---

## benchmark 配置 v1

当前项目推荐的第一版 benchmark 配置为：

文件：
- `configs/benchmark_pikafish_v1.yaml`

建议内容：

```yaml
engine_name: pikafish
engine_protocol: ucci

search_limit_type: depth
depth: 5

games_per_side: 20
evaluation_seeds:
  - 42
  - 137

swap_colors: true

resign_enabled: false
draw_adjudication_enabled: false

max_moves: 300
max_moves_result: draw
```

---

## benchmark v1 字段解释

### `engine_name`
表示 benchmark 使用的引擎身份名。  
当前固定为：

- `pikafish`

这个字段用于结果记录和协议说明，不包含本地路径。

---

### `engine_protocol`
引擎通信协议。  
当前固定为：

- `ucci`

脚本通过该字段决定使用哪种命令交互逻辑。

---

### `search_limit_type`
定义搜索终止方式。  
一个 benchmark 版本中**必须只使用一种搜索终止模式**。

v1 固定为：

- `depth`

可选未来扩展：
- `movetime`

但如果切换到 `movetime`，必须新建 benchmark 版本，不能在 v1 中混用。

---

### `depth`
当 `search_limit_type=depth` 时生效。  
表示引擎每步搜索的固定深度。

v1 固定为：

- `depth: 5`

---

### `games_per_side`
定义每个 seed 下、每个执色的局数。

例如：

- `games_per_side: 20`
- `swap_colors: true`

表示：

对于每个 seed：
- 模型执红 20 局
- 模型执黑 20 局

总计：
- 每个 seed 共 40 局

如果有两个 seed：
- 总局数 = `20 × 2 × 2 = 80`

---

### `evaluation_seeds`
定义一次完整 milestone benchmark 所需的随机种子集合。

例如：

```yaml
evaluation_seeds:
  - 42
  - 137
```

其语义不是“任选一个 seed”，而是：

> 一次完整 benchmark 必须在这组 seed 上分别独立跑完，并分别记录结果。

milestone 判定时，默认要求：
- 所有 seed 子评测都满足门槛，才算整体通过

---

### `swap_colors`
是否执行执色平衡。

当为 `true` 时：
- 每个 seed 下都会同时跑“执红”和“执黑”的局数

v1 固定为：

- `true`

目的是减少先后手偏差。

---

### `resign_enabled`
是否启用自动认输。

v1 固定为：

- `false`

原因：
- 避免依赖引擎默认认输规则
- 避免因引擎版本变化导致隐式 benchmark 语义变化
- 保持协议简单、透明、可复现

---

### `draw_adjudication_enabled`
是否启用自动和棋裁定。

v1 固定为：

- `false`

原因：
- 避免依赖引擎或对弈框架默认和棋判定
- 保持第一版 benchmark 语义最小化

注意：
这不等于“永不判和”，因为项目仍然使用 `max_moves` 作为硬终止条件。

---

### `max_moves`
单局允许的最大步数上限。

v1 固定为：

- `300`

达到该值后，对局强制终止。

---

### `max_moves_result`
定义达到 `max_moves` 后的结果。

v1 固定为：

- `draw`

这意味着：

> 当一局棋走满 `max_moves` 而未自然终局，则该局按和棋计入统计。

这与 `draw_adjudication_enabled: false` 不冲突，因为：
- `draw_adjudication_enabled` 关闭的是基于评估/启发式的提前和棋裁定
- `max_moves_result` 定义的是达到硬上限后的结果

---

## 本地环境配置

### 不允许进入版本化 benchmark 文件的内容
以下内容必须来自本地环境，而不是 benchmark 配置文件：

- Pikafish 可执行文件路径
- 本机临时目录
- 用户目录路径
- 本机线程/资源偏好

推荐两种方式之一：

### 方式 A：环境变量
```bash
export PIKAFISH_PATH=/absolute/path/to/pikafish
```

### 方式 B：本地配置文件
`configs/local_env.yaml`（加入 `.gitignore`）

示例：

```yaml
pikafish_path: /absolute/path/to/pikafish
```

---

## 结果文件必须记录的元信息

每一份棋力 benchmark 结果，至少必须写入以下字段：

- `benchmark_config_name`
- `benchmark_config_hash`
- `engine_name`
- `engine_version`
- `checkpoint_id`
- `seed`

建议额外记录：
- `games_per_side`
- `total_games`
- `wins`
- `draws`
- `losses`
- `win_rate`
- `timestamp`

这些字段必须由脚本**自动写入**，不能依赖人工填写。

---

## 评测脚本职责边界

### `scripts/evaluate_vs_pikafish.py`
只负责：
- 模型 vs Pikafish 棋力对战
- 读取 benchmark 配置
- 读取本地引擎路径
- 执行对局
- 写入 benchmark 结果与元信息

它**不负责**：
- 风格评测
- 风格吻合率统计
- 目标棋手历史局面分析

风格相关评测必须使用独立脚本：
- `scripts/evaluate_style.py`

---

## milestone 评测规则

### 一次完整 milestone benchmark 的定义
对于一个 checkpoint：

1. 读取固定 benchmark 配置
2. 遍历其中所有 `evaluation_seeds`
3. 每个 seed 下跑完整执色平衡局数
4. 分别记录各 seed 的结果
5. 汇总整体结果

---

### 同一个 checkpoint 的双次独立评测
如果某阶段要求“两个独立评测都达标”，第一版协议定义为：

> 在同一个 benchmark 配置下，使用配置中列出的多个 seed 分别完成所有子评测，并要求每个 seed 子结果都达标。

这比“临时换 seed 重跑”更严格，也更不容易和版本化规则冲突。

---

## benchmark 版本升级规则

只有**核心 benchmark 语义字段**发生变化时，才允许升级 benchmark 版本。

例如以下变化必须升级版本：

- `search_limit_type`
- `depth`
- `games_per_side`
- `evaluation_seeds`
- `swap_colors`
- `resign_enabled`
- `draw_adjudication_enabled`
- `max_moves`
- `max_moves_result`

版本升级时，必须在本文档或附带变更说明中记录：
- 升级原因
- 与上一版的差异
- 旧结果是否仍可用于某些对比
- 是否需要重跑旧 baseline

---

## 推荐输出格式

评测结果可以用：
- JSON
- JSONL
- Parquet
- CSV（仅简单汇总）

但无论采用哪种格式，都必须包含：
- 配置身份
- 引擎身份
- checkpoint 身份
- seed 身份
- 对局结果统计

---

## 常见错误

### 错误 1：把本地路径写进 benchmark 配置
后果：
- 不同机器 config hash 不一致
- benchmark 结果不可比

---

### 错误 2：混用 depth 和 movetime
后果：
- 引擎行为不确定
- benchmark 语义模糊

---

### 错误 3：把风格评测塞进棋力 benchmark 脚本
后果：
- 脚本职责膨胀
- 结果难解释
- 后续维护困难

---

### 错误 4：Pikafish 版本变了还直接比较结果
后果：
- benchmark 不再可比
- 结论失真

---

## 第一版 benchmark 的设计哲学

v1 的 benchmark 协议故意采取“最小但严格”的设计：

- 单一搜索终止模式
- 无默认认输
- 无默认和棋裁定
- 明确最大步数行为
- 明确种子集合
- 明确局数定义
- 引擎路径与语义分离

目标不是“功能齐全”，而是：

> **先让 benchmark 结果可解释、可比较、可复现。**
