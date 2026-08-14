# ODR 复现专题 · 教学流程文件(REBUILD-PLAN.md)

> **给后续 session 的开工流程(每次必做)**:
> ① `git pull`(两机同步)→ ② 读本文件 **F 断点交接区** 的最后一条 → ③ 按"下一步第一件事"继续。
> 本模块的断点在**本文件**里管理,PROGRESS.md 只记里程碑(开工/每课封版/结业)。
> 教学法细节若有疑问,以 `COURSE-OVERVIEW-v3.md` §三补二(门禁三条)/补三(带着盖楼,勿改)为准。

---

## A. 模块元信息

- **目标**:通过"挖空复现"吃透 **langchain-ai/open_deep_research**(下称 ODR)的 supervisor 多 agent 架构,达到:(a) 面试可深挖(LangGraph 原语、架构取舍、读出过官方 bug);(b) 能脱离源码徒手复现三层图;(c) 在其上做出至少一个有据可依的扩展。
- **源码**:本地克隆 `E:\Agent\open_deep_research`(shallow,2026-08-11)。核心 5 文件:
  `src/open_deep_research/{deep_researcher.py(719行主战场), state.py, configuration.py, prompts.py, utils.py}`
- **复现代码**:本目录 `src/deep_research/`,**镜像源码文件布局**,便于逐文件 `git diff --no-index` 对照。
- **LLM**:DeepSeek 为主 —— `init_chat_model("deepseek:deepseek-chat")`,key 走仓库根 `.env` 的 `DEEPSEEK_API_KEY`。**R0 需 `uv add langchain-deepseek`**。个别环节(结构化输出不稳)可临时切 OpenAI。
- **搜索工具**:R0 课上先确认用户的 Google key 类型:
  - Google **Custom Search**(API key + CX)→ 自写 `google_search` 工具(顺便练自定义工具接入);
  - 只有 **Gemini** key → 主线回退源项目默认的 **Tavily**(免费注册),Gemini native grounding 降级为 R6 扩展⑥;
  - 都没有 → Tavily。
- **与主课程的关系**:阶段三 capstone 的**前置专题**;R6 扩展②(Langfuse)与 L13 主题重叠,完成可部分抵扣 L13;扩展④⑤分别回扣 L12(评估)、L10(MCP)。
- **产出定位**:结业后本目录可独立包装为求职作品(README + DESIGN + ADR + 测试 + 与源码的 diff 复盘文档)。

## B. 教学法约定(每课固定五步)

1. **讲解**:当课概念 + 源码对应段落导读(源码行号见 C 表)。
2. **出骨架**:我生成当课文件骨架——完整 imports、函数签名、docstring(输入/输出/行为契约)、编号 TODO(`# TODO(R1-3): ...`),**每课 TODO ≤10–12 个,集中在一个文件**;同时给 `tests/test_rXX.py`(≥1 happy + ≥1 failure path),鼓励 TDD:先跑红再填绿。
3. **用户填空**:用户写函数体,我只答疑不代写;卡住时给渐进提示(方向 → 伪码 → 关键行),不直接给答案。
4. **对照源码 diff 复盘**:`git diff --no-index src/deep_research/<file> E:\Agent\open_deep_research\src\open_deep_research\<file>`,逐差异讨论"谁更好、为什么";用户版更好的地方记入 findings,源码更好的地方改进用户版。
5. **quiz + 封版**:quiz 考推导不考背诵(3–5 题);**门禁三条**(①环境可复现 ②pytest 绿含正反用例 ③无调试残留)全过才封版;封版动作 = notes.md/quiz.md/summary.md(→pdf)+ 更新 `interview-notes.md` + 更新本文件 F 区 + commit。

**节奏铁律**:一课封版后停下等用户开口;答疑不催进度;quiz 未过不硬推进度,补讲后重出变式题。

**commit 规范**:`R<N> 封版: <一句话交付物>`;非封版 `决策留痕: ...` / `进度: ...`。默认只 commit 不 push,commit 后问一句是否顺手 push(两机同步需要)。

## C. 课程路线(MVP 纵切螺旋:每课结束都有能跑的东西)

| 课 | TODO 主战场 | 核心考点 | 对照源码(`src/open_deep_research/`) | TODO 预算 |
|---|---|---|---|---|
| **R0 蓝图与环境**(半节) | 共创 `DESIGN.md`;`uv add langchain-deepseek`(+搜索依赖);确认 Google key;写 smoke test(DeepSeek 调通一次) | 三层图全景;四模型角色分工;与 stage2 capstone 架构对比 | `README.md` + 架构图 | ~2 |
| **R1 Researcher 纵切 MVP** | `state.py`(Researcher 部分)+ `deep_researcher.py` 之 researcher / researcher_tools / 子图编译;**fake search 先行**(拔网线能跑) | `StateGraph`、`Command(goto+update)`、`bind_tools`、reducer=`operator.add`、ReAct 预算 `max_react_tool_calls`、`asyncio.gather` 并发执行工具 | `deep_researcher.py:365-509`、`state.py:83-96` | ~9 |
| **R2 压缩与上下文隔离** | compress_research + `ResearcherOutputState`(子图 output schema)+ token 韧性(`remove_up_to_last_ai_message`);真搜索接入(Google/Tavily 落地) | context isolation(子图为何只吐 compressed_research)、token 超限跨 provider 检测、压缩重试丢旧保新 | `deep_researcher.py:511-605`、`utils.py:599-886` | ~7 |
| **R3 Supervisor 与并发派活** | `state.py`(Supervisor 部分 + `override_reducer`)+ supervisor / supervisor_tools;`ConductResearch`/`ResearchComplete` Pydantic 工具协议 + think_tool;`asyncio.gather` fan-out 子图;超发教育性报错;三重预算 | 自定义 reducer 双语义(append/override)、Pydantic-as-派活协议、**gather vs `Send` API 取舍**、think_tool=显式反思 | `deep_researcher.py:178-363`、`state.py:55-81` | ~10 |
| **R4 主图与端到端** | clarify_with_user / write_research_brief / final_report_generation(渐进截断:上限×4 字符,后每轮 −10%)+ 主图组装;**第一次全流程真跑**,产出一份真报告存 `runs/` | `with_structured_output`+`with_retry`、一次调用拿分支两侧产物(ClarifyWithUser 三字段)、override 清状态、入口/出口 state schema | `deep_researcher.py:60-175, 607-719` | ~8 |
| **R4.5 prompts 精读**(30–60 分钟,不挖空) | 无 TODO。精读 `prompts.py`:supervisor 如何被教会"何时并行何时串行"、压缩 prompt 如何要求保留原文引用 | prompt 工程:结构化指令、few-shot 边界、"以研究简报为唯一事实源" | `prompts.py` 全文 | 0 |
| **R5 配置层与总复盘** | `configuration.py` 全接线(`from_runnable_config`、env>configurable 覆盖顺序);全项目 diff 复盘写 `findings.md`;**修 `or True` bug 并写回归测试** | `RunnableConfig` 传播机制、x_oap_ui_config 的作用;"我读出了官方仓库的 bug"面试素材 | `configuration.py` 全文;bug 在 `deep_researcher.py:334` | ~6 |

> **prompts.py 特殊处理**:R1 起直接从源码复制(手抄 21K prompt 无教学价值),R4.5 专课精读,quiz 考设计意图不考默写。
> **utils.py 特殊处理**:搜索工具、MCP/OAuth、token 检测等 ~900 行大部分**给现成**;用户只写当课考点相关的少数函数(R1 的 think_tool、R2 的 remove_up_to_last_ai_message 等)。

### R6+ 扩展选单(结业后用户挑,每个一节,TODO ≤10)

| # | 扩展 | 价值 / 回扣 |
|---|---|---|
| ① | `SqliteSaver` checkpoint + `interrupt()` 人工审批 research brief | 补源码缺失的持久化与 HITL;LangGraph 招牌特性 |
| ② | Langfuse tracing 全链路接入 | 抵扣 L13 可观测主题;已有 Langfuse 账号 |
| ③ | 用 `Send` API 重构 fan-out,与 gather 对比写成 **ADR-002** | 面试高频:两种 fan-out 的 checkpoint/错误隔离差异 |
| ④ | mini eval:LLM-as-judge 评报告质量(拿 3–5 个题目跑对比) | 回扣 L12 评估体系;呼应源码 tests/ 的 Deep Research Bench |
| ⑤ | 接一个 MCP 工具作为 researcher 的额外工具 | 回扣 L10 MCP;源码 utils.py 有完整参考实现 |
| ⑥ | Gemini native grounding 作为第四条搜索路径 | 仅当用户 Google key 为 Gemini 时;对照源码 openai/anthropic 原生搜索的实现模式 |

## D. 骨架生成规范(给未来 session 的我)

- 骨架 = 完整 imports + 函数签名 + docstring(行为契约:输入、输出、边界情况)+ 编号 TODO 注释;函数体只留 `raise NotImplementedError` 或 `...`。
- TODO 注释格式:`# TODO(R3-7): 把超发的 ConductResearch 调用转成教育性报错 ToolMessage(提示最大并发数)`——写清"做什么",不写"怎么做"。
- 源码有坑处标 `# ⚠️ 源码此处有坑,先按你的直觉写,diff 时再讨论`(如 R5 的 `or True`、compress 原地 append 污染 state)。
- 每课测试先行:`tests/test_rXX.py` 用 fake ChatModel(`langchain_core.language_models.fake_chat_models.GenericFakeChatModel` 或自写 stub)隔离网络——延续用户"拔网线也能跑绿"的纪律;真 API 冒烟测试单独放 `tests/smoke/` 并标 `@pytest.mark.smoke`,默认不跑。
- 运行方式:在本目录 `uv run pytest`(monorepo 分目录隔离,根 pytest 配置已 norecursedirs)。
- 不确定用户是否达标时,看的是:能否**先于我**说出某段设计的动机;quiz 变式题正确率;diff 复盘时能否为自己的写法辩护。

## E. 五级对照(本专题内的达标定义)

- **Beginner**:能解释三层图逐节点职责,跑通 R1 MVP
- **Intermediate**:独立完成 R1–R4 全部 TODO,quiz 全过
- **Advanced(本专题终点)**:diff 复盘能指出源码优劣各 ≥3 处;修掉 `or True` 并论证影响面;完成 ≥1 个 R6 扩展并讲清取舍
- 不追 Expert(那是"给 ODR 提 PR 被合并"的级别,可作为可选彩蛋:`or True` 修复值得试投 upstream)

## F. 断点交接区(append-only,每 session 结束必更新)

### 2026-08-11 · 模块开工
- **已完成**:选型定案(ODR)、源码全文摸底(讲解存于对话,要点见 PROGRESS.md 里程碑记录)、本流程文件、目录骨架、PROGRESS/ROADMAP 挂接。
- **课程状态**:R0 未开始。
- **下一步第一件事**:用户说"开始 R0"后——共创 DESIGN.md(先让用户凭记忆画三层图,再对照源码图纠偏)→ `uv add langchain-deepseek` → 确认 Google key 类型定搜索方案 → smoke test。
- **软信息**:用户已通读过我的 ODR 架构讲解(三层图/reducer/gather fan-out/or True bug),R0 讲解可快进,重点放在"凭记忆复述"检验;用户 LangGraph 经验=stage2 的 agent_langgraph.py 单图重写(L9),**没写过子图和自定义 reducer**——R1/R3 是真正的新知识。

### 2026-08-11 · R0 封版 ✅
- **交付物**:DESIGN.md 定稿(含搜索选型=Tavily)· `lessons/r0/{notes,quiz,summary}.md + summary.pdf` · `tests/smoke/smoke_r0.py` 两条依赖验通 · interview-notes 新增「十四、ODR 复现专题」。
- **依赖**:`langchain-deepseek==1.1.0`、`langchain-tavily==0.2.18` 已入 pyproject;`TAVILY_API_KEY` 已入 .env(用户 Google API 确认不可用)。
- **quiz**:3/3(Q3"推理模型分配"初答方向反——把"重要"当理由;补讲"决策密度×调用频率"框架后变式题秒对)。
- **软信息(R1 教学要注意)**:
  - "改一半/漏 return"再犯(Tavily smoke 返回占位符)——已立规矩"写完回读契约再跑",R1 每个 TODO 验收时**主动问他有没有做这个动作**。
  - 蓝图复述:主图结构一次全对,循环退出条件需支架才推出——结构记忆好,**机制推导是薄弱点**,R1 讲 Command 路由时多用"你觉得为什么"少用陈述。
  - smoke 用了 `deepseek-v4-flash`(推理模型);四角色正式选型 R4 讨论,别忘。
- **下一步第一件事**:用户说"开始 R1"后——生成 `src/deep_research/state.py`(Researcher 部分)+ `deep_researcher.py` 骨架(researcher / researcher_tools / 子图编译,~9 TODO)+ `tests/test_r1.py`(fake ChatModel,1 happy + 1 failure);fake search 工具我给现成放 utils.py。先讲 30 分钟:Command 路由 / bind_tools / reducer=operator.add,再放手写。

### 2026-08-11 · R1 封版 ✅(quiz 欠账,见下)
- **交付物**:researcher 子图全绿(10 TODO 全亲手,`tests/test_r1.py` 4/4,假模型离线跑)· `lessons/r1/{notes,quiz,summary}.md + summary.pdf` · interview-notes「十四」新增 R1 六条。骨架含脚手架:conftest.py、极简 configuration.py(R5 推倒重建)、prompts.py 源码原样复制、compress_research 占位节点。
- **⚠️ quiz 未亲答**:当天课末信息量到顶("有点懵"),四题由教练讲评("今天我负责记忆")。**R2 开工第一件事:出 4 道变式题(Q1 动态边声明 / Q2 reducer 删除推演 / Q3 think_tool vs reflect / Q4 计数点位置),过了 R1 quiz 才关闭,再开 R2**。热身题战绩:Q1 对一半,Q2 方向对机制错(误用 token 论证)。
- **首跑六类错(变式题出题素材)**:①`configurable_model = ...` 遮蔽全局(函数内赋值=局部判定,最深的坑)②with_retry 位置传参 ③Configuration 字段名想当然 ④reducer 交全量→翻倍膨胀(手动跑表 3→7 推醒的),修对后又写出不存在的 `response.messages` ⑤Command 位置传参 ⑥tool_calls 元素当对象访问。
- **软信息(R2 教学要注意)**:
  - 学习者主动要过标准答案(R1-8)和整体串讲两次——**吸收型学习倾向增强,警惕替代亲手推导**;R2 出骨架后先让他复述"这课要造什么"再动笔。
  - 高光:自己推出"删 reducer 后交全量与现状等价"(教练补:并发下碎裂)——机制推导在进步,但要在**新知识**上验证。
  - "回读契约"习惯本课两次见效(③号错自己抓出);继续在每个 TODO 验收时问。
  - configuration.py 默认模型被他改成 `deepseek-v4-flash`(推理模型)——四角色选型 R4 讨论时收账。
- **findings 候选(R5 汇总)**:①重复 get_all_tools 属低危缺陷,修法=utils 层记忆化(按影响工具箱的配置字段做 key);②"覆盖+全量单线等价、并发碎裂"论证;③`max_react_tool_calls` 名不符实(数模型轮数)。
- **下一步第一件事**:用户说"开始 R2"(或"继续 ODR")后——先 4 道变式题关闭 R1 quiz → 讲 compress_research 真实现 + `ResearcherOutputState` 防火墙(`output=` 参数)+ token 韧性(`remove_up_to_last_ai_message`)→ 真搜索 Tavily 接入。对照源码 `deep_researcher.py:511-605`、`utils.py:599-886`,~7 TODO。

### 2026-08-12 · R1 quiz 关账 ✅(变式题 4/4)
- 学习者次日主动补账。战绩详录在 `lessons/r1/quiz.md` 文末附表。要点:Q4' 三问秒对;Q1'/Q2' 均"结论对、机制表述错"(把覆盖语义说成 reducer、给裸 dict 节点脑补了 Command)——**R2 验收口令:说结论必带机制**。
- 补账前学习者主动要求复核概念并两次给出自己的复述(ResearchComplete 声明/响应两半、Command 注解层 vs 实例层)——复述质量高,吸收型转主动输出的好迹象。
- 新增 R5 辩题素材:researcher 的 goto 恒定却用 Command(源码风格统一 vs 最小权力原则)。
- **下一步第一件事**:用户说"开始 R2"后直接开讲(quiz 债已清):compress_research 真实现 + `output=ResearcherOutputState` 防火墙 + token 韧性 + Tavily 真搜索。对照源码 `deep_researcher.py:511-605`、`utils.py:599-886`,~7 TODO。

### 2026-08-14 · R2 封版 ✅(quiz 4/4 亲答满分)
- **交付物**:ResearcherOutputState 防火墙(用户自升 `output_schema`/`context_schema` 新参数名)· compress_research 真实现(模式切换+3 重试+截断+降级)· remove_up_to_last_ai_message · get_all_tools 按 search_api 切 Tavily/fake · 10/10 测试绿(R1 四条改道 raw_notes 审计通道)· `tests/smoke/smoke_r2.py` **researcher 子图首次真跑成功**(DeepSeek+Tavily,raw_notes 32,138 字符)· `lessons/r2/` 四件套。
- **quiz**:4/4 亲手一次过,全部带机制带行号(对比 R1 讲评代过——推导能力跃升,"说结论必带机制"口令退役)。Q4 主动答出"bug 上游存活三层掩体"。
- **findings 池(R5 汇总)现四条**:①`or True`(334)②原地 append 污染 state(538)③嗅探传 research_model 错位(569)④max_react_tool_calls 名不符实。其中②③我们的复现版已修——"读出并修掉官方仓库两个坑"是成型的面试素材。
- **软信息(R3 教学要注意)**:
  - **TODO 分组交付 + 每组先讲调用链定位**是用户明确要求的新模式(A→B→C→D 过一组开一组),R3 沿用;**批量文件改动走后台 agent,对话零 diff**(用户强反馈,已入长期记忆)。
  - R2-5(重试循环)是**教练代写**(用户要求),已经 quiz Q2 反事实推导验证消化——但 R3 骨架难度应回归全亲手。
  - 用户 quiz 水平跃升(带行号引证、主动答未问的问题)——**变式题难度可以提**;其 Q3 方案 B(裁剪+教育性回执)恰是 R3 超发教育的雏形,开讲时回接。
  - configuration 默认 research_model=deepseek-v4-flash(推理模型)系用户自选,四角色选型 **R4 收账勿忘**;summarization 摘要管线欠条也在 R4。
- **下一步第一件事**:用户说"开始 R3"后——supervisor 子图:`state.py` Supervisor 部分(SupervisorState + override_reducer + ConductResearch 协议)+ supervisor / supervisor_tools 节点 + `asyncio.gather` fan-out 子图 + 超发教育性报错 + 三重预算。对照源码 `deep_researcher.py:178-363`、`state.py:55-81`,~10 TODO 按分组交付(建议:A 状态与协议 → B supervisor 节点 → C supervisor_tools 拦截与 fan-out → D 预算与超发教育)。
