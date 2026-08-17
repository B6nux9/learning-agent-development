# R3 · Supervisor 与并发派活 —— 总结

> 2026-08-15(Group A,Windows 端)/ 2026-08-17(Group B/C/D,mac 端)· ODR 复现专题第四课

## 交付物

- `state.py`:override_reducer(双语义 reducer)· ConductResearch(带字段协议工具)· SupervisorState(5 字段,3 个挂 override_reducer);ResearcherState/ResearcherOutputState 的 raw_notes 升级 override_reducer(源码同款)
- `deep_researcher.py`:supervisor 节点(三件套协议 + 不拼 system prompt + research_iterations 计数)· supervisor_tools(前置三退出 + think_tool 内联 + ConductResearch gather fan-out + 预算切片 + 超发教育回执 + except 兜底收工)· supervisor_subgraph 编译(无 output_schema——供墙内调用,无需二道防火墙)
- `configuration.py`:max_researcher_iterations=6 · max_concurrent_research_units=5(教练给)
- `utils.py`:get_notes_from_tool_calls(教练给,源码原样)
- `tests/test_r3.py`:**20/20 绿**(Group A 8 + B 4 + C 5 + D 3),全套回归 30/30;FakeResearcherSubgraph/ExplodingResearcherSubgraph 替身隔离层级(supervisor 层只测转手逻辑)
- 本机新增源码参照 clone:`reference/repos/open_deep_research/`(gitignore 内)

## 过程实录(如实)

- **Group A(跨机交接后完成)**:R3-1/3 一次过;R3-2 栽在 `Annotated[str, "描述"]`——pydantic 静默忽略裸字符串,`description=None`。教学点:LangGraph 和 pydantic 是**两套 Annotated 元数据消费者**,互不认识对方的货。
- **Group B**:R3-4/5 全对,一个字没改。但 IDE 自动 import 事故(`from asyncio import tools` 等两行)混进 import 区,与 R1 错①(名字遮蔽)同族。验收两问全过且超范围:override 信封缺失的三条后果推导完整(特权位/续写压力/永不清场),"不出示信封,它就是 operator.add 本人"为本课金句。
- **Group C**:R3-6/7/9 亲手一次过(前置三条件、think 拦截、子图编译含"为什么不需要 output_schema"思考题)。**R3-8 两处翻车**:①`args["topic"]` 字段名想当然(出处是自己 R3-2 定义的 schema);②"改一半/漏 return"**三犯**——写到 gather 就停,无回礼无 return。
- **⚠️ 代写升级**:R3-8 学习者两次要求教练代写(含清空重写一次);Group D 的 R3-10/11 也要求教练代写。教练劝亲手重写清债,学习者选择直接封版——**如实记账,quiz 未亲答**。
- **findings ① 拍板**:except 兜底取诚实写法(无条件收工),未复现 `or True` 死代码,注释存源码原文。

## 债务账本(R4 开工先清,不清不开)

| 项 | 内容 | 验收 |
|---|---|---|
| quiz 未亲答 | `lessons/r3/quiz.md` 全卷 5 题 | R4 开工第一件事亲答,过了才开课 |
| R3-8 二次代写 | fan-out 四步(gather/zip 回礼/raw_notes 聚合/收尾路由) | quiz Q1/Q2 押题 |
| R3-10 代写 | 预算切片 + 超发教育回执 | quiz Q3 押题 |
| R3-11 代写 | except 兜底 + findings① 选择 | quiz Q4 押题 |

## 与源码的差异总账(累计)

**我们更好(3 处)**:①模式切换拼新列表 vs 源码原地 append(538);②token 嗅探传 compression_model vs 源码传 research_model(569);③**新增**:except 兜底诚实写法 vs 源码 `or True` 死代码(334)——行为等价,但不留"看似在嗅探实则永真"的误导。

**findings 池(R5 汇总 findings.md)**:① `or True`(334,本课处理)② 原地 append(538,R2 修)③ 嗅探错位(569,R2 修)④ `max_react_tool_calls` 名不符实(R1 发现)。

## 面试速记(详见 interview-notes 十四)

镜像 ReAct 零真实执行 · 前置/后置检查 × 成本结构 · override_reducer 数据通道内嵌控制协议 · 成果双通道(决策 ToolMessage / 审计 state)· 超发教育(应答规矩 + 教模型自我修正)· 三重预算量纲(深×2 宽×1)· gather 顺序保证。
