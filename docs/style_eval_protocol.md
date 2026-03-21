# Style Evaluation Protocol

## 目的

本文档定义本项目中**风格评测（style evaluation）**的统一协议，目标是：

1. 衡量模型与目标棋手风格的相似度
2. 为 `Phase 1b` 的风格参考模型提供准入标准
3. 为 `Phase 2a / Phase 2b` 的风格约束强化学习提供可比较的风格保留指标
4. 保证风格评测在不同阶段、不同 checkpoint、不同实验中的可复现性

本文档只适用于**风格评测**，不适用于棋力 benchmark。  
棋力评测请见 `docs/benchmark_protocol.md`。

## 当前优先级说明（2026-03-21）

该协议当前仍然有效，并用于约束风格质量判定与灰区恢复流程。  
但当前活跃主线优先级是纯 RL 稳定化、profiling 与 benchmark 准备；风格相关 phase 处于延后状态。

---

## 核心原则

### 1. 风格评测与棋力评测必须分离
风格评测必须使用独立脚本和独立配置，不得与棋力 benchmark 混在一起。

推荐脚本：
- `scripts/evaluate_style.py`

风格评测不依赖外部引擎对战，而是依赖：
- 目标棋手历史对局
- 目标棋手历史局面
- 模型在这些局面上的策略分布输出

---

### 2. 第一版重点是“动作吻合”而不是“风格哲学解释”
风格是一个很宽泛的概念，但在工程上，第一版必须落到**可计算的具体指标**。

因此 v1 的风格评测核心指标是：
- top-1 move match
- top-3 move match

后续可以增加更高阶指标，但第一版必须先把基础指标做好。

---

### 3. 风格评测必须按阶段分段统计
仅看全局平均会掩盖很多问题。

例如：
- 一个模型可能开局风格很像目标棋手
- 但中残局已经明显漂移

因此从第一版开始，就必须分阶段统计：
- opening
- middlegame
- endgame

---

## 风格评测输入

风格评测依赖的数据通常来自：

1. 目标棋手历史对局
2. 从历史对局展开得到的逐步局面样本

每个样本至少需要：
- 局面（通常用 FEN 或内部表示）
- 该局面下目标棋手实际走的着法
- ply 信息（用于阶段切分）
- 可选元数据：
  - 对局 ID
  - 来源
  - 比赛日期
  - 对手信息

---

## style eval v1 配置

文件：
- `configs/style_eval_v1.yaml`

建议内容：

```yaml
style_eval_name: style_eval_v1

phase_split:
  opening:
    ply_start: 1
    ply_end: 20
  middlegame:
    ply_start: 21
    ply_end: 60
  endgame:
    ply_start: 61
    ply_end: null

metrics:
  - top1
  - top3

top1_thresholds:
  unusable_lt: 25.0
  gray_zone_gte: 25.0
  gray_zone_lt: 35.0
  usable_gte: 35.0
  preferred_gte: 40.0

gray_zone_recovery:
  verify_data_pipeline: true
  strengthen_generic_pretrain_then_personal_finetune: true
  enable_left_right_mirror_augmentation: true
  allow_increase_model_capacity_after_other_steps: true
```

---

## 配置字段解释

### `style_eval_name`
风格评测配置名。  
用于结果记录和结果可比性标识。

---

### `phase_split`
定义阶段切分规则。

第一版固定使用简单的 ply 区间：

#### opening
- `ply_start: 1`
- `ply_end: 20`

#### middlegame
- `ply_start: 21`
- `ply_end: 60`

#### endgame
- `ply_start: 61`
- `ply_end: null`

这不是唯一可能的划分方式，但第一版的目标是：
- 简单
- 一致
- 易复现

后续如果升级更复杂的阶段识别逻辑，必须作为新版本 style eval 协议处理。

---

### `metrics`
定义需要输出的风格指标。

v1 固定要求：
- `top1`
- `top3`

---

### `top1_thresholds`
定义 `Phase 1b` 中风格参考模型的准入标准。

#### `unusable_lt`
如果全局 top-1 小于这个值：
- 风格模型不可用
- 不允许进入风格约束强化学习

v1：
- `25.0`

#### `gray_zone_gte` / `gray_zone_lt`
定义灰区范围。

v1：
- `25.0 <= top-1 < 35.0`

#### `usable_gte`
达到此值即可认为风格模型可用于 `Phase 2a`

v1：
- `35.0`

#### `preferred_gte`
达到此值则认为风格参考模型质量较好，优先作为正式 `π_style`

v1：
- `40.0`

---

### `gray_zone_recovery`
定义灰区恢复策略是否启用。

这些字段本质上不是模型训练超参数，而是**流程控制开关**，用于提醒和约束：

当风格模型处于灰区时，必须优先按这个恢复顺序来做。

---

## 风格指标定义

### 1. Top-1 Match
定义：

> 在一个目标棋手历史局面上，模型预测概率最高的着法，是否恰好等于目标棋手实际走的着法。

记为：
- 命中 = 1
- 未命中 = 0

对全部样本平均后得到 top-1 match。

---

### 2. Top-3 Match
定义：

> 在一个目标棋手历史局面上，目标棋手实际着法是否出现在模型概率最高的前三个着法中。

top-3 比 top-1 更宽松，常用于衡量：
- 模型是否至少抓住了目标棋手的主要候选思路

---

## 分阶段指标

所有风格指标必须至少分为：

1. **全局**
2. **开局**
3. **中局**
4. **残局**

也就是说，第一版最少要输出：

- global top-1
- global top-3
- opening top-1
- opening top-3
- middlegame top-1
- middlegame top-3
- endgame top-1
- endgame top-3

---

## Phase 1b 准入逻辑

风格参考模型 `π_style` 的质量分为四类：

### A. 不可用
- `top-1 < 25%`

处理：
- 不允许进入 `Phase 2a`
- 优先检查数据、训练和评测实现问题

---

### B. 灰区
- `25% <= top-1 < 35%`

处理：
- 不允许直接进入 `Phase 2a`
- 必须进入恢复流程

---

### C. 可用
- `top-1 >= 35%`

处理：
- 可以进入 `Phase 2a`

---

### D. 优选
- `top-1 >= 40%`

处理：
- 优先作为正式冻结的 `π_style`

---

## 灰区恢复协议（Style Model Recovery Plan）

如果风格参考模型落入灰区，不允许直接拿去做 KL 约束训练。  
必须按以下顺序执行恢复：

### 第一步：检查数据与评测正确性
优先检查：

- 目标棋手数据是否正确
- 数据集是否混入其他棋手
- 记谱解析是否正确
- FEN 恢复是否正确
- 动作编码是否对齐
- top-1 / top-3 统计是否正确
- ply 分段是否正确

---

### 第二步：增强通用预训练 → 个人微调
如果数据量不足或局面覆盖窄，优先采用：

1. 通用棋谱预训练
2. 再对目标棋手棋谱微调

这比单纯在小样本上盲目加轮数更合理。

---

### 第三步：轻量数据增强
v1 只允许一种增强：

- 棋盘左右镜像

原因：
- 成本低
- 规则风险小
- 能缓解数据不足

不建议在 v1 引入过多复杂增强，以免破坏个人风格信号。

---

### 第四步：增大模型容量
只有在前三步后仍然落在灰区，才允许尝试：
- 增大模型宽度/深度
- 调整训练轮数
- 调整正则化
- 调整 batch size / learning rate

原则是：

> 先补数据与训练阶段结构，再补模型容量。

---

## 风格评测脚本职责边界

### `scripts/evaluate_style.py`
只负责：
- 读取目标棋手历史局面
- 运行模型策略推理
- 计算风格吻合指标
- 输出全局和分阶段统计

它不负责：
- 与 Pikafish 对战
- 胜率 benchmark
- milestone 强度判定

这些属于棋力 benchmark 脚本的职责。

---

## 结果文件必须记录的元信息

每份风格评测结果，至少应写入：

- `style_eval_config_name`
- `style_eval_config_hash`
- `checkpoint_id`
- `action_encoding_version`
- `observation_encoding_version`
- `dataset_schema_version`
- `rules_version`

如果使用了风格参考模型，还建议写入：
- `style_reference_checkpoint`

---

## 推荐输出字段

建议至少输出：

- `global_top1`
- `global_top3`
- `opening_top1`
- `opening_top3`
- `middlegame_top1`
- `middlegame_top3`
- `endgame_top1`
- `endgame_top3`
- `sample_count_global`
- `sample_count_opening`
- `sample_count_middlegame`
- `sample_count_endgame`

可选输出：
- 每阶段平均交叉熵
- 每阶段 KL
- 每阶段概率覆盖率

---

## 可比性规则

两份风格评测结果只有在以下条件下才可直接比较：

1. `style_eval_config_identity` 相同
2. 使用的目标棋手数据集合相同
3. phase split 规则相同
4. checkpoint 所用编码版本相同

如果其中任一项变化，应谨慎解释，必要时重跑基线。

---

## 常见错误

### 错误 1：只看全局 top-1，不看分阶段
后果：
- 看不出开局风格是否保留
- 看不出中残局是否已经漂移

---

### 错误 2：灰区模型直接进入 KL 约束训练
后果：
- 主模型被拉向一个质量不足的风格参考
- 后续 style-constrained RL 结果失真

---

### 错误 3：把棋力评测和风格评测混在一个脚本
后果：
- 职责边界不清
- 结果难解释
- 后续维护困难

---

### 错误 4：把 style eval 配置改了却不升版本
后果：
- 不同阶段结果不可比
- 误判风格保留变化

---

## 第一版风格评测的设计哲学

style eval v1 故意保持简单：

- 使用 ply 切分阶段
- 只要求 top-1 / top-3
- 强制使用灰区恢复机制
- 强调全局 + 分阶段并重

目标不是“完整解释风格”，而是：

> **先建立一个稳定、可执行、可比较的风格评测基线。**
