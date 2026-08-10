# DESIGN.md · ODR 复现施工图

> R0 共创(2026-08-11):以下结构由学习者凭记忆复述、教练纠偏后落笔。
> 蓝图先行——动笔写代码前,先对这张图没有异议。

## 一、文件职责与边界(镜像源码布局)

| 文件 | 职责 | 一句话边界 |
|---|---|---|
| `state.py` | **数据的形状**:三个 State 类 + 结构化 schema | 状态(AgentState/SupervisorState/ResearcherState + reducer)和协议类(ConductResearch/ResearchComplete/ClarifyWithUser/ResearchQuestion)都是"数据形状",归这里;**不放任何可执行逻辑** |
| `prompts.py` | 全部提示词模板 | 从源码原样复制,不挖空;R4.5 专课精读设计意图 |
| `utils.py` | **可执行的东西** | 搜索工具、think_tool、token 超限检测、消息裁剪;R1 先用 fake search |
| `deep_researcher.py` | **图本身** | 三层图的全部节点函数、边、compile;R1–R4 主战场 |
| `configuration.py` | 运行时可配置 | `from_runnable_config` 读取 + env 覆盖 + `x_oap_ui_config` UI 元数据;R5 接线 |

## 二、三层图

```
主图 deep_researcher (AgentState)
  START → clarify_with_user → write_research_brief
              ↓
        research_supervisor        ← supervisor 子图整体作为一个节点
              ↓
        final_report_generation → END

supervisor 子图 (SupervisorState)
  START → supervisor ⇄ supervisor_tools
                          │ asyncio.gather 并发起 N 个 ↓
researcher 子图 (ResearcherState, output=ResearcherOutputState)
  START → researcher ⇄ researcher_tools → compress_research → END
```

**循环退出条件**(学习者自行推导,已验证):

| 循环 | 预算耗尽 | 主动宣告 | 不调工具 |
|---|---|---|---|
| supervisor | `max_researcher_iterations`(默认 6,数 supervisor 轮数) | 调用 `ResearchComplete` | 一个工具都没调 → 流程结束 |
| researcher | `max_react_tool_calls`(默认 10,数工具调用轮数) | 调用 `ResearchComplete` | 不调工具(开始写总结文字)→ 去压缩 |

- researcher 退出后**必经 `compress_research`**,不能直接 END。
- 第三重预算:`max_concurrent_research_units`(默认 5)限制单轮并发派活数,超发的 call 收到教育性报错 ToolMessage。

## 三、关键设计决策(面试可直接引用)

1. **Context isolation 是多 agent 的核心价值**:researcher 在自己的 context 里翻几十条搜索垃圾,子图声明 `output=ResearcherOutputState`(仅 `compressed_research` + `raw_notes`)作防火墙,过墙的只有提炼稿——supervisor 的 context 不爆、不被污染、派活判断力不降。
2. **工具可以只是协议,不必可执行**:`ConductResearch`/`ResearchComplete` 是 Pydantic BaseModel,`bind_tools` 转成 schema 给模型;模型调用时无代码执行,`supervisor_tools` 节点拦截 tool call 当消息读——参数就是派活任务书。对比 capstone 裸 SDK:手写 JSON schema + dispatch;框架吃掉体力活,拦截逻辑仍要自己写(R3 亲手写)。
3. **fan-out 用 `asyncio.gather` 包子图 `ainvoke`,不用 `Send` API**:简单直接,代价是整批一个 superstep、单个失败整批进 except、无独立 checkpoint。R6 扩展③用 Send 重构对比,写 ADR-002。
4. **think_tool = 把 ReAct 的 Reasoning 变成可见的 tool call**:结构化 scratchpad,强制 supervisor/researcher 在行动间显式反思(对比 capstone 的 reflect.py:事前反思 vs 事后审查)。
5. **四模型分工**:research / summarization(便宜模型) / compression / final_report 四个角色独立可配——按任务难度分配算力。

## 四、动笔顺序(纵切 MVP,每课结束都能跑)

R1 researcher 子图(fake search,拔网线能跑)→ R2 压缩+上下文隔离+真搜索 → R3 supervisor 并发派活 → R4 主图端到端真跑 → R4.5 prompts 精读 → R5 配置层+diff 总复盘。

## 五、与 stage2 capstone 的架构对比

| 维度 | stage2 客服 agent | ODR |
|---|---|---|
| 形态 | 单 agent ReAct + 安全线 | 三层图多 agent(supervisor–researcher) |
| 循环防失控 | LoopGuard 单一上限 | 三重预算(迭代/并发/工具调用)分层设防 |
| 反思 | reflect.py 事后 LLM-as-judge | think_tool 事前显式反思 |
| 终止 | 转人工=终态工具 | ResearchComplete=纯协议终止信号 |
| 上下文 | 单 context 滚动 | 子图 output schema 强制隔离 |
| 编排 | 裸 SDK 手写 dispatch(ADR-001) | LangGraph Command 路由 + reducer 合并 |

## 六、技术选型(R0 定案)

- **LLM**:DeepSeek(`init_chat_model("deepseek:deepseek-chat")`),key 走 `.env` 的 `DEEPSEEK_API_KEY`;`langchain-deepseek==1.1.0` 已装。
- **搜索**:**Tavily**(R0 定案:用户 Google API 确认不可用,回退源码默认方案;free tier 1000 次/月足够教学)。`langchain-tavily==0.2.18` 已装,`TAVILY_API_KEY` 已入 `.env`。
- **测试纪律**:延续"拔网线也能跑绿"——单测用 fake ChatModel,真 API 冒烟测试标 `@pytest.mark.smoke` 单独跑。
