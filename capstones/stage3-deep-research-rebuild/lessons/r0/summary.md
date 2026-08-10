# R0 蓝图与环境 · 课程总结

> 封版:2026-08-11 · ODR 复现专题第一课(半节课体量)· 交付物:DESIGN.md 定稿 + 环境全通 + smoke test
> 定位:动笔前把三层图立在脑子里;检验方式=凭记忆复述,不是听讲。

## 一、这节学了什么(一句话)

ODR 的三层图结构、两个循环各自的三条退出路径、context isolation 与"协议工具"两大设计决策,以及环境打通(DeepSeek + Tavily 各自 smoke 通过)。

## 二、这节课实际发生了什么

1. **凭记忆画蓝图**:主图结构一次画对(含"supervisor 子图整体作为一个节点"),两个循环的退出条件最初答"不确定"——用"预算耗尽 / 主动宣告"两分法支架后,六条全部自行推导出来,含第三种"不调工具"边界。
2. **文件职责问答**:prompts/utils/configuration 基本对;`deep_researcher.py` 答不确定——实际上就是"图本身"(任务一画的图写在哪);`ConductResearch`/`ResearchComplete` 本质(Pydantic 协议类、拦截不执行)是本课最大的新知识。
3. **DESIGN.md 共创落笔**:五条"面试可直接引用"的设计决策 + 与 stage2 capstone 六维对比表。
4. **smoke test**:两个 TODO。DeepSeek 一次过,还顺带发现 v4-flash 是推理模型(46/70 token 在思考);Tavily 一侧**"改一半/漏 return"再犯**——dict 打出来看了,返回值还是占位符"test"。这是 PROGRESS 长期跟踪的短板第 N 次出现,当场立了规矩:**每个 TODO 写完,跑之前回读 docstring 契约问"返回的东西对吗"**(30 秒动作)。
5. **Quiz 3 题**:Q1 Q2 过;Q3 答反(把"重要"当成了给推理模型的理由)→ 补讲"决策密度 × 调用频率"框架 → 变式题(capstone 三处调用选一个)秒对。

## 三、面试可复用的表述(本课新增)

- "多 agent 的核心价值之一是 context isolation:子图 output schema 是**结构保证**的防火墙,不靠下游自觉——和我 capstone '约束优于自觉'同一哲学,约束对象从模型换成了未来的自己。"
- "工具可以只是协议:ConductResearch 是 Pydantic 类,模型调用时无代码执行,supervisor_tools 拦截 tool call 当派活任务书读。"
- "推理模型分配看决策密度 × 调用频率,不看'重要性':最高频最机械的 summarization 恰恰最不能用推理模型。"

## 四、遗留与下一步

- 模型名暂用 v4-flash(推理模型),四角色正式选型放 R4 讨论。
- **R1(下一课)**:Researcher 子图纵切 MVP——state.py(Researcher 部分)+ researcher / researcher_tools + 子图编译,fake search 先行。用户第一次亲手写 LangGraph 子图与 reducer。
