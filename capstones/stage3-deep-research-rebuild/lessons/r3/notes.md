# R3 · Supervisor 与并发派活 —— 讲义

> 2026-08-15(Group A,Windows 端)/ 2026-08-17(Group B/C/D,mac 端)· ODR 复现专题第四课
> 对照源码:`deep_researcher.py:178-363`、`state.py:55-81`(本机 clone:`reference/repos/open_deep_research/`)

## 调用链定位(全课总图)

```
R4 主图 write_research_brief ──(override 信封:system prompt + brief 整体写入)──▶ SupervisorState
                                                                                    │
                                    ┌───────────────────────────────────────────────▼──┐
                                    │  supervisor(思考半步:派谁研究什么)               │
                                    │     │ Command(goto="supervisor_tools")            │
                                    │     ▼                                             │
                                    │  supervisor_tools(行动半步:零真实执行的转运站)  │──▶ END(收割 notes 过墙)
                                    │     │ think_tool → 内联 ToolMessage               │
                                    │     │ ConductResearch → researcher_subgraph ×N    │
                                    │     │ ResearchComplete → 按名字识别改路由          │
                                    │     └ Command(goto="supervisor")继续循环          │
                                    └───────────────────────────────────────────────────┘
```

supervisor ⇄ supervisor_tools 是 researcher ⇄ researcher_tools 的**镜像 ReAct 骨架**,三个关键差别:

1. **supervisor 的工具零真实执行** —— 三件套 `[ConductResearch, ResearchComplete, think_tool]` 全按名字拦截转手:think_tool 内联造 ToolMessage;ConductResearch 转手 `researcher_subgraph.ainvoke(...)`;ResearchComplete 只改路由。R2 防火墙的下游回报:supervisor 只见 `compressed_research` 提炼稿,不见 32k 垃圾山。
2. **前置检查 vs 后置检查** —— researcher_tools 后置(先执行后查预算);supervisor_tools 前置(进门先查三个退出条件)。原因是成本结构:这一层一次"工具执行"= 整个 researcher 子图跑一遍(十几次模型调用 + 几十次搜索),先查再跑省的是真金白银。
3. **system prompt 来源不同** —— researcher 节点内自己拼 SystemMessage;supervisor 的 system prompt 由 R4 主图用 override 信封整体写入 state,节点内不拼(`input_messages = supervisor_messages` 一行完事)。R3 测试手动 seed。

## Group A · 状态与协议(R3-1/2/3,state.py)

- **override_reducer**:双语义 reducer——`{"type": "override", "value": X}` 信封 → 整体替换;其他一切 → `operator.add` 老路。R1 quiz"写 0 等于没写"的官方解法:**在数据通道里内嵌控制协议**。代价:协议占用数据空间,字段从此不能安全存放恰好长得像信封的普通 dict。学习者金句:"**不出示信封,它就是 operator.add 本人**"。
- **不清场的三条后果**(学习者自行推导,超出提问范围):①system prompt 失去"位置 0 + 全对话唯一"的特权(Anthropic 消息列表见 system role 直接 400,OpenAI 不报错但语义未定义);②旧剧本续写压力——模型看到上一幕以 ResearchComplete 圆满收尾,最顺滑的续写是照旧模式提前收工;③上下文永不清场,token 只增不减。
- **ConductResearch**:带字段的协议工具(对比 ResearchComplete 空壳)。`research_topic: str` + `Field(description=...)`;docstring = 工具级说明书,Field description = 字段级填表须知,两层各管一件事。
- **SupervisorState**:TypedDict 5 字段,`supervisor_messages`/`notes`/`raw_notes` 挂 override_reducer。

## Group B · supervisor 节点(R3-4/5)

- 模型配置**仍用 research_model 那对字段** —— 四角色分工按任务类型切,不按图层级切:supervisor 和 researcher 同属"研究"工作,共用 research_model。"领导和员工用同一个模型合不合理"→ R4 四角色选型辩题。
- 计数器 `research_iterations` +1:形式与 R1-5 一致,但一轮的代价 = 一整批研究。

## Group C · 拦截与 fan-out(R3-6/7/8/9)

- **前置三退出条件**:①`research_iterations > max_researcher_iterations`(`>` 不是 `≥`:supervisor 先 +1 后到这里,数的是"已思考几轮"含本轮)②最新消息无 tool_calls ③出现 ResearchComplete。任一满足 → END,**退出要带货**:`get_notes_from_tool_calls` 把散落对话里的 ToolMessage 收割成 notes 过墙(对比 researcher_tools 退出只是路由)。
- **fan-out 的话题写两处**:`researcher_messages=[HumanMessage(topic)]` 是给模型的对话开场白;`research_topic=topic` 是给 compress_research 的元数据。一份数据、两个消费者、两条通道。
- **gather 保证结果顺序 == 提交顺序**(不管谁先完成),所以 zip 对齐 tool_call_id 是安全的;错位 = 模型看到张冠李戴的研究结果。
- **成果两通道**:`compressed_research` 走 ToolMessage——模型看得见,喂给下一轮派活决策;`raw_notes` 走 state——模型永远看不见,纯审计留档过墙给 R4。塞进 ToolMessage = 亲手拆 R2 防火墙。
- **子图编译不需要 output_schema**:supervisor 的调用方是 R4 主图,SupervisorState 里没有垃圾山(垃圾在 researcher 层已被防火墙拦住),没有需要隔离的东西。

## Group D · 预算与超发教育(R3-10/11)

- **三重预算的量纲**:

  | 预算 | 管谁 | 一单位成本 |
  |---|---|---|
  | `max_react_tool_calls: 10` | researcher 内部轮数(深度) | 几次搜索 |
  | `max_researcher_iterations: 6` | supervisor 思考轮数(深度) | 一整批研究 |
  | `max_concurrent_research_units: 5` | 单轮并发派活数(**宽度**) | 一单=一个完整子图 |

  前两条管循环圈数,这条管单轮扇出宽度——模型一轮派 20 张单,深度预算拦不住(R2 真跑实证的"深度预算管不住宽度",在这里补上了宽度闸)。
- **超发教育两层道理**:①硬约束——provider 规矩,AIMessage 里每个 tool_call_id 都必须有对应 ToolMessage 应答,少一张下轮 ainvoke 直接 400,**裁剪执行不能裁剪应答**;②软设计——回执把预算数字明说给模型("try again with N or fewer"),下轮自我修正。对比沉默丢弃:模型不知道错在哪,还会再超发。(= 学习者 R2 quiz Q3 自提的方案 B,官方同款)
- **except 兜底**:researcher 烂尾不许炸穿图 → END 优雅收工,已收割成果照样带出墙。**findings ①**:源码 334 行 `is_token_limit_exceeded(e, ...) or True` —— 嗅探被 or True 吞成永真死代码。复现版取诚实写法(无条件收工,行为等价,注释存档)。
- 切片用 `[:N]`/`[N:]` 不用 if:对"单子不够 N 张"天然安全。

## 本课错题实录(quiz 素材)

1. **pydantic 不认裸字符串**:`Annotated[str, "描述"]` 里的字符串被 pydantic 静默忽略(`description=None`)——LangGraph 从 Annotated 里找 reducer,pydantic 只认自己的类型(如 Field 对象)。**两套 Annotated 元数据,消费者完全不同**。
2. **IDE 自动 import 事故**:`from asyncio import tools` / `from langchain_openai import tools` 混进 import 区——与 R1 首跑错①(名字遮蔽)同族:名字被无关绑定占用。规矩:跑测试前扫一眼 import 区有没有自己没写过的行。
3. **派活单字段名想当然**:`tool_call["args"]["topic"]` → KeyError。args 的 key 是 R3-2 自己定义的 schema 字段 `research_topic`——名字不是猜的,出处就在三十行外自己写的类。与 R1 错③同族。
4. **"改一半/漏 return"三犯**:R3-8 写到 gather 收齐结果就停,没有 zip 回礼、没有 raw_notes 聚合、没有 return Command——函数返回 None,think_tool 的回礼全部丢失。①②③④是一个完整动作,做到④才算做完。
