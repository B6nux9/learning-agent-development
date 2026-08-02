# ADR-001：客服 Agent 编排层 —— 裸 SDK vs LangGraph

- **状态**：已接受
- **日期**：2026-07-29
- **背景课**：L9 框架对比。同一个有界工作流（客服 Agent 的 orchestration 循环）用两版实现后做选型。

---

## 1. 背景（Context）

客服 Agent 的编排层（agent loop：模型决策 → 调工具 → 观察 → 循环/终止）已用**裸 OpenAI SDK 手写 `run()` 封版**
（`agent.py`）。L9 用 **LangGraph** 把同一循环重写一版（`agent_langgraph.py`），工具层 `tools.py` 两版**共用、一行不改**。
需要决策：**这个项目的编排层，用裸 SDK 还是 LangGraph？** 约束/在意点：
- 硬安全线：`user_id` 由会话代码注入，**绝不接受模型输出的 id**（防越权）；退款阈值 hard-code；转人工可审计。
- 场景：有界、短对话、延迟敏感、可靠性 > 灵活性。
- 目标：可维护、面试可讲清取舍、为未来复杂化（human-in-loop、三档澄清、多 agent）留余地。

## 2. 备选方案（Options）

| 方案 | 定位 | 一句话 |
|---|---|---|
| **A. 裸 SDK 手写 loop**（已封版） | 完全自控 | 一个 `while` + `if`，控制流全在你手里 |
| **B. LangGraph**（本节重写） | 有状态图编排 | 把 loop 画成图：节点+条件边+回边，框架跑图 |
| **C. `create_react_agent`（一行版）** | 最高层封装 | 一行生成整个 agent⇄tools 循环 |

## 3. 本节实测证据（Evidence，事实记录）

**概念映射（B 相对 A 没有新概念，只是给循环一个标准形状）**
- `while` 循环 → 图；`messages` → `State`；调 LLM → `agent` 节点；`dispatch` → `tools` 节点；
  `if not tool_calls` → 条件边；`回到 while 顶` → `tools→agent` 回边；`terminal 检查` → tools 后第二个条件边；
  `LoopGuard.max_steps` → `recursion_limit`。**一一对得上。**

**框架 B 买来的好处（实测）**
- **可视化**：`draw_mermaid()/draw_mermaid_png()/draw_ascii()` 真能把图画出来（本节生成了 PNG）。
- **结构可声明/可校验**：条件边给 `path_map`（或 list）后，框架"看得见"所有可能去向。
- （未用但天然支持）checkpoint 断点续跑、streaming 中间步、加节点容易（human-in-loop / 三档澄清）。
- **便利**：LangChain 把 `tool_calls` 的 `args` 预解析成 dict，省了裸 SDK 的 `json.loads`。

**框架 B 的摩擦/代价（本节真撞到的）**
- ⚠️ **内置件不合身**：`ToolNode`/`create_react_agent` 假设"模型 args 可信、直接喂工具"，
  **撞我们的 `user_id` 注入安全线** → 只能落回**自定义 `tools_node`**（或学 `InjectedState` 这套额外机制）。
  → **框架的优雅捷径假设你走 happy path；一旦有非标准安全需求，捷径就不合身。**
- ⚠️ **`recursion_limit` 是 `raise GraphRecursionError`**，不像裸 SDK 的 `LoopGuard` 优雅 return 转人工
  → 生产要自己 `try/except` 兜底。**框架给闸门，但默认行为（崩）未必是你要的（优雅降级）。**
- **可视化红利依赖静态声明**：动态路由（不给 `path_map`）能跑，但框架"看不见"结构、画不出图。
  → **框架工具的价值 ∝ 你把结构显式声明出来的程度。**
- **迁移摩擦**：`tool_calls` 从裸 SDK 的嵌套对象（`call.function.name`、args 是 JSON 字符串）
  变成 LangChain 的扁平 dict（`call["name"]`、args 已是 dict）——写法要改。
- **依赖变重 + 工具链复杂度上升**：多了 langgraph/langchain-openai 及一堆传递依赖；
  画 ASCII 要额外装 grandalf（且踩了"pip 装错环境、uv 项目要 uv add"的坑）。

**代码量**：两版**功能对等**，LangGraph 版**并没有更短**——因为安全注入逼我们写自定义节点，省不掉。
但 B 的**结构更显式、能画图、加分支更容易**。

---

## 4. 决策（Decision）

**编排层采用裸 SDK（方案 A）。**

理由（按分量排序）：
1. **框架招牌价值对当前场景提升不大**：客服是有界、短对话、延迟敏感的 loop，
   LangGraph 的核心红利（可视化 / checkpoint 断点续跑 / 易加分支）现在都用不上。
2. **安全注入需求逼我写自定义节点**：`user_id` 会话注入这条安全线，让内置 `ToolNode` 不合身，
   用 LangGraph 也得手写 `tools_node`——**框架连"省代码"都没做到**。红利用不上 + 代码没省下 + 复杂度还上升。
3. 省依赖是附带好处，不是主因。

## 5. 后果与权衡（Consequences）

- **得到**：完全控制安全关键路径（注入/阈值/终止）、依赖最小、无框架黑盒（出问题能直接看到底层）。
- **代价**：放弃现成的可视化 / 断点续跑 / 声明式分支——未来若需要，得自己搭或届时迁移。
- **重新评估的触发条件**（任一出现即重估切 LangGraph）：
  - loop 长出**多条件分支**（如 RAG 三档 confidence-band 澄清路由）；
  - 需要 **human-in-the-loop**（人工审批节点）；
  - 扩成**多 Agent 协作**；
  - 长任务需要 **checkpoint 断点续跑 / 状态持久化**。
