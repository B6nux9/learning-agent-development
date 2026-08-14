# R2 · 压缩与上下文隔离 —— 讲义

> 2026-08-13/14,Windows 端。交付:output_schema 防火墙 + compress_research 真实现 + token 韧性 + Tavily 真搜索,10 测试全绿,researcher 子图首次真跑。
> 本课起采用**分组交付**模式(用户要求):A 防火墙 → B 压缩工人 → C 韧性自救 → D 真搜索,每组先讲"这段在调用链的哪一环"。

## 〇、R2 在调用链里的位置

```
supervisor_tools(R3)
   └─ asyncio.gather(researcher_subgraph.ainvoke(...) × N 个子课题)
        └─ researcher ⇄ tools 循环:攒下几十条消息的垃圾山
        └─ compress_research:把垃圾山提炼成一页纸        ← Group B/C
   └─ N 份返回值汇入 supervisor 的 context               ← 过墙点(Group A)
```

没有墙:5 并发 × 几十条消息 → supervisor context 爆炸、判断力被垃圾稀释。墙上只开一个小窗:提炼稿 + 原料笔记。

## 一、Group A · 防火墙(output_schema)

- `StateGraph(ResearcherState, output_schema=ResearcherOutputState, context_schema=Configuration)`:第一个 schema 管**图内**(节点看到的完整状态),`output_schema` 管**图外**——`ainvoke` 返回前引擎拿它当滤网,**不在 schema 里的字段一律留在墙内**。
- 这是**结构保证**:supervisor 想拿 `researcher_messages` 都拿不到,不是"它自觉不拿"。约束优于自觉第三次现身(安全线 → reducer → 边界)。
- 旧参数名 `output=`/`config_schema=` 已在 LangGraph 1.0 弃用;`context_schema` 背后是新 Runtime Context API,我们走 `configurable` 老通道不受影响,R5 正面处理。

### TypedDict vs BaseModel:为什么两个 schema 用两种类?

- 能力差异:TypedDict 纯静态标注,运行时就是 dict——零校验零开销,**不支持默认值**(源码 TypedDict 里的 `= 0` 是死代码);BaseModel 有运行时校验和**能生效的默认值**。
- 角色差异:内部状态 = 私有管道,要轻快;输出 = 对外契约,边界上校验和默认值才有价值(异常结束也保证形状完整)。
- 一句话:**内部状态用轻量标注,边界契约用校验模型**——和 FastAPI"内部普通对象、请求/响应边界上 Pydantic"同一哲学(pydantic-at-the-edges)。

### 防火墙的代价:测试世界观崩塌

- R1 的 4 条测试靠偷看 `result["researcher_messages"]` 验证循环行为——墙一立全部作废(KeyError)。
- 修法:断言全部改道**公开契约**。`raw_notes` 保全 tool+ai 原始内容,循环里发生过什么(搜了 q1 没搜 q2、错误变 observation)从墙外都能读出来——**防火墙的第二字段既是降级通道也是审计通道**。
- 教训:加边界会同时约束消费方和测试;验证内部行为只剩两条正路——节点级单测,或经公开契约观察。

## 二、Group B · 压缩工人(compress_research)

- **四模型分工首次落地**:压缩用独立的 `compression_model`(决策密度低、调用频率高——每个 researcher 结束必跑一次,N 并发 = N 次,按 R0 框架应配便宜模型,R4 定案)。
- **模式切换的手法**:复用同一段对话,system prompt 从"你是研究员"换成 `compress_research_system_prompt`,尾部追加一条 HumanMessage(`compress_research_simple_human_message`)。同一堆消息,换个系统人设 + 一句新指令 = 重新框定,不搬运数据。
- **⚠️ 源码坑一(deep_researcher.py:538)**:`researcher_messages.append(...)` **原地改 state 里的 list 对象**——`state.get()` 拿到的就是状态通道本体,append 把压缩指令污染进图状态。与 R1 的 iconcat 同罪:**碰 state 里的可变对象,拼新的,不改旧的**。我们的版本:`researcher_messages = researcher_messages + [HumanMessage(...)]`。
- raw_notes 提取的**类型链方法**(由内向外标类型):`filter_messages(...)` → `list[Message]` →(逐条 `str(m.content)`)→ `list[str]` →(join)→ `str` →(装列表)→ `list[str]`。`.content` 长在每条消息上,不长在装消息的篮子上;`str()` 包一层因为 content 可以是多模态块列表。

## 三、Group C · 韧性自救(重试 + 截断)

- **调用链定位**:compress 的 ainvoke 是全子图**咽喉**——循环每轮只咽增量,唯独这里全量一口闷,最可能被 token 超限打死。
- **错误分类学**:可修复(token 超限)→ 剪短重试;未知错误 → 盲重试赌运气;3 次耗尽 → **降级不抛**(返回错误文案 + raw_notes 照常过墙,原料保命)。
- **截断策略 `remove_up_to_last_ai_message`**:倒序找最后一条 AIMessage,返回它**之前**的所有消息(丢新保旧)。方向由价值分布决定:头部是任务书(丢头 = 失忆任务),尾部是最新一轮结果(丢尾只伤增量)。纯函数:切片产新列表,不碰入参。
- **模式切换双保险与截断相容**:截断必然把尾部的模式切换 HumanMessage 一起剪掉——但 messages 在**循环内重组**,压缩任务书住在 SystemMessage 里,每次重试都新鲜。单通道设计(只靠 HumanMessage)会被截断剪掉任务书本身。
- **⚠️ 源码坑二(deep_researcher.py:569)**:`is_token_limit_exceeded(e, configurable.research_model)`——嗅探对象错位,正在爆 token 的是 compression_model。同 provider 或前缀不被识别(→ 全分支兜底)时侥幸无害;**异构 provider 时被锁死在错误分支**:token 超限被误判为其他错误 → 不截断 → 盲重试三连败 → 本可一刀救活的场景必死。上游长期存活的三层掩体:默认配置掩护 + 异构才触发 + 表象是"压缩失败"不是"检测失灵"。
- `is_token_limit_exceeded` 嗅探比想象更严:不光匹配报错文案,还验异常**类名**(BadRequestError)和**所属模块**(openai/anthropic/...)——文案会撒谎,出身不会。测试里造 `__module__ = "openai"` 的假异常类过安检。
- **FakeChatModel 剧本可安排异常**(item 是 Exception 则 raise):脚本式假模型的边界——**验证控制流走向可靠,验证"某角色说了什么"脆弱**(只认调用顺序不认调用者,控制流一变,脚本位置与节点角色错位)。

## 四、Group D · 真搜索(配置开关)

- **单一装配点的回报**:搜索工具全项目只从 `get_all_tools` 进入,fake 换真只切这一个函数,两个调用点、循环、压缩、防火墙零改动——R1"同签名换实现"的兑现。
- **配置驱动**:`search_api: str = "fake"`,默认离线(10 条单测拔网线纪律不破),冒烟显式配 `"tavily"`。行为差异进配置,不进代码硬分支。
- **惰性构造**:`TavilySearch(max_results=3)` **实例化即要 key**(无 key 直接 ValidationError)——必须在 `"tavily"` 分支内部构造,写在 if 外"备用"会让离线环境进函数就炸。
- `research_topic` 字段至今无人读:主题以**种子 HumanMessage** 进场(R3 里是 supervisor_tools 的活,冒烟脚本代劳)。
- 欠条:源码自研 tavily 工具(逐页拉全文 + summarization_model 摘要)vs 我们用现成 TavilySearch——R4 算账。

## 五、smoke 实证(首次真跑)

- DeepSeek 决策 + Tavily 搜索 + 压缩稿出炉;raw_notes 32,138 字符留墙内,过墙一页纸——context isolation 成为机器上的事实。
- **3 轮预算,5 次搜索**:预算单位 = 模型回合 ≠ 工具次数的活证据(单轮并发多调)。TavilySearch 单 query 接口 vs fake_search 收 list——**工具 schema 反过来塑造模型调用形态**。
- 压缩稿格式(调用清单 + 分节 findings + 来源标注)全部来自 compress_research_system_prompt,零格式化代码——R4.5 精读。

## 六、diff 复盘总账(6 项)

| # | 差异 | 判定 |
|---|---|---|
| 1 | 原地 append 污染 state(源码 538) | **我们更好**(findings ②) |
| 2 | 嗅探传 research_model(源码 569) | **我们更好**(findings ③) |
| 3 | 源码自研 tavily(全文+摘要管线) | 源码更强,欠条 R4 |
| 4 | SearchAPI 枚举 + metadata vs 一个 if | 源码更工程化,规模下等价,R5 再看 |
| 5 | 截断剪掉模式切换 HumanMessage(两版同病) | 双保险兜住,quiz Q2 |
| 6 | filter messages vs researcher_messages | 等价(include_types 反正滤掉 system/human) |
