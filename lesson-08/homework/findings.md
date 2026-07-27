# L8 Part C · ReAct vs Plan-and-Execute 实测对比

> 目的：把讲义 §3 那张"我告诉你的"对比表，自己跑一遍验证。
> 跑法：`uv run python lesson-08/homework/compare.py`（真调 API，会花钱）。
> 原始数据落盘在 `compare_result.json`，可复跑对比。

## 度量口径（重要，先说清楚才有意义）

- **llm_calls**：真实**模型调用次数**。ReAct = 每轮 1 次；P&E = 规划 + 每次 replan + 最终答复。
  **不是** P&E 的 `steps`（那个数的是工具执行数）。修这个偏差的过程见文末「踩坑」。
- **prompt_tokens**：累计 `response.usage.prompt_tokens` 真实值，**含规划那次调用**。
- **elapsed_s**：墙钟耗时。注意 P&E 的规划用慢模型 `deepseek-v4-pro`，单看调用数会低估它的延迟。
- **correct**：**没法自动判**，人工填。（这个痛点就是 L12 要上 LLM-as-judge 的理由；
  L7 建评估集时已撞过一次"子串匹配区分不了确认与否认"，这是第二次。）

## 对比数据表

> 运行环境：DeepSeek 端点，2026-07-27。**json_schema 每次调用都 400
> （`This response_format type is unavailable now`），全部降级到 json_object。**

| 任务 | 形状 | 模式 | stop_reason | LLM调用 | prompt_tokens | 耗时(s) | 正确? |
|---|---|---|---|---|---|---|---|
| T1 | single_step | react | final_answer | 3 | 2334 | 6.44 | ✅（过度调了 check_delay，但答案对） |
| T1 | single_step | plan_execute | final_answer | 2 | 864 | 6.14 | ✅（更精简） |
| T2 | parallel_fanout | react | final_answer | 4 | 3956 | 7.44 | ✅（实赔 A123=17.94 / C789=53.94） |
| T2 | parallel_fanout | plan_execute | final_answer | 2 | 831 | 29.6 | ❌ **幻觉**：编出不存在的 ID 001/002 和假日期，一笔赔付都没执行 |
| T3 | branch_on_observation | react | final_answer | 2 | 1445 | 3.28 | ✅（B456 未延迟，不赔） |
| T3 | branch_on_observation | plan_execute | final_answer | 3 | 1912 | 12.31 | ✅（靠 1 次 replan 自救，但慢 4 倍） |

> ⚠️ **不能只看数字**：T2/P&E 的 831 token / 2 调用看着"最省"，实则**它啥也没干、直接幻觉**。
> "便宜"是失败的副产物。这就是 correct 列必须人工判、且 L12 要上 LLM-as-judge 的理由。

---

## 四问回答

### ① 三个任务各是哪种范式赢？和跑前 expectation 一致吗？

**T1（单步 · A123 查询）—— 预期"ReAct 赢"，部分打脸**
- 实测：ReAct 3 calls / 2334 tok / 6.44s；P&E 2 calls / 864 tok / 6.14s。
- ReAct 因 SYSTEM_PROMPT 逼它 check_delay，**多跑了一轮**（3 calls），token 也因每轮重发全部上下文而累到 2334。
- P&E 反而 token 更省、延迟基本打平——**但打平的原因是 P&E 的规划走慢模型 `deepseek-v4-pro`**，
  1 次慢规划 ≈ 2 次 flash，吃掉了它"调用数少"的优势。
- 结论修正：预期"P&E 白付规划延迟"没完全成立——单步上 P&E 没输，只是**慢模型规划把 token 优势换成了持平延迟**。
  **教训：调用数少 ≠ 更快，要看每次调用的成本。**

**T2（并行扇出 · 列 2026-06 订单并赔付延迟的）—— 预期"P&E 赢"，完全打脸**
- 实测：ReAct 4 calls / 3956 tok / 7.44s **正确**（实赔 A123=17.94、C789=53.94，日志有物证）；
  P&E 2 calls / 831 tok / 29.6s **幻觉翻车**——答案编出不存在的 ID 001/002 和假日期，一笔赔付都没执行。
- **深层原因**：扇出目标（订单号）要先 `list_recent_orders` 才知道，是**运行时才发现**的；
  而 P&E **规划期就得把计划定死**，此刻它根本不知道有哪些订单，**没法写出 `check_delay(A123)`…**。
  于是它规划了个残缺东西 → 答复模型硬编 → 幻觉。
- **金句**：扇出任务目标"运行时发现" vs P&E 要求"规划期已知"——**时序天生冲突**。
  独立可并行还不够，**目标必须规划期已知** P&E 才能并行。
- 便宜是假象：831 tok 看着最省，实则是"啥也没干"的副产物。**只看数字会把失败读成高效。**

**T3（观察分支 · B456 延迟才赔）—— 预期"P&E 翻车"，部分打脸（replan 救了它）**
- fake 数据：**B456 未延迟**（actual 2 < promised 3，`delayed=false`）。
- 实测：ReAct 2 calls / 3.28s **正确**（天然看到观察再决定，一轮搞定）；
  P&E 3 calls / 12.31s **答案也正确**，但 3 calls = 规划 + **1 次 replan** + 答复。
- replan 是怎么触发的：计划给未延迟的 B456 排了 `apply_compensation` → amount 非法 → BusinessError →
  error JSON → `is_plan_stale` 信号①命中 → 触发 replan → 新计划带着"delayed=false"重规划 → 不赔。
  **安全网（信号①）真的兜住了。**
- 结论修正：P&E 没给错答案（replan 自救），但**翻在延迟**——比 ReAct 慢 4 倍，且多烧一轮规划。
  ReAct 对 branch-on-observation 是**原生**处理，P&E 得"先错→再 replan"。

### ② T2 里 parallel_groups 分了几层？真并发能省多少墙钟？

- **实测结论：T2/P&E 根本没能并行。** 因为规划期不知道订单号，它的计划退化成
  「只有 `list_recent_orders` 一步」（或残缺计划），`parallel_groups` 自然只有 1 层——
  **没有扇出，就没有并行可言**。这恰恰印证了 Q①的深层原因。
  （局限：`Measurement` 没存 trace，层数是从"答案幻觉+未执行赔付"反推的；要精确看层数，
  应把 `result.trace` 里 `event=plan` 的 `groups` 也纳入 Measurement——已记为改进项。）
- 反事实估算（**假如**订单号规划期已知、4 单可并行）：分层会是
  `[{list}, {check×4}, {compensate×2}]` 共 3 层；顺序执行 ≈ 7 步 × t，真并发 ≈ 3 层 × t，
  理论省 ≈ (7−3)×t。
- **估算局限**：① 假工具零耗时，真实收益只在工具是网络 IO 时才有；② 忽略并发调度/连接开销；
  ③ 规划那轮固定延迟不随并发缩短；④ 前提"目标规划期已知"在本任务并不成立——这才是关键。

### ③ T3 触发 replan 了吗？几次？max_replans=0 会怎样？

- **常规跑（max_replans=2）：触发了 1 次 replan**（llm_calls=3 = 规划+replan+答复，stop_reason=final_answer，答案正确）。
- **max_replans=0（关掉安全网）实测**：
  `stop_reason=replan_exhausted | llm_calls=1 | steps=3 | 赔付记录={} | answer=None`
  - 计划排了赔付类操作（steps=3），`apply_compensation(B456, amount)` 的 amount 被填成非法值
    （B456 的 `compensable_amount=0`）→ BusinessError → error → `is_plan_stale` 信号①命中 →
    但**无 replan 额度** → 立刻 `replan_exhausted`，`answer=None`。
  - **失败形态是"侦测到→无力修复→安全放弃（不出答案）"，不是"乱赔一通"**。赔付记录为空即证。
- **洞见（这次最值钱的一条）**：安全网的**侦测**（信号①）生效了，但**修复**（replan）被预算掐断。
  更关键——它这次能安全中止是**运气**：模型恰好把 amount 填成非法值撞上了信号①。
  **假如模型猜成一个合法正数，`apply_compensation` 会成功执行（真给未延迟订单赔钱），
  而 `is_plan_stale` 只有信号①、没有信号②，根本检测不到"delayed=false 却赔付"的语义矛盾**——
  那才是真正的"机械执行过时计划且无人察觉"。生产必须补信号②，代价是每步多一次 LLM-as-judge（贵）。
- **契约印证**：`replan_exhausted` 配 `answer=None`，正是 test_executor 里 T2/T5 那条
  "被迫结束 → final_answer is None" 的真实现身——被迫中止就该是 None，让上层知道"无可交付答案，去兜底"。

### ④ 综合结论（面试话术，≤150 字）

> 我在三类客服任务上实测了 ReAct 与 Plan-and-Execute：**ReAct 三战全胜或打平**。
> 单步任务 P&E 的慢模型规划把 token 优势换成持平延迟；并行扇出任务里 P&E 因**目标要运行时才发现、
> 而它规划期就得定死**，直接幻觉出假订单；分支任务 P&E 靠 replan 自救但慢 4 倍。
> 更关键的教训是：**光看 token/调用数会把"失败"误读成"高效"**——P&E 最省的那次其实啥也没干。
> 客服多为单步/浅分支且目标运行时发现，故我**以 ReAct 为主**，仅在目标规划期已知且真可并行的批处理子任务上局部用 P&E。

---

## 踩坑记录（进 interview-notes）

- **llm_calls 度量偏差**：最初 `measure()` 用 `result.steps` 当调用数，但 P&E 的 `steps` 数的是
  **工具执行数**不是**模型调用数**，导致表谎报"P&E 单步省一半"。修法：给 `RunResult` 加独立
  `llm_calls` 字段，两个 executor 各自如实计数。**教训：对比实验里，度量口径错一个，结论全废。**
- **json_schema 降级（真实战况）**：DeepSeek 端点对每一次规划调用都返回
  `400 This response_format type is unavailable now`，**6 次 P&E 规划全部降级** json_object +
  把字段要求写进 prompt + 自己校验。降级代码不是假设演习，是真的救了场——graceful degradation 实例。
- **is_plan_stale 只做了 ①**：只检测 error、没检测语义矛盾（delayed=false 却要赔付），
  是 T3 暴露的安全网漏洞。通用做法是 LLM-as-judge，贵；规则法便宜但不通用。
