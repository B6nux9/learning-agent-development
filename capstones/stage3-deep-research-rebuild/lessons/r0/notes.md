# R0 蓝图与环境(ODR 复现专题)

> 专题定位:挖空复现 langchain-ai/open_deep_research(LangGraph supervisor 多 agent)。
> R0 的任务:把三层图蓝图在脑子里立住 + 环境打通。蓝图先行,动笔在 R1。

## §0 最小记忆集(四个锚点)

1. **三层图**:主图(clarify → brief → supervisor子图 → final_report)⊃ supervisor 子图(supervisor ⇄ supervisor_tools)⊃ researcher 子图(researcher ⇄ researcher_tools → compress)。
2. **循环退出三件套**:预算耗尽 / 显式宣告(ResearchComplete)/ 不调工具。两个循环各自成立。
3. **Context isolation**:researcher 子图声明 `output=ResearcherOutputState`,几十条搜索垃圾在子图内消化,过墙的只有提炼稿——**结构保证,不靠下游自觉**(capstone 哲学的延续:约束优于自觉)。
4. **工具可以只是协议**:`ConductResearch`/`ResearchComplete` 是 Pydantic BaseModel,模型"调用"时无代码执行,`supervisor_tools` 拦截 tool call 当消息读。

## §1 文件职责(镜像源码布局)

| 文件 | 职责 | 边界 |
|---|---|---|
| `state.py` | 数据的形状 | State 类 + 协议/结构化 schema;无可执行逻辑 |
| `prompts.py` | 提示词 | 原样复制不挖空,R4.5 精读 |
| `utils.py` | 可执行的东西 | 搜索工具 / think_tool / token 检测 / 消息裁剪 |
| `deep_researcher.py` | 图本身 | 全部节点函数、边、compile(R1–R4 主战场) |
| `configuration.py` | 运行时可配置 | from_runnable_config + env 覆盖 + x_oap_ui_config(=Studio UI schema) |

## §2 循环退出条件(学习者自行推导)

| 循环 | 预算 | 宣告 | 不调工具 |
|---|---|---|---|
| supervisor | `max_researcher_iterations=6`(supervisor 轮数) | `ResearchComplete` | 一个工具都没调 → 结束 |
| researcher | `max_react_tool_calls=10`(工具调用轮数) | `ResearchComplete` | 不调工具 → 去压缩 |

第三重预算:`max_concurrent_research_units=5` 限单轮并发派活;超发的 call 收到教育性报错 ToolMessage。
researcher 退出必经 `compress_research`(不直接 END)——为 context isolation 服务。

## §3 AIMessage 的形状(R1 天天用)

- `content` 正文 · **`tool_calls`**(空列表=模型这轮不想干活,`if response.tool_calls:` 就是循环判断)· `response_metadata`(finish_reason 等)· `usage_metadata`(token 账单,L13 主题)。
- 看全貌:`response.pretty_print()` / `response.model_dump()`(LangChain 消息全家是 Pydantic)。

## §4 推理模型分配框架(smoke 中的意外收获)

deepseek-v4-flash 是推理模型(46/70 输出 token 在思考)。四角色分配规律:
**调用频率越高越要便宜,决策密度越高才配推理。**
research=唯一决策密集角色(配推理);summarization=最高频×最机械(源码给 gpt-4.1-mini,四角色唯一便宜货,最不能给推理);compression=忠实清洗;final_report=可商榷(写作收益 vs reasoning token 成本)。

## §5 环境定案

- LLM:DeepSeek `init_chat_model("deepseek:deepseek-chat")`(smoke 用了 v4-flash,推理模型,选型 R4 再定);`langchain-deepseek==1.1.0`
- 搜索:**Tavily**(用户 Google API 不可用,回退源码默认;free tier 1000 次/月);`langchain-tavily==0.2.18`;`TAVILY_API_KEY` 入 `.env`
- smoke:`tests/smoke/smoke_r0.py`,两条外部依赖各自验通(冒烟脚本不进 pytest;单测纪律=拔网线跑绿)
