# Reflection 反思范式（L8 追补 · 校招闭环补齐）

> 定位：**不是新概念，是给 L8 那个 loop 补最后一环**。
> 百度 JD1/JD3 点名「Planning-Acting-**Reflection** 闭环」/「反思」——这是校招缺口，故最优先。
> 对标书 Ch8（持续进化/self-improvement）的入门形态。

---

## §0 最小记忆集（三个锚点，记不住时只记这三条）

1. **Reflection = 执行后加一道「自我批判 → 修正」的关卡**。
   你 L8 的 loop 是 Reason→Act→Observe；反思是在 **Observe 之后、把答复交出去之前**，插一个 **Evaluate→Revise**。
2. **一条轴 = 反思的触发频率**：每次都反思（贵、可能 over-correct） vs 有失败信号才反思（L8 `stop_reason` 回扣）。
3. **反思必须有「依据」**：空泛的「再想想」没用；要给明确 rubric/红线。
   **你的三道安全线 + SYSTEM_PROMPT 话术约束，就是现成的 rubric。**

---

## §1 为什么是这一课（JD 缺口）

- 百度 JD1/JD3 都点名 **Planning-Acting-Reflection 闭环** / 「反思」。
- capstone 现状：**Planning**（模型自己决定调哪个工具，隐式）+ **Acting**（dispatch 落地）+ **Observing**（结果回喂）——**唯独缺 Reflection**。
- 一句话：现在的 agent「做完就交」，没有「交之前自己审一遍」。补上这一环，闭环才完整，简历才敢写「Planning-Acting-Reflection」。

---

## §2 Reflection 到底指什么 —— 三个层次别混（面试要能区分）

「反思」是个大词，学界至少三种，别混为一谈：

| 层次 | 是什么 | 代表 | 适用 |
|---|---|---|---|
| **(a) Self-Refine 单次输出精修** | 对一次输出做 生成→批判→改写，不涉及任务成败 | Madaan et al. 2023 | 写作/代码/答复质量 |
| **(b) Reflexion 从失败轨迹学教训** | 任务**失败**（有 reward 信号）后，写一段「我为什么失败/下次怎么改」的反思文本，**存进 memory**，下次 attempt 带着教训重试 | Shinn et al. 2023 | 多次尝试的任务（游戏/编码/agent benchmark） |
| **(c) Reflection as node 工程落地** | agent 图里加一个 critic/evaluate 节点，条件边决定 accept 还是回到 act | LangGraph 典型 pattern | 生产落地形态 |

- **Reflexion 的精髓**：它是「**语言化的强化学习**」——不更新模型权重，更新的是 **context 里的经验**。这也是它能接到书 Ch8「持续进化」的原因：真正的 self-improvement 会把这些教训沉淀成长期 memory 甚至微调数据。
- **你的 capstone 要做的 = (a)+(c) 的结合**：输出前加一个 critic 节点，按 rubric 判 accept/revise。
  (b) 那种「跨 attempt 存教训」是更重的版本——**讲清、但先不做**（留 L11/Ch8）。

---

## §3 反思的解剖（Reflexion 的三个角色）

- **Actor（干活的）**：你现在的 `run()` loop。
- **Evaluator（打分/挑错的）**：新加的 `reflect`。它可以是三种信号来源，**越靠上越可靠**：
  1. **代码/规则**（最可靠、零成本）——能用 `if` 判的（越权、超额）**根本不该让 LLM 反思**，那是 L8 已经 hard-code 的闸。
  2. **真实环境反馈**（最强）——如「测试是否通过」「工具是否报错」。
  3. **LLM-as-judge**（最灵活、但有盲区）——判「代码判不了、但有对错」的东西。
- **Self-reflection（改进指令）**：把 evaluator 的「不合格」**翻译成一段可操作的修改指令**，喂回 Actor。

> **关键判断**：反思**只留给「代码判不了、但有对错」的地方**——话术是否泄露隐私、是否答非所问、是否承诺了不该承诺的（如替人工下了退款结论）。
> 能 hard-code 的（越权/超额）继续 hard-code，别退化成让 LLM 去「反思要不要越权」——那是把可靠的闸换成不可靠的判断，倒退。

---

## §4 工程判断（面试真正问的六点）

1. **反思不是免费的**：+1~N 次 LLM 调用（latency 可能翻倍）、+token、**可能 over-correct**（把对的改错）。
2. **什么时候值得反思？** 三个信号同时看：① 输出**面向用户且不可撤回**（客服话术发出去收不回）② 有**明确失败判据**（rubric）③ 错误**代价高**。
   反过来：内部中间步骤、代价低、无判据 → **别反思**。
3. **触发方式**：全量反思（每次）vs **信号触发**（有 `stop_reason`/工具报错/低置信才反思）。生产多用后者省成本（L8 stop_reason 回扣）。
4. **必须有次数上限**：反思→修正→再反思 可能死循环或 thrashing（**L6 压缩 thrashing 回扣**）。`max_reflections = 1~2`。
5. **Evaluator 的独立性问题**：让同一个模型「自己判自己」有盲区（它当初就是觉得对才这么写的）。缓解三招：① 换视角提问（「站在**合规审查**角度，这条回复有没有泄露/越权/瞎承诺？」）② 换更强模型当 judge ③ 用代码红线兜底。
6. **反思要具体**：让它「指出哪里不好 + 给可操作修改」，不是「再检查一遍」（**L6 prompt 别用模糊限定词回扣**）。

---

## §5 接到 capstone 的落点（本节作业的施工图）

- **落点 = `run()` 的正常出口前**：`if not msg.tool_calls:` → 即将 `return msg.content` 那一刻。
  这一刻 agent 已拿到工具结果、写好了给用户的话 = **最该在「发出去之前」审一遍的点**。
- **rubric 来源 = 现成的**，不用另编：
  - SYSTEM_PROMPT 话术约束：`forbidden` 统一话术不解释原因 / `needs_human`·`not_covered` 不自己承诺、去调 escalate。
  - 三道安全线：越权、退款阈值、RAG 幻觉。
- **流程**：reflect 判 `revise` → 把 critique 当一条反馈 append 回 messages，让模型**重写一次**；判 `accept` → 照常 return。
- **上限 = 1 次**（客服场景 latency 敏感）。
- **可测性**：`reflect` 内部用 LLM-judge，但**接口设计成可 mock**（惰性化、接缝清晰），这样门禁 pytest 能「拔网线还能过」（L10 mock 深水区回扣）。

---

## §6 对标书 Ch8 & 研究锚点

- **一手论文**：Reflexion（Shinn et al. 2023）、Self-Refine（Madaan et al. 2023）。
- **工程 pattern**：LangGraph 官方 reflection / reflexion tutorial（条件边 + critic 节点，正好对比你 L9 的 ADR）。
- **书 Ch8**：Reflexion 是 self-improvement 的入门形态（不更新权重、只更新 context 经验）。真正的持续进化把反思教训沉淀成**长期 memory / 微调数据** → Ch7/Ch8 研究向加分项。

---

## §7 一句话总结

> 你 L8 造了会「想→做→看」的 loop；这一课教它在「看完、要交卷之前」，
> **按红线自己审一遍、不合格就重写一次**——这就是 Planning-Acting-**Reflection** 闭环缺的那一环。
> 工程上真正的难点不是「加个 critic」，而是**判断哪些该反思、给什么 rubric、如何不 over-correct、如何控成本**。
