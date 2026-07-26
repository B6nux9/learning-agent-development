# L8 讲义：任务规划 —— 路由 / ReAct / Plan-and-Execute

> JD **6/10**。本节的特殊之处：**几乎不教新代码结构，而是给你 L2 就写出来的东西正式命名，
> 并划清它的边界。** 别当新东西学 —— 是给旧知识装上术语和权衡。

## 0. 最小记忆集：只记 3 个锚点，其余全部现场推

> 本讲义表格多，**表格是查阅用的，不是背诵用的**。真正要装进脑子的只有下面三条。

### 锚点 ①　我 L2 手写的 loop 就是 ReAct
Thought（模型推理）→ Action（`tool_calls`）→ Observation（`role="tool"`）→ 回到 Thought。
**推得出**：ReAct 不是新东西 / 原版靠解析文本、现版靠结构化字段 /
Thought 不外显 ⇒ 不可观测 ⇒ "看 tool_calls 不看话术"。

### 锚点 ②　一条轴：**重规划频率**
```
每步重规划 ◄──────────────────────────► 只规划一次
  ReAct          真实系统在中间        Plan-and-Execute
              (Plan→Execute→偏差才Replan)
```
**推得出**（不用背表）：
- 失败模式：每步都能改主意 → 绕圈/无限循环；从不改主意 → **机械执行过时计划**
- 成本：每步重规划 = 每步 1 次 LLM 调用，贵且天然串行；只规划一次 = 多一轮首延迟，但执行可并行
- 适应性：轴左端强、右端弱。**"更可控"是错觉——右端只是把不确定性提前了**

### 锚点 ③　**自主性是成本，不是收益**
只在**环境不可预测 + 试错便宜**两条同时成立时才买它。
**推得出**：
- coding agent：两条都成立 → 不要 planner，纯 ReAct（Claude Code 的 plan mode 是**给人审批的工件**，不是调度器）
- 客服 agent：两条都不成立 → 静态路由收敛意图 + 分支内受限短 loop
- §4"什么时候该规划"那 5 条 → 其实只问 3 个问题：
  **规划时信息够吗？步骤能并行吗？人要审批吗？** 三个都否就别规划。

### 附：§6 那 6 个 stop_reason 也不用背
分两类：**正常结束**（`FINAL_ANSWER` / `HANDOFF`）+ **被迫结束**。
被迫结束 = 四样东西耗尽 —— **步数没了 / 进展没了 / 钱没了 / 工具死了**
（`MAX_STEPS` / `NO_PROGRESS` / `BUDGET_EXCEEDED` / `TOOL_FATAL`）。

---

## 1. 正名：你 L2 手写的 loop 就是 ReAct

ReAct = **Rea**soning + **Act**ing（Yao et al., 2022）。循环三拍：

```
Thought      我该干什么
Action       调用工具
Observation  工具返回什么
   └──────► 回到 Thought
```

对照 `lesson-02/homework/order_agent.py`：

| ReAct 环节 | 你的代码 |
|---|---|
| Thought | `client.chat.completions.create(...)` 模型内部推理 |
| Action | `msg.tool_calls` |
| Observation | `AVAILABLE_TOOLS[name](**args)` 的返回值 → `role="tool"` 消息 |
| 循环 | `while True` |
| 终止 | `if not msg.tool_calls: return msg.content` |

**一处不落，全中。**

## 2. 面试高分点：原版 ReAct vs function-calling 版

原论文年代（GPT-3）没有 function calling。ReAct 是**纯 prompt 格式**：让模型输出文本
`Action: query_order[A123]`，你用正则/解析器抠出来。

今天 **function calling 把 ReAct 协议化了**：Action → 结构化 `tool_calls` 字段，
Observation → `role="tool"` 消息。

> **现代 function-calling agent loop = ReAct 的协议化版本。**
> 你不是"没学过 ReAct"，你是一上来就写的工业版。

| | 文本版 ReAct | function calling 版 |
|---|---|---|
| Action 解析 | 正则抠字符串，**会解析失败** | API 返回结构化字段，格式几乎不出错 |
| 参数类型 | 全字符串，自己转 | JSON Schema 约束，类型/必填模型侧保证 |
| 并行调用 | 做不到 | 一轮可返回多个 `tool_calls` |
| 换模型 | prompt 要重调 | schema 通用 |
| 还有用吗 | **有**：模型不支持 tool use 时的降级方案（小模型/老开源模型） |

回扣 L6：**function calling 本质是结构化输出**——这个结论你 L6 已经自己得出过。

### Thought 去哪了？
function-calling 版里显式 Thought 被三种方式承载：
1. 模型自己在 `content` 里写一段（部分模型会）
2. 推理模型的 reasoning tokens（你 L2 作业就开了 `extra_body={"thinking":{"type":"enabled"}}`）
3. 完全不外显，隐含在权重里

**生产影响：Thought 不外显 = 不可观测。** 你 L5 的金句
"验收 agent 看 tool_calls 不看话术"正是这条的推论。L13 可观测性回收。

## 3. 谱系：确定性 ↔ 自主性

```
确定性高 ──────────────────────────────────────────► 自主性高
硬编码流程   静态路由    路由+受限ReAct    纯ReAct    Plan-and-Execute   自主多agent
(if/else)   (L4学的)    (客服主流)                  (先出全量计划)      (L11)
```

**反直觉点：Plan-and-Execute 不比 ReAct"更可控"，它只是把不确定性提前了。**
"先规划"听着稳，实则把赌注一次性押在"规划时信息是否足够"上。

| | ReAct | Plan-and-Execute | 静态路由 |
|---|---|---|---|
| 何时决定下一步 | 每轮看到 observation 后 | 开头一次性定完 | 代码/路由器定，模型不逐步定 |
| LLM 调用 | 每步 1 次（贵） | 规划 1 次 + 执行可批量/可用小模型 | 1 次路由 + 分支内 |
| 适应意外 | 强 | 弱（计划会过时） | 无（走不到的分支就走不到） |
| 可预测/可审计 | 差（路径每次不同） | 中（计划是可看可审批的工件） | 强 |
| 典型失败 | 绕圈、越走越偏、无限循环 | **计划过时后仍机械执行** | 意图覆盖不到 → 掉兜底 |
| 延迟 | 步数 × 单轮延迟，累加 | 多一轮规划首延迟；执行可并行 | 最低 |

## 4. 核心问题：什么条件下显式规划有帮助？

**有帮助（几条同时成立才值得）：**
1. 步数多且相互依赖（>5 步），逐步决策容易丢目标
2. **规划期信息就足够**——不必先看中间结果才知道后面怎么走
3. 步骤**可并行**——有计划才能并发调度（ReAct 天然串行）
4. **需要人类审批**——计划是能给人看、给人改的工件（退款、运维变更、大改代码）
5. 执行贵/不可逆——执行前能对计划做静态检查（预算、权限、幂等）

**产生过时计划和多余延迟：**
1. 任务 1–3 步就完 → 规划那轮纯属额外延迟
2. 中间结果决定后续分支（"查了才知道该退款还是转人工"）→ 计划开头就是猜的
3. 用户会打断、会改口（**客服对话的常态**）→ 计划刚出就作废
4. **没有 replan 机制** → 计划一错就一路错到底（最惨失败模式：机械执行已知错误的计划）

### 本节最值钱的一句（面试直接用）
> **ReAct 和 Plan-and-Execute 不是两种架构，是"重规划频率"这条连续轴的两端。**
> ReAct = 每步重规划；Plan-and-Execute = 只规划一次。真实系统落在中间某点。
> 所以主流实现都是 Plan → Execute → **偏差触发 Replan**。

## 5. 为什么 pi / Claude Code 不内置 planner，客服 agent 却常要显式路由？

**coding agent（pi / Claude Code）**
- 环境极度动态：读一个文件就可能推翻整个计划
- 反馈**廉价且即时**：跑个测试就知对错，试错成本低
- 单会话可跑几十上百轮，模型有充足机会自我纠正
- 工具少而强（read/write/edit/bash），组合空间靠模型自己探索
- → **逐步 ReAct 优于预先规划**；硬塞 planner 只产出立刻过时的计划 + 首轮延迟
- ⚠️ Claude Code 有 plan mode，但那是**给人审批的工件**，不是内部执行调度器
  —— 正好印证"规划的价值常在人机协作面，不在调度面"

**客服 agent**
- 意图空间**有界且已知**（查单/退款/改地址/投诉……就那些）
- 合规硬约束：校验、幂等、审计、可转人工
- 用户等着，延迟敏感，不能自由探索 10 轮
- **错误代价不对称**：多问一句=轻微体验损失；错退一笔款=真金白银+合规事故
- → **静态路由把不确定性锁小**，分支内跑**受限短 ReAct**（工具子集 + 低步数上限）

> 面试话术：**自主性是成本，不是收益。** 只在"环境不可预测 + 试错便宜"时买它。
> 客服两条都不成立，所以我用路由收敛意图，在分支内跑受限 loop。

## 6. 生产级 loop 控制（本节最硬的工程部分）

`while True` 是玩具。生产 executor 至少要有：

### 6.1 多重终止条件，且**原因必须显式枚举**
| stop_reason | 触发 | 上层该怎么兜 |
|---|---|---|
| `FINAL_ANSWER` | 模型不再点单 | 直接返回 |
| `MAX_STEPS` | 轮数上限 | 道歉 + 转人工 |
| `NO_PROGRESS` | 连续 N 轮重复"同工具+同参数" | 打破循环，转人工 |
| `BUDGET_EXCEEDED` | 累计 token/耗时超预算 | 降级或转人工 |
| `TOOL_FATAL` | 工具不可恢复错误（≠ L3 那种可回传自愈的错误） | 报错 + 告警 |
| `HANDOFF` | 模型/规则主动转人工 | 走人工队列 |

**为什么必须枚举而不是返回一个字符串？**
→ 可观测（L13 trace 字段直接来源）、可测试（pytest 断言的就是它）、
上层能分情况兜底。返回 `str` 的 loop 在生产里等于瞎子。

### 6.2 纯逻辑 / 副作用分离（回扣 L6 v2 作业）
终止判断、no-progress 检测、预算记账 —— 全是**不碰网络的纯函数**，所以能 pytest。
碰 API 的部分只做接线。**这是本节作业能过门禁条件 2 的前提。**

### 6.3 每轮一行结构化日志（v3 可靠性最小集）
`step_index / tool_name / 耗时 / prompt_tokens / stop_reason`。
用 `logging` 不用 `print`（门禁条件 3）。

### 6.4 循环上限不是防模型犯傻，是防钱包破产
失控 loop + 长上下文 = **平方级 token**（L6 算过的账）。

## 7. 预告：CodeAct —— 第三种 Action 表示法

模型不输出 `{"name":"query_order","args":{...}}`，而直接输出可执行代码：
```python
orders = [query_order(i) for i in ["A123", "B456", "C789"]]
late = [o for o in orders if o["status"] == "延迟"]
```
**在受益于循环与组合的任务上**可显著减少轮次（幅度依工作负载和模型而定，不记定值）。
代价：需要沙箱、安全面暴增、小模型写不出能跑的代码就直接崩。
→ 锚点 `smolagents CodeAgent` 会看真实实现。

## 8. 作业（见 homework/）
把 loop 从玩具升级到生产件，并亲手对比两种范式：
- Part A：带 `stop_reason` 枚举 + no-progress 检测的 ReAct executor（纯逻辑可测）
- Part B：结构化输出 planner（顺手补 L6 Part B 的缺口）+ 偏差触发 replan
- Part C：同一任务两种范式跑对比，出数据（轮次/token/延迟/成功率）
