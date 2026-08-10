# 学习进度：Agent 开发

## 会话启动流程（每次开工必做）
- **第一件事：`git pull` 拉最新代码**。用户在 macOS / Windows 两台机器上学，共用 B6nux9
  同一个远端仓库。不先 pull 就动手，两机会产生分叉/冲突。
- 拉完再读本文件确认断点，然后按「下一步」行动。
- 收尾照旧：commit 后 `git push` 到 B6nux9，让另一台机器下次能 pull 到。

## 课程元信息
- 路径：**分级(tiered)**
- 目标终点等级：**Advanced（第 4 级）** —— 能独立设计并搭出 production 级客服 agent，
  懂每个组件的权衡，在面试里讲透细节。不追 Expert。
- 起始日期 / 最近更新：2026-07-13 / 2026-07-28（**阶段二 capstone 第三轮 build 第一次坐下：盖完 4 块、端到端 4 场景跑绿**）
- 默认模型：**DeepSeek**（`deepseek-chat`，OpenAI 兼容，写法可迁移通义千问/GPT）
- 环境：conda 环境 `agent`，Python 3.12
- 仓库（**用户在两台机器上学，按当前系统判断路径**）：
  - **macOS**：本地 `/Users/el4435/learning-agent-development/`
  - **Windows**：本地 `E:\Agent\learning-agent-development\`，conda 环境路径 `E:\Anaconda\envs\agent`
  - 远端私有 https://github.com/B6nux9/learning-agent-development （**所有课程统一存 B6nux9 账号**，两机同步）

## 学习者画像（来自开课摸底，续学时别再重复问）
- **已有基础**：会写 Python、调过大模型 API、懂 LLM 原理。但**代码/工程基本功偏弱**，
  尤其 Python 环境管理是明显短板。
- **目标与动机**：为**国内求职**而学，特别看重项目细节与落地（客服场景），想解决真实
  工作痛点，尤其关注**上下文长度管理**。
- **时间投入**：每周 5–10 小时。
- **学习偏好**：边做边讲、理论实践平衡；**不想直接看答案**（coaching 式，给提示不给答案）。
  🆕（2026-07-27 更新）作业方式从"纯填空骨架"升级为**"带着盖楼"引导手写**：先讲多文件蓝图，
  再从空文件一小块一小块带着写，重在建立**整体代码结构**的理解。详见 `COURSE-OVERVIEW-v3.md` §三·补三
  与下方「🔴 教学标准变更②」。

## 课程大纲与进度
- [x] **L1 什么是 agent** —— 已完成，达标（quiz 5/5，跑通 hello_llm.py）
- [x] **L2 手写 agent loop** —— 已完成，达标（作业 order_agent.py 跑通：单/双订单查询 + 「几点下班」不调工具直接答；quiz 5/5）
- [x] **L3 tool use 深入** —— 已完成，达标（作业 refund_agent.py 跑通：多工具/链式退款/错误回传/循环上限；quiz 3满分+2需补全）
- [x] **L4 多工具编排** —— 已完成，达标（讲义/quiz 5满分；**阶段一 capstone `cli_agent.py` 跑通**：
  分组路由 order/refund/account + 会话内多轮记忆 + LLM-as-router；关键词法与 LLM 法两版都验证）
- [x] **阶段一 capstone** —— 已完成（命令行多工具客服 agent，L2~L4 综合）
- [x] **L5 记忆与状态** —— 已完成，达标（quiz 5/5；作业 `agent_with_memory.py` 跑通：
  load/save memory.json + 注入 system prompt + `remember` 工具，**分两次运行验证跨重启记忆**）
> **⚠️ 大纲已于 2026-07-21 按 11 份目标岗位 JD 重排**。完整分析见
> [`Requirements/JD分析与大纲调整.md`](Requirements/JD分析与大纲调整.md)（含频次统计表、gap 分析、两个战略决策）。
> 求职定位：**校招/应届为主（在校生），社招兼顾**（2026-07-29 用户确认，原写社招）。JD 原文存 `Requirements/`。
> **🆕 新增 4 个百度校招高优先岗**（`Requirements/百度2027校招-Agent岗位4则.txt`：AIDU 全栈/**Agent Harness**/智能体算法/大模型研发；JD3 要硕士；加分=论文/开源/竞赛）。
> **技术融合（详见 [ROADMAP.md](ROADMAP.md)）**：① L8 补 **Reflection 反思**范式(capstone reflection 节点)；② L9 从只学 LangGraph **扩成横扫 LangChain/LlamaIndex/AutoGen/CrewAI 定位 + ADR 对比**；
> ③ 新增 **L13.5 Agent Harness 专题**(沙箱/执行约束/上下文交接/compaction/长任务稳定，Claude Code 锚点)；④ 研究向(书 Ch5/7/8/9=Coding/RL/self-improvement/多模态)从长期作战**上调为校招加分，投递前尽量碰**；⑤ 加分项(开源贡献/竞赛)纳入。

### 🔵 阶段二：核心能力补齐（投递前必做）
- [x] **L6 上下文管理 + Prompt/Context Engineering** —— 已完成，达标（quiz 6 题过；
  作业 `homework/v2/` 端到端跑通：阈值触发压缩、13 单测通过、真实会话验证跨压缩记住用户名）
  - 讲授：平方级增长、lost in the middle、上下文=预算表、四类策略；Prompt 五块骨架 +
    别用模糊限定词 + 点名禁失败模式；结构化输出三层次（补缺口 2）。
  - **两个尾巴并入阶段二 capstone**（见「阶段二 capstone 待办」）：
    ① Part B 结构化输出路由（缺口 2 的动手部分，只讲了没写）
    ② 单元测试系统学习（v2 测试由教练代写，用户当时选择先专注实现）

#### L6 作业最终状态（已封版）
`lesson-06/homework/` 下两套：
- `context_manager.py`（v1）= 参考实现，带 `【改】` 注释记录踩坑，**勿再让他做**。
- `v2/`（正式作业，已完成）三文件分层：`context.py`（纯逻辑，用户实现）、
  `test_context.py`（单测，教练代写，13 通过）、`agent.py`（接线层）。
  端到端验证过程见 `lesson-06/summary.md` 第五节（9 条实战道理，全部已进 interview-notes）。

### 🔴 教学标准变更（2026-07-22 用户明确要求，最高优先级）
> **"在后面的课程学习中，尽量保持生产环境的规范。estimate 还是有点太简单了，
> 不符合我们找工作准备面试的目标。"**

起因：L6 作业里我用 `len(content)//2` 估算 token，他立刻指出太幼稚——**而且它确实漏算了
工具 schema（每轮几百 token），是系统性偏低**。已改用 `response.usage.prompt_tokens`。

**执行要求（本机记忆 `production-grade-teaching` 同步不到 Mac，故记在此）：**
- 默认给**生产级写法**，不要为降低难度而教玩具实现。
- 确需简化时，**明说"生产环境会怎么做、差距在哪"**，别让简化版悄悄变成他的认知。
- 他问"真实项目怎么做"时，要给**具体方案对比 + 选型判断**，不能只答概念。
- 理由：唯一目标是**国内社招求职**，玩具写法写进简历会在面试追问时穿帮。

### 🔴 教学标准变更②（2026-07-27 用户反馈，最高优先级）：作业改"带着盖楼"
> 起因：L8 单节太重（3 文件、25 个 TODO、Part A→B→C 跨文件链式依赖），用户花 ~5h 做完仍
> 沮丧。复盘（本 session）发现真正短板是**多文件项目"怎么拼成整体"的心智模型缺失**，
> 不是作业量。用户明确：**不要**简化成单文件（真实工程就是多文件），而要**少填空、多带着从头写**。

**执行要求（权威版在 `COURSE-OVERVIEW-v3.md` §三·补三；本机记忆同步不到另一台机，故也记这）：**
- **量级**：每节作业 TODO/填空 ≤ ~10–12，尽量单个主文件，**严禁跨文件链式依赖**；要多文件
  就用测试门禁切成可**独立验证**的小段，一段封绿再上一段。
- **蓝图先行**：动手前先讲清做什么 agent、拆几个文件、每个文件职责/边界、写作顺序为什么
  （由内向外），给可复用结构模板"①工具层→②核心循环→③编排层→④入口/实验→⑤测试"。
- **带着盖楼不填空**：一小块一小块，每块先讲"是什么/干嘛/为什么在这个文件这个位置"，
  用户从**空文件**自己写函数体；教练只给**接口契约**（签名+输入输出+约束），不替他填实现。
- **纵切+早反馈**：先打通最小可跑链路让他看到东西转起来、看清文件间如何互调，再逐层加厚。
- **重头戏节**（capstone 级）提前标注更大预算、拆 2–3 次坐下完成，对齐预期。
- **L8 已按新法补做了一次架构复盘**（本 session）：带他把 tools/executor/planner 三文件的职责、
  边界、依赖方向、写作顺序、"纯逻辑 vs 接线"分层过了一遍，用户已理解。**L9 起正式用此法。**

- [x] **L7 RAG 与向量数据库** —— 已完成，达标（quiz 3题过；作业 `rag.py` 端到端跑通：
  切块+OpenAI embedding+ChromaDB+grounding；口语/近义命中、库外问题 grounding 挡幻觉；
  **亲手验证 chunking 决定 RAG 上限**：固定窗口 vs 按标题切对比，检索与答案质量都上台阶）
- [x] **L8 路由 / ReAct / Planning** —— **已完成，达标，已封版**（JD 6/10）
      讲授 ✅ · quiz ✅ · 作业 25 TODO 全完成 · **11 测试全绿** · Part C 对比实验跑通 · findings.md 定稿 ·
      summary.pdf 出好 · interview-notes 补齐。门禁三条全满足。详见文末「L8 封版记录」。
- [x] **smolagents CodeAgent 锚点** —— 已完成（三引导问题全答透，三栏笔记 `anchor-notes/L8-smolagents.md` 已落笔，
      第③栏已摘进 interview-notes）。用户吃透「JSON tool-calling vs CodeAct」两范式取舍。
- [~] 🎯 **阶段二 capstone（用户主动提前开工）** —— 设计面两轮通过 + **第三轮 build 盖完 4 块跑绿**（见下方「阶段二 capstone 进度」）　← **当前断点**
- [ ] **L9 主流框架：用 LangChain 重写项目** ——（JD 6/10，**从 L14 大幅前移**；简历关键词。capstone 裸 SDK 版做完后进）
      （v3 L9 改法：同一有界工作流用裸 SDK vs LangGraph 两版对比 → 产出 ADR）
- [ ] **L10 MCP 协议** ——（JD 4/10，**新增**；2025-26 热点，面试常问）
- [ ] 🎯 **阶段二 capstone：简历级客服 Agent 项目**（最重要产出，直接写进简历）
      **capstone 待办（含 L5/L6 遗留）**：
      - remember(L5) + 上下文压缩(L6) + RAG(L7) 三者合成完整客服 agent
      - **L6 Part B：结构化输出路由**（用 `response_format` json_schema 重写 L4 的 route_llm，
        缺口 2 的动手部分，只讲了没写）
      - **单元测试系统学习**（L6 的 v2 测试是教练代写的，capstone 里让他自己写）

### 🟢 阶段三：工程化与求职冲刺（投递前做完）
- [ ] **L11 Multi-Agent 多智能体协作** ——（JD 5/10，**从 L13 前移**；是 L4 编排的自然延伸）
- [ ] **L12 评估体系** ——（对标蔚蓝 JD：工具调用准确率、任务完成率、响应延迟）
- [ ] **L13 可观测性、成本与延迟** ——（对标拼多多 JD：成功率、延迟、Token 消耗、业务转化率）
      **⚠️ 必须包含「API 调用层的重试 / 超时 / 限流(429)」**（补 L1-L5 缺口 4）：L3 只学了
      **工具报错**的处理，**API 调用本身失败**（超时、限流、网络抖动）完全没碰过，是生产必备。
- [ ] **L14 服务化与部署：FastAPI + Docker** ——（决策 1 的"最小量"；含 Agent 安全基础：
      权限控制、输出过滤、高危操作二次确认；以及优雅降级/熔断这类稳定性兜底）
- [ ] 🎯 **阶段三 capstone：项目上线 + 简历/面试包装**

### ⚪ 长期作战（第一轮投递后继续）
- [ ] 高并发与分布式深化 · RLHF/RL 后训练深水区（**SFT 已于 2026-08-10 用户拍板提前**，见文末优先级清单） ·
      多模态 · KV Cache/vLLM 推理优化 · Agent 安全深水区(沙箱执行) · 前沿跟踪

- capstone 状态：阶段一 ✅ 已完成；阶段二/三 未开始
- **时间估算**：阶段二 5 节 + 阶段三 4 节 ≈ 9 节 × ~3h + 两个 capstone ≈ **50 小时**；
  按每周 5-10 小时 → **5-10 周**，落在 1-3 个月窗口内，可行但要保持节奏。

## 当前掌握等级评估
**Intermediate 稳步推进（阶段二进行中，已完成 L5/L6/L7/L8）**。L8 亮点：能独立把玩具 loop 升级成
生产级 executor（显式终止语义、纯逻辑可测、结构化日志），能设计并跑通 ReAct vs P&E 对比实验、
并从三个被打脸的 expectation 里提炼出正确权衡（"扇出目标运行时发现 vs 规划期定死"、
"光看 token 会把失败读成高效"）。工程判断力持续上台阶（stop_reason 可观测性判据、度量口径修正）。
**头号短板"改一半/漏 return"仍是最顽固项，本节又犯 4 次。**除阶段一能力外，已掌握长期记忆存取闭环、
上下文压缩（阈值触发/混合策略/切点安全）、Prompt 工程、结构化输出，并能把逻辑拆成**可测的纯模块**。
**L6 亮点：几乎全程自驱 debug**——阈值 thrashing、反复摘要衰减、模型可用性、`-`vs`_` 一字之差，
都是他跑出来撞明白的。**工程判断力明显上台阶**（会追问"生产环境怎么做"、主动要求对齐生产规范）。
**仍需盯的短板**：多部分任务只做一半（L3 漏兜底 return、L5 漏空分支、L6 __init__ 校验了没存值——
**同一模式第 3~4 次**，已反复叮嘱"看到 TODO 里有'并/、'连接的多动作，做完数一遍"）。
**本节高光：一次真实 debug 全程自驱**——LLM 路由静默失灵→加 `repr` debug print→看到 `content=''`
→定位到「思考型模型 `deepseek-v4-flash` 被 `max_tokens=5` 饿死」→换非思考模型 `deepseek-chat` 修复。
工程 debug 直觉明显在长。
工程细节意识在增强（兜底代码、调试残留），但仍是相对短板：L3 作业里 ①漏写兜底 return（只写计数）
②测试用的 `MAX_TURNS=0` 忘改回 8 导致 agent 罢工。已叮嘱**养成 commit 前 `git diff` 扫一眼**的习惯。
环境问题（哪个 python/包装哪了/key 在不在）已能用 `sys.executable`/`conda info --envs`/`echo $KEY` 自查，
且已把 DEEPSEEK_API_KEY 写进 macOS `~/.zshrc`(理解了 env 变量属 shell 会话、conda 不隔离它)。

## 关键软信息（下个 session 尤其要知道的）
- **反复卡住/易错**：Python 环境管理（哪个 python、包装哪了、conda 环境是否有 python）。
  真实开发中要持续帮他留意这类问题。
- **已很扎实、可略过**：agent 是什么、loop/tool/memory 四部件、不该用 agent 的判断。
- **学习者的高光直觉**（值得在后续课程呼应）：
  - task A 里自问"客户的问题是否需要模糊处理" → 正是 **L7 RAG/向量检索**要解决的，届时点回来。
  - task A 里"QA 查不到就转人工"的兜底逻辑 → 客服 agent 的安全设计，L8/L10 呼应。
  - **L2 里自己追问出**："LLM 无持续连接、追问会忘、messages 越滚越长" → 提前推到了 **L5 记忆**
    与 **L6 上下文**，届时明确点回来"这就是你 L2 就想到的问题"。
- **L2 已扎实、可略过**：function calling 四步握手、agent loop 骨架、TOOLS schema 各字段含义、
  "模型决策 / agent 本地执行"的分工、无状态 API 心智模型。
- **L3 已扎实、可略过**：多工具 description 路由、"错误也是信息"(try/except→error JSON 回传→模型自愈)、
  链式调用是 loop 涌现的(零新代码)、循环次数上限兜底、"agent 能力来自工具不来自 loop"这一抽象。
- **L3 埋的伏笔**：30 工具会带来①选择困难②schema 每轮吃 token 撑大上下文 → L4 工具编排/分组、
  进阶"按需检索工具"(思路同 L7 RAG)。学习者 Q5 只答出①,②(schema 占上下文)是我补的,L4 可回扣。（L4 已回扣完）
- **L4 已扎实、可略过**：模型编排 vs 代码编排/路由、"可靠性来自约束"、静态分组(共享底座+场景增量)、
  LLM-as-router 模式及其 4 坑(约束输出/temperature=0/max_tokens/校验兜底)、会话内多轮记忆(累积 messages)。
- **L4 埋的伏笔（务必回扣）**：①capstone 的多轮 messages = 会话内记忆 → **L5** 讲边界(越滚越长/跨会话)；
  ②schema 吃 token + messages 膨胀 → **L6** 正式收；③tool RAG(按需检索工具) → **L7**；
  ④高危操作(改密码/注销)光分组不够，要二次确认/权限 → **L10**；⑤主模型是思考型，延迟调优时回扣。
- **本节暴露/仍需盯的工程点**：①`route_keyword` 改名时把函数体整段注释掉→隐式 return None(切开关会 KeyError)，
  是"改一半"的残留；②`messages` 混血列表(dict + SDK 对象)访问方式不统一→AttributeError；
  ③fallback 会掩盖 bug，调试期要用 `repr`/`!r` 打出兜底前真实值。这些都属"工程基本功"短板，持续留意。
- **L5 已扎实、可略过**：短期/长期记忆与状态三分("记忆给模型看，状态给代码用")、长期记忆=存+取闭环、
  为什么注入 system 而非伪装 user 消息、`remember` 工具让模型自己决定何时存。
- **L5 两次翻车（都是高价值教训，后续要反复呼应）**：
  ① **漏写兜底 return（惯犯！L3 已犯过一次）**：`build_system_prompt` 只写 `if memory:` 那支的 return，
     空 memory 时静默返回 `None` → API 报 `content should be a string`。已叮嘱自查动作：
     **写完带返回值的函数，扫一眼每个分支是否都 return**。**这是他最顽固的短板，下次仍要盯。**
  ② **模型"嘴上说做了、其实没调工具"**：模型回"我已经记下了😊"但 `memory.json` 不存在，
     `remember` 从未被调用。靠 ①查物证(文件) ②打印真实 `tool_calls` 才发现。
     治本=**prompt 太软**，改强命令并点名禁掉偷懒话术("绝对不要只嘴上说'已记住'却不调用工具")。
     → **金句：验收 agent 永远看动作(tool_calls)，不看话术。** L11 可观测性回扣。
- **Windows 环境变量（L5 踩坑，已解决）**：永久设 key 用
  `[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY","sk-...","User")`；
  **关键坑：VSCode 启动时就把环境变量拍了快照**，改注册表后新开终端标签也读不到，**必须完全重启 VSCode**。
  临时救急：`$env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY","User")`。
- **L6 已扎实、可略过**：上下文平方级增长、lost in the middle、上下文=预算表、四类压缩策略、
  阈值触发惰性优化、Prompt 五块骨架、结构化输出三层次、FunctionCalling=结构化输出、
  纯逻辑/副作用分离 + 依赖注入使代码可测。详见 `lesson-06/summary.md`。
- **L6 关键事实（后续会用）**：
  - **本端点可用模型只有 `deepseek-v4-pro` / `deepseek-v4-flash`**，**无 `deepseek-chat`**！
    （我曾误建议 deepseek-chat 导致 400。模型名以端点为准，`client.models.list()` 可查。）
  - 摘要器这类"低频但质量关键"的活可用 `deepseek-v4-pro`；主对话/路由用 `deepseek-v4-flash`。
  - `msg.model_dump(exclude_none=True)` 在入口把 SDK 对象归一化成 dict，根治混血列表。
  - 压缩切点：危险的是 **tool** 落在切点上（父 assistant 被切走→孤儿），用 while 退过连续 tool。
  - 压缩阈值必须 > "压缩地板价"，否则每轮都压(thrashing)→ 反复摘要衰减信息（名字会丢）。
- **L6 遗留（并入阶段二 capstone）**：① Part B 结构化输出路由（只讲没写）② 单元测试系统学习
  （v2 测试是教练代写的）。**别忘。**
- **流程改进（本次确立，已存记忆 material-creation-timing）**：三份材料分时创建——notes 讲授时就建、
  quiz 出题时就建、**只有 summary.pdf 等封版才生成**。以后每节照此，别再堆到封版一起做。
- **PDF 生成方式**：
  - **macOS**：无 pandoc/weasyprint；用 base anaconda 的 `markdown` 库转 HTML，再 Chrome headless `--print-to-pdf`。
  - **Windows（L4 本机验证）**：python 无 markdown 库，但有 **pandoc**(`/e/Anaconda/Scripts/pandoc`)。
    流程：`pandoc summary.md -t html5 -s -H 样式头.html -o x.html` → Chrome
    `--headless=new --no-pdf-header-footer --print-to-pdf` 转 PDF（中文用 Microsoft YaHei 字体）。
    Chrome 路径 `C:\Program Files\Google\Chrome\Application\chrome.exe`；file URI 用 `cygpath -w` 转 Windows 路径。
- **途中的决定/调整**：模型定 DeepSeek（国内求职）；工作路径与仓库从 `E:\CAS\展望` 迁到
  `E:\Agent`；GitHub 账号从误用的 el4435 改为指定的 **B6nux9**（el4435 上的旧副本待用户手动删）。

## ⚠️ 课程大纲已升级到 v3（2026-07-26，务必先读）
**权威大纲 = [`COURSE-OVERVIEW-v3.md`](COURSE-OVERVIEW-v3.md)**（两轨版，用户自己评审合并的）。
下面这份 PROGRESS 的大纲章节是 v2 时期的，**遇冲突以 v3 为准**。v3 核心变更：
1. **两轨制**：Core Track（L7→S1→L8→L9→L10→capstone+最小部署）**封版即开始投递**；
   Advanced Track（L11-L14 + PR 支线）边投边学。
2. **工程封版三条门禁**（替代独立工程课，每节强制）：①环境可复现 ②本节作业至少 1 正 1 反
   pytest 用例且绿 ③无调试残留（无 print 残留/死代码/硬编码 key）。**三条不满足不封版。**
3. **[必做] 进作业 / [谈资] 只进 interview-notes**——防课程膨胀，严格执行。
4. **源码锚点机制**：每节在作业与封版之间插 ≤90min 锚点，产出 `anchor-notes/LXX-<项目>.md`
   三栏笔记（它怎么做/我怎么做/差异原因）。锚点池：smolagents、pi(只读)、OpenAI Agents SDK、
   OpenHands、Claude Code。
5. 客服域专项检查表 + 可靠性最小集 + 最小部署 → 都在 Core capstone。

### 🔑 用户已拍板的三条执行决策（2026-07-26）
- **时间**：能稳定 **8h/周** → Core 约 9-11 周，装得进 1-3 个月投递窗口。
- **测试时序**：v3 门禁要求写 pytest，但用户系统学测试排在 capstone。
  → **门禁期由教练搭测试脚手架**（给测试骨架/样板），他补断言；capstone 再系统自己写。
- **评估集**：**已按 v3 补建完成**（见下）。

### 📌 教练对 v3 的两点保留（已告知用户，S1 那条用户未明确回应）
- **S1 解剖 pi 建议降级**：TS 语言、大型陌生库、不能写进简历，Core 里 ROI 最低。
  已按"**读复盘文章 + 教练带过一遍架构图，约 60-90 分钟，不逐包啃 TS 源码**"处理，
  而非原定的一整周。**用户若坚持深挖，开 L8 前会说。**
- **锚点收紧**：只在高 ROI 处做（L8 smolagents、L9 LangGraph），Python 优先、
  指定到具体文件/函数、≤90min。第一个锚点（L8 smolagents）做成模板。

### ✅ L7 增补已完成：RAG 评估集（v3 要求，commit 0a712cd）
- `eval/rag_eval_set.json`：18 条，四分区 normal(9)/unanswerable(4)/out_of_scope(2)/adversarial(3)，
  带 `must_not_contain` 硬红线（防泄露 system prompt、防确认假前提、防越权执行）。
- `eval/run_rag_eval.py`：分类打分卡 + **检索/答案两条正交指标** + 失败明细。
  跑法：`uv run python eval/run_rag_eval.py`。**最终 18/18，检索 11/11。**
- **过程中的高价值教训（已进 interview-notes）**：
  ① 评估集抓到一次**真实回归**——改 prompt 修 a03 时，a02 从"正确纠正"退化成"拒答"；
  ② **三次**撞上"子串匹配无法区分确认与否认"（"7 天"vs"7天"、"而非100天"、"并非秒到"）
  → 这是 L12 上 LLM-as-judge 的依据；
  ③ prompt 分支要按**主题**划而非按**具体说法**划（v1 三条规则边界打架 → v2 两条按主题，18/18）。
- **这份评估集一直养到 capstone 和 L12**，每次改 RAG/prompt 都要跑全套回归。

## 🔶 L8 封版记录（2026-07-27，macOS 续完并封版）

> 状态：**已封版。作业 25 TODO 全完成，11 测试全绿，Part C 跑通，summary.pdf 出好。**
>
> ### 封版当天做完的（2026-07-27，mac）
> - 续 Part A：修 `record_step` 下划线 bug、TODO-3 `should_stop`（budget 优先 + `>=` 边界 + `first and` 排空指纹）、
>   TODO-6 `run_react`（补回被删的 `_normalize` append、决策 2(B) fatal 后不触发副作用）、TODO-7 结构化日志（DRY 重构）。
> - Part B 全写：`PLAN_SCHEMA`（arguments 存 JSON 字符串）、`parallel_groups`（Kahn 分层+环检测+幻觉依赖）、
>   `is_plan_stale`（只做信号①）、`make_plan`（json_schema→json_object 降级 + 解析兜底）、`run_plan_execute`。
>   新增 2 个 StopReason 语义：`INVALID_PLAN` / `REPLAN_EXHAUSTED`。
> - `test_executor.py` 10 个 TODO-T 全补（改对 2 处枚举名 + 3 处 final_answer 语义 + 2 处 fatal 语义）→ 11 绿。
> - **度量修正**：给 `RunResult` 加 `llm_calls` 字段（P&E 的 steps≠模型调用数），两 executor 各自如实计数。
> - Part C 真跑（DeepSeek，json_schema 全程 400 降级 json_object）+ `max_replans=0` 现场 + findings.md 定稿。
> - 门禁三条全过：环境可复现 ✅ / 11 测试含正反 ✅ / 无 print·无死码·无未用 import ✅。
>
> ### L8 关键结论（供后续回扣）
> - **Part C 三个 expectation 全被不同程度打脸**：ReAct 三战全胜或打平；P&E 在扇出任务幻觉翻车
>   （目标运行时发现 vs 规划期定死，时序冲突）；"光看 token/调用数会把失败读成高效"→ L12 LLM-judge 动机。
> - **头号短板"改一半/漏 return"本节又犯 4 次**（record_step 漏下划线、is_plan_stale 漏 return、
>   trace 声明没 append、run_react 删掉了给的 append 行）——已固化 4 条自查动作，下次继续盯。
> - **未做（留 capstone/L13）**：is_plan_stale 信号②（语义矛盾，需 LLM-judge）、worth_planning 回退 ReAct、
>   API 层超时/限流/重试。

### （历史）原 L8 交接细节 —— 2026-07-26 晚
> mac 上开工先 `git pull` 然后 `uv sync`。以下为封版前的进行中记录，已全部完成。

### 已产出
- `lesson-08/notes.md` —— 讲义。**§0「最小记忆集」是后加的**：用户读完说"能理解但记不住"，
  于是把全课压缩成**三个锚点**（①我的 L2 loop 就是 ReAct ②一条轴=重规划频率
  ③自主性是成本不是收益），并演示"表格全部可现场推导"。**后续课程可复用这个手法。**
- `lesson-08/quiz.md` —— 5 题，含参考答案待补（用户已答完，答案未写进文件）。
- `lesson-08/homework/` —— 6 个文件，共 **25 个 TODO**（executor 7 / planner 5 /
  test 10 / compare 3）。`README.md` 里有完整的门禁自检清单。

### 作业进度（`lesson-08/homework/executor.py`）
| TODO | 状态 |
|---|---|
| TODO-1 `LoopGuard.__init__` | ✅ 完成 |
| TODO-2 `record_step` | ⚠️ **写了但有 bug，见下** |
| TODO-3 `should_stop` | ❌ 未做 |
| TODO-4 `_normalize` | ✅ 完成 |
| TODO-5 `_execute_tool` | ✅ 完成（**经三轮 review**，已对齐参考实现） |
| TODO-6 `run_react` | ❌ 未做（**这是最大的一块**） |
| TODO-7 `_log_step` | ❌ 未做 |
| `planner.py` / `test_executor.py` / `compare.py` | ❌ 全未开始 |

### ⚠️ 已知 bug（**已告知用户，留给他自己修，别代劳**）
`executor.py` `record_step` 里 `self.total_prompt_tokens += prompt_tokens`
**漏了下划线**（应为 `self._total_prompt_tokens`）→ 撞上只读 property →
`AttributeError: property 'total_prompt_tokens' has no setter`。
同一个方法里 `self._steps += 1` 却写对了 —— **典型的"改一半/不一致"，头号短板第 6 次**。

### 封版前还欠的（门禁三条）
- 门禁 3：`_execute_tool` 下方**留着一大段注释掉的旧版死代码**，封版前必须删；
  `ToolError` import 了但没用到。
- 门禁 2：10 个测试断言全未补。
- 还欠 `findings.md`（Part C 交付物）。

### L8 教学过程中的高价值观察（写进最终 summary）
- **quiz Q4 的盲区（本节最重要的教学发现）**：给他一段有问题的 loop 找 bug，他找出的
  4 条全是**通用工程问题**（json.loads 在 try 外导致消息序列非法——这条相当漂亮，
  比教练预设的还细；无步数上限；result 不保证是 str；上下文无限增长），
  但**本节刚讲的 4 条一个没提**（stop_reason 枚举 / fatal 分流 / no-progress / print 残留）。
  → 结论：**他的通用工程直觉在长，但"刚学的东西还没变成扫代码的检查清单"**。
  后续出题可继续用这个手法验证。
- **`_execute_tool` 三轮迭代是本节最好的一段教学**：v1 只写 2 条路径 → 指出
  `ensure_ascii=False`、"error message 是给模型读的 prompt" → v2 写全 6 条但有
  ① 成功路径 double encoding（`json.dumps` 一个已经是 JSON 的字符串）
  ② `TransientError` 返回 fatal=False（方向反了）
  ③ `TypeError`（模型把 order_id 写成 orderId，高频）能逃出去 → 违反"任何路径都返回字符串"
  → **教练跑真实值给他看**（double encoding 的转义输出、TypeError 实际报错），
  这个"看真实值"的手法他很吃 → v3 修好。
- **用户主动要了一次参考实现**（"可以给一个正确的 _execute_tool 吗"）。判断：
  他已自己写完 6 条路径 + 吃透 3 轮反馈，属于"做完对答案"而非"跳过思考"，故给了，
  并附差异表 + 明说其中一处简化（`except (BusinessError, TypeError)` 把
  "模型传错参数名" 和 "工具内部 bug" 混为一谈，生产应先用
  `inspect.signature(fn).bind(**arguments)` 校验）。**这个尺度可沿用。**
- 顺带补了两次 Python 基本功（**他的已知短板**）：光杆 `*`（强制关键字传参）/
  `**kwargs` 收集 vs `{**d}` 展开 / `sorted(d)` == `sorted(d.keys())` +
  `in d.keys()` 会被 ruff SIM118 flag。

### 下一步（mac 上继续时）—— ✅ 已全部完成（L8 封版 + 2026-07-27 架构复盘）
L8 作业早已封版；2026-07-27（本 session）又按新教学法补做了一次「L8 三文件架构蓝图复盘」
（工具层/核心循环/编排层的职责、边界、依赖方向、写作顺序、纯逻辑 vs 接线分层），用户已理解。
**真正的下一步见文末「下一步（给下个 session 的明确指令）」。**

---

## 阶段二 capstone 进度（用户主动提前开工，2026-07-27）
> 用户在做完 smolagents 锚点后主动说"去做一个真实的求职级 agent 项目，用上目前学的所有东西，
> **你当面试官，别让我这么容易通过**"。教练遂以**模拟面试**驱动 capstone。全部设计沉淀在
> **[`capstones/stage2-customer-service-agent/DESIGN.md`](capstones/stage2-customer-service-agent/DESIGN.md)**。
- **第一轮 需求拆解 —— 过**：用户主动问到核心三坑（范围/退款权限/知识来源），超过多数候选人。
  漏项已在 DESIGN 记录：#5 身份校验（越权泄露）、#6 规模延迟。给了满分答法「7 维度 + 三线索」。
- **第二轮 架构设计 —— 过**：五块蓝图讲全。**高光**：退款阈值 hard-code 不让 LLM 判、拿使用经验反驳"十几轮"前提。
  **被压力追问纠正的四个点**（都已进 DESIGN 收敛版）：
  ① 把"意图路由"和"退款安全"合并 → 应分两层（路由用模型/L4 LLM-router+L6 结构化输出，高危执行用代码）；
  ② 关键词路由脆弱（L4/L7 已证），弃用，改模型意图分类；
  ③ RAG 永远返回东西 → 用相似度阈值判"没覆盖"转人工，**阈值从 L7 评估集标定**；
  ④ 上下文杀手是 RAG 检索载荷不是对话轮数，控法是检索更准+压 top-k，**不 summarize 政策原文**。
- **第三轮：动手搭（带着盖楼）—— 进行中，2026-07-28 第一次坐下**：
  由**教练切第一刀**（定文件蓝图 + 第一条最小可跑链路，从"查订单"纵切），用户从空文件带着写；
  纵切打通再逐层加厚（退款阈值→RAG→转人工）。门禁三条 + 复用 L7 `eval/`、L5 记忆、L6 预算、L8 三类分流。
  ⚠️ 严守「带着盖楼」四约束（单文件为主、TODO≤~10–12、不跨文件链式依赖、蓝图先行纵切早反馈）。

  **代码在 `capstones/stage2-customer-service-agent/`（tools.py / agent.py / main.py）。已盖完 4 块，端到端 4 场景跑绿：**
  - block 1 `query_order`：归属校验（存在/forbidden/not_found 三分），出口白名单塑形。
  - block 2 `dispatch`：注入落地——user_id 用会话注入值、order_id 取模型 args，两道防线。
  - block 3 `run()`：把「两段式」升级成真 while-loop + `LoopGuard`（max_steps=8 精确、真实 `usage.prompt_tokens` 闸门）。
  - block 4 `process_refund`：**招牌菜**——复用 query_order 拿归属+真实金额，阈值 `REFUND_AUTO_LIMIT=200` hard-code、幂等防重复退、超阈值 `needs_human`。schema/dispatch/SYSTEM_PROMPT 已接。
  - 验证：查订单正常/越权收敛/退 A123(¥199)自动退/退 D999(¥699)转人工不承诺。三条面试金句已进 `interview-notes.md`「动手实现沉淀」。
  - **模型名**：用户环境用 `deepseek-v4-flash`（存在，教练知识过时；跑通即证）。key 在 `deepseek_api.txt`（gitignore）或 env。

  - block 5 ✅ **门禁第二条 pytest**（`test_tools.py`，6 条全绿，**用户自己写**）：query_order 正+两反、
    process_refund 正+超阈值+幂等；教了「空测试=假绿/red-green」「测试隔离(autouse fixture 清 `_REFUNDS`)」
    「先测纯逻辑层、碰网络用 test double」。**还了 L6「测试教练代写」的债**。三条金句已进 interview-notes。

  **✅ RAG 政策答疑 sit 1 + sit 2（接线）已完成（2026-07-29 Windows）**：
  - **sit 1**：`policy_rag.py` 的 `search_policy()` 用户已写（检索→距离阈值闸→覆盖则 grounded 生成，两分支都对）。
    阈值 `POLICY_DISTANCE_THRESHOLD=0.9` **已按真实距离标定**（命中组 0.81/0.85 vs 未覆盖组 1.45/1.60，取 0.9 偏严侧防幻觉），
    注释里留了标定证据。端到端 4 探针验过（覆盖答原文 / 不覆盖 not_covered）。
  - **sit 2（接线）**：`search_policy` 已接进 `agent.py` 当工具——三处同步改齐（TOOLS schema + dispatch 路由 + SYSTEM_PROMPT 的 `not_covered` 话术），
    import 也加了。`main.py` 端到端 6 场景全绿（查订单/越权/退款自动/退款转人工/**政策答原文/政策不覆盖转人工**）。
    ⚠️ 注意：`search_policy` 的 dispatch 路由**不注入 user_id**（政策是共享知识、无主，判据"按用户隔离才上锁"，用户已答透）。
  - **门禁第二条（测试）已补**：新建 `test_policy.py`，1 正 2 反共 3 条，全绿（连同 tools 6 条 = **9 passed**）。
    **系统学了 mock/测试替身**（还了 L6「测试系统学习」的债）：① 惰性化 `_get_collection()` 消除 import 期 I/O（可测性核心功）；
    ② `monkeypatch` 换三接缝 + 自动还原；③ "绿≠对"照妖镜"拔网线还能过吗"（用户漏 `_patch_seams` 那条偷打 3s 网络，已修）；
    ④ 行为验证 `_boom`（断言 not_covered 时不该调 `_grounded_answer`）。四连招已进 interview-notes「mock 深水区」。

  **✅ sit 3 ① 阈值标定已完成（2026-07-29）**：新建 `calibrate_threshold.py`（复用 policy_rag 索引，
     对 eval 13 条=9 normal+4 unanswerable 算 top-1 距离分布）。结果**有干净的沟**：normal 0.78–1.09 / unanswerable 1.34–1.52，
     沟(1.09,1.34)。**关键教训**：4 点拍的旧值 0.9 会误踢 3 条正例（0.914/1.041/1.090，normal 长尾）→"少量样本漏长尾把阈值定错"。
     **`POLICY_DISTANCE_THRESHOLD` 已改 0.9→1.15**（偏严防幻觉、不贴沟留正例余量；生产按误判率回调）。test_policy 注释同步更新，9 绿。
     用户高光：自己提出**三档 confidence-band 路由**（沟里加 ask_for_clarification 让用户 rephrase→重检索），并自己点出隐私风险——
     已存 DESIGN「未来增强」+ interview-notes「设计谈资」（senior 级降级路径设计，留作可选实现 / LangGraph conditional edge 对比）。

  **✅ sit 3 ② 真 escalate_to_human 工具已完成（2026-07-29）—— 裸 SDK 版封版**：
     - `tools.py` 加 `escalate_to_human(user_id, reason, summary)`：生成工单号 `T{n:04d}`、落审计台账 `_TICKETS`、
       返回 `{"ok":True,"terminal":True,"ticket_id":...}`。**terminal 是给 run() 的停机信号**。
     - `agent.py` 接线四处：import + TOOLS schema(reason 用 enum + required) + dispatch 路由(注入 user_id) +
       SYSTEM_PROMPT 改「needs_human/not_covered 去调 escalate 工具，别自己说话术」。
     - **run() 加通用 terminal 检查**：dispatch 结果 `result.get("terminal")` 为真 → 直接 return `HANDOFF_REPLY`(带工单号)、
       退出整个 loop（不 hardcode 工具名，L8"loop 读信号"回扣）。main.py 验：D999 超限→开 T0001 停机、双十一→T0002。
     - 测试补 1 条（`test_escalate_to_human_records_ticket`：开单落账 + 工单连号 T0001/T0002，查物证台账）。
       **踩坑**：`is "T0001"` vs `== `（is 比身份、== 比值；字符串运行时拼出=新对象；ruff F632）。fixture 拆成
       `reset_refunds`/`reset_tickets` 两个 autouse（单一职责）。
     - **门禁三条全过**：环境可复现 ✅ / 10 测试正反俱全 ✅ / **无残留**（清光全部 `你来写`/TODO/`我给你` 脚手架 + 硬编码 key 无 + print 均正当）。

  **🎉 阶段二 capstone 裸 SDK 版 = 封版（2026-07-29）**。文件：tools/agent/main/policy_rag/calibrate_threshold + test_tools/test_policy。
  能答三类（查订单/退款/政策答疑），三道安全线（越权注入/退款阈值 hard-code/RAG 幻觉阈值），转人工=可审计工单+终止 loop。

  **📚 对标教程已引入（2026-07-29，用户找来）**：`reference/repos/ai-agent-book/`（bojieli，10 章/93 项目/中文优先，
  已浅克隆 gitignore；`chapter1-10/`=项目，`book/`=中文讲义）。**整合策略=用户拍板「当参照脊柱、按主题精读」**（不照搬替换 JD 大纲）：
  - 书↔课程映射（到重合主题就精读对应章+跑项目）：**L10 MCP←Ch4 · L12 评估←Ch6(GAIA/SWE-bench/TAU2/OSWorld) · L11 多智能体←Ch10 · KV Cache←Ch2**。
  - **书没有、继续按 JD 走**：**L9 LangChain/框架、L13 可观测·成本·延迟·重试限流、L14 部署** —— 社招硬需求，书缺（研究者写书重理解、企业招人重落地）。
  - 书 Ch5 Coding/Ch7 后训练/Ch8 持续进化/Ch9 多模态 = 研究向加分项 → **长期作战**，第一轮投递不碰。判据不变：二八 + 社招过滤器。

  **✅ L9 框架对比 已封版（2026-07-29）**：`agent_langgraph.py` 把裸 SDK `run()` 循环用 **LangGraph** 重写，功能对等
  （agent⇄tools 循环 + terminal 终止 + recursion_limit），**工具层 tools.py 一行不改共用**。产出 **`ADR-001-langgraph-vs-bare-sdk.md`**：
  结论**编排层采用裸 SDK**（框架招牌价值当前用不上 + 安全注入逼写自定义节点=框架连省代码都没做到；触发切 LangGraph=多分支/human-in-loop/多agent/checkpoint）。
  - **Part A 框架横扫**（LangChain/LlamaIndex/AutoGen/CrewAI 定位）已讲，进 interview-notes（待补）。
  - **教学高光**：用户批判性很强——自己质疑 `{"tools":"tools"}` 恒等映射冗余（→ list 形式）、质疑写法优雅度（→ 引出"内置件不合身安全注入"ADR 金句）、追问 recursion_limit 数什么（→ 澄清 super-step vs 对话轮/escalate 终止 vs 保险丝两条路）。
  - **环境坑**：`pip install grandalf` 装错环境（uv 项目要 `uv add`）——头号短板重现，已强化"uv 项目只用 uv add"。
  - LangGraph 概念（State/node/edge/条件边/回边/画图 draw_mermaid|png|ascii）全过一遍，映射到 while-loop 每块。

  **✅ L10 MCP 与工具生态 已封版（2026-07-29，第一个真从对标书 Ch4 学的课）**：
  - 讲授（照书 Ch4）：**工具五分类**（感知/执行/协作/用户沟通/事件触发，用户 capstone 三工具对号入座）· **MCP 机制**（client-server / `@mcp.tool` / list_tools 发现 / call_tool / 三原语 工具-资源-提示 / stdio·HTTP 传输 / 插座标准 · 一次开发处处可用）· **MCP 安全四风险**（描述投毒=prompt注入变种/恶意server/tool shadowing/凭证）· **工具设计 ACI 原则**（什么时候用>能做什么、边界最重要、参数示例72%→90%、参数保真性、话术留prompt不进工具描述）· **主动工具发现**（L3 伏笔收口：主动发现MCP-Zero省98%/Skills渐进披露/动态加载别破坏KVCache/判断何时用）。
  - **动手（lesson-10/）**：用官方 `mcp` SDK 的 FastMCP 建最小 MCP server（暴露 query_order）+ client（发现+调用，stdio）。跑通 client-server 一个来回。
  - **⭐安全高光**：发现"包成 MCP 后 user_id 成 client 传参 → capstone 越权防线失效"，改成 server 侧注入 SESSION_USER_ID（工具只收 order_id），实测 client 硬塞 user_id 冒充仍 forbidden。**capstone 注入原则搬到 MCP 边界。**
  - **反哺 capstone**：用 ACI 原则审计四个工具描述，统一成 `功能/时机/边界/参数/返回` 结构（search_policy 从"查询平台政策"→具体范围+边界）。10 测试仍绿。
  - **环境**：`mcp` 2.0 拆走了 FastMCP，钉到 `mcp<2`（1.29.0）。用户批判性延续（问描述该不该结构化标签→引出"话术属prompt不属工具描述"分层）。

  **✅ Reflection 反思范式 已封版（2026-08-04，Windows）—— 校招缺口补齐**：
  - 定位：L8 追补 / 补齐 capstone 的 **Planning-Acting-Reflection 闭环**（百度 JD1/3 点名）。对标书 Ch8 入门形态。
  - **新建 `reflect.py`**（evaluator，LLM-as-judge）：rubric 从 SYSTEM_PROMPT 话术约束 + 三道安全线翻译成「质检员视角」；
    结构化输出 json_object 返回 `{verdict, critique}`；**client 依赖注入可 mock**；**整段 try + fail-open**（质量层不拖垮已有安全线）。
  - **`agent.py run()` 接线**：正常出口前调 reflect（`MAX_REFLECTIONS=1`）；revise→append 草稿+critique 重写一次；
    `tool_trace` 累积每个工具返回喂 judge 判忠实性。**落点只在正常出口**（terminal 转人工提前 return，天然不进反思）。
  - **`test_reflect.py`（门禁第二条，3 条全绿）**：accept 正 / revise 反 / **fail-open 兜底**（judge 抛异常→仍 accept，钉死防回退）。
    假 client 用 SimpleNamespace 拼调用链，零网络。连同 tools 6 + policy 3 = **13 passed**。
  - **实测证据**：直接探针 3 条——泄露归属 revise（点名红线1）/ 编造金额 revise（点名红线3）/ 合规 accept；端到端 6 场景全绿不误伤。
  - **门禁三条全过**：环境可复现 ✅ / 13 测试正反俱全 ✅ / 无残留（你来写·TODO 清光、py_compile 过、无硬编码 key）✅。
  - **教学高光/踩坑**：① rubric 初版抄成「演员台词」→ 翻译成审查视角；② 模型名误写 gpt-4o-mini（DeepSeek 端点没有）；
    ③ fail-open 声明与代码打架（try 没包 API 调用，模型宕机时实际 fail-closed）→ 整段 try 修正；
    ④ **头号短板重现**：`tool_trace.append` 摆在 for 循环外（一轮多工具只收最后一个）→ 挪进循环内；
    ⑤ 两个埋点答透：fail-open 理由（质量层叠在已执行的安全线上）、client 为何注入（可 mock / 副作用依赖注入）。
  - 素材已进 interview-notes「十一、Reflection」（含 fail-open / 代价不对称 / 落点选择 / Evaluator 独立性 王牌话术）。

  **🚩 用户拍板（2026-08-04）：先冲「投递-ready」再学 L11**（在校生冲 2027 届校招，秋招 9 月开闸，时间不等人）。
  投递-ready 三件套（≈1–2 次坐下，按序）：
  ① ✅ **最小部署 已完成（2026-08-04，Windows，用户亲手 build+run Docker）**：
     - `app.py`：FastAPI POST `/chat` + `/health`；**认证注入身份**（`X-User-Token`→user_id 查 FAKE_TOKENS，请求体故意不含 user_id）；
       `Depends(resolve_user)` 依赖注入；run() 异常兜成 503 优雅降级（`from e` 异常链）。
     - `test_app.py`（3 条）：正（合法 token→200+身份对）/ 反（无 token→401 且 run 没被调）/ **安全（body 偷塞 user_id 被无视，仍 u_li）**。
     - `Dockerfile` + `requirements-deploy.txt`（pin 版本）+ `.dockerignore`：slim 基础镜像、层缓存序、非 root、key 运行时 `-e` 注入不烤进镜像、`--host 0.0.0.0`。
     - **真跑容器揪出两个隐患**：① app 隐藏依赖第二个 key（policy_rag 的 embedding 用 OPENAI_API_KEY，本地被 env 掩盖）；
       ② policy_rag 两个 client 在 **import 期急切构建**（`os.environ["OPENAI_API_KEY"]` 缺 key 就崩）→ 用户**惰性化**成 `_get_embed_client/_get_gen_client`（照 `_get_collection` 套路），验证缺 key 也能 import、`/health` 能起、RAG 路径延到调用时才要 key。
     - 环境坑（都真踩了）：国内拉 Docker Hub 超时→配 registry-mirrors（daocloud/百度/dockerproxy）；Windows 8000 保留端口→换 8071；PowerShell curl 引号/`curl.exe`/UTF-8；**从仓库根跑 pytest 撞同名 tools.py + reference/ 的 sys.exit→加 `[tool.pytest.ini_options] norecursedirs` 忽略 reference，并确立「monorepo 分目录跑 pytest」工作流**。
     - 门禁三条过：环境可复现（pin+uv）✅ / 16 测试正反俱全（分目录跑）✅ / 无残留（你来写·TODO 清光）✅。
     - **⚠️ 老短板重现**：惰性化时两个 getter **都漏 `return`**（一次两个，参考模板 `_get_collection` 就在下面 4 行）→ 已固化自查句「写完带 `-> X` 的函数扫每条路径是否都 return，尤其干完副作用那步」。
  ② ✅ **capstone README 已完成（2026-08-04）**：`README.md` 门面+导航——能力表/亮点/架构图(mermaid 画 ReAct+Reflection 闭环)/
     三道安全线/快速开始(CLI+pytest+uvicorn+Docker)/设计决策表链 DESIGN+ADR/已知简化。教练起草，用户 review。
  ③ 🔵 **简历包装 = 用户自己弄**（教练已给一版 4 bullet 重排建议：拆短、加 Reflection+FastAPI/Docker 关键词、10→16 pytest、
     "意图路由"改"function-calling 分派"防穿帮；用户说简历自己搞定）。
  ④ 做完即**开投**，然后 L11 起边投边学。

  **🔧 修复潜伏 bug（2026-08-04）**：上次"最小部署"commit(124890d) 的 policy_rag 两个惰性 getter **漏了 return**（buggy 版被提交），
     测试没抓到（monkeypatch 的是上层接缝 `_embed`/`_get_collection`，不真调 getter；容器只测了查订单不走 RAG）→ 第一次问政策会 `None.embeddings` 崩。
     commit 前 `git diff` 扫出来补上（`return _EMBED_CLIENT`/`_GEN_CLIENT`），验证 getter 返回+缓存生效、16 绿。**"漏 return"老短板 + git diff 自查习惯又各印证一次。**

  **🧭 反思节点门控决策（2026-08-04，用户批判性提问）**：用户问"现在项目该加 reflection node 吗"——教练诚实评估：**当前"每轮都反思"对客服场景偏过度工程**
     （安全已 hard-code、反思只兜话术低风险残差、6 场景实测全 accept=常态白跑、成本/延迟翻倍）。**生产正解=信号触发**（仅本轮 tool_trace 出现 forbidden/needs_human/not_covered/退款成功才反思）。
     **用户决定"先不加"（保持每轮反思现状）**，作为面试口头故事（"我加了反思→发现每轮跑浪费→该门控到高危路径"=懂何时不用一个技术）。信号触发留作可选增强（性价比高的一刀）。

  **✅ L11 Multi-Agent 已封版（2026-08-04，对标书 Ch10 主线，边投边学第一课）**：
  - 讲授（照书 Ch10）：**两维度**（上下文共享/隔离=线程/进程 · 协作拓扑 对等/管理者/去中心化）· **核心判据=协作是否引入单Agent拿不到的新信息**（引入=执行/视觉/工具反馈显著提升;没引入=同模型自审/纯辩论通常无效;成本≈15×token）· 失败模式（并发冲突/级联放大）· Agent 社会（谈资）。
  - **⭐打脸呼应**：上节 reflect=同模型自审=判据表"通常无效"那行→解释了它 6 场景全 accept。用户"该不该每轮反思"直觉被 Ch10 印证。
  - **动手（lesson-11/，用户自己提的项目）= 多 Agent 代码审查系统**：管理者模式+隔离上下文+并行。`static_review`(pyflakes 工具反馈,唯一引入新信息的)+ `llm_review`(安全/正确性 lens,隔离+DI+fail-open)+ `synthesize`(去重+工具优先排序)+ `review`(ThreadPoolExecutor 并行)。
    活证据：pyflakes 抓 db未定义/os未用(LLM漏)、LLM 抓 SQL注入/除零(工具看不见)——**价值来自异质性不是人头数**。
  - **门禁三条过**：环境可复现(uv+pyflakes)✅ / 4 测试正反俱全（synthesize去重排序/static确定性/**隔离性招牌测试**/fail-open）✅ / 无残留(print→logger、你来写·TODO清光)✅。
  - **本节坑（都真踩）**：sys.executable vs 裸python · Windows盘符冒号打乱解析(已知路径先剥再解析) · **prompt↔parser契约不同步→findings丢光**(改一半) · NamedTemporaryFile漏mode=w · 测试断言对着"我以为"非真实英文输出 · 并行先全submit再收result。
  - **新概念=并行**：ThreadPoolExecutor(I/O-bound用线程,等I/O释放GIL)。用户第一次碰并发,理解了 submit/result/flatten + GIL下list.append原子。
  - 素材进 interview-notes「十二、Multi-Agent」（判据/隔离防anchoring/并行选型/防级联 王牌）。

  **✅ L12 评估体系 已封版（2026-08-04，对标书 Ch6，收束课）**：
  - 讲授（照书 Ch6）：**指标词典**（过程/结果/安全/鲁棒；**Pass@k vs Pass^k** 能力上限 vs 稳定性；轨迹 vs 结果双重覆盖=L5 体系化）·
    **LLM-as-Judge**（长度偏差；**Rubric 四准则** + 一票否决 veto；**评判者校准** 金标集+kappa>0.7）· **统计显著性**（二项标准误/配对分析 McNemar/多重比较陷阱；分差<噪声带宽→不切换）· **可观测性回流评估资产**。
  - **收束**：把 L7 eval 集、reflect/代码审查的 judge、刚做的 Langfuse tracing 收成体系。
  - **动手（eval/rubric_judge.py）= Rubric LLM-judge 填掉 L7 子串匹配的坑**：`RUBRIC`(多维度+veto) + `judge_reply`(结构化+DI+fail-closed 兜底+veto 归一化) + `GOLDEN_SET`(6 条人工判定) + `calibrate`(算一致率)。
    **⭐高光**：g03「不是,是7天」pass vs g04「是的,100天」fail——都含子串"100天"、子串匹配都误杀,LLM-judge 语义区分确认/纠正。校准 6/6 一致(诚实局限:6 条统计不够,真实要 100-200+kappa,回扣 §4 自打脸)。
  - **门禁三条过**：环境可复现 ✅ / 4 测试正反俱全(veto 归一化/fail-closed/pass/calibrate) ✅ / 无残留 ✅。
  - **本节坑**：json.loads 结果不保证 dict(用户自己抓到,要校验形状) · **raise ValueError 却 except JSONDecodeError 接不住**(子类接不住父类)→ except (两者) · veto/verdict 归一化差点漏 · judge 挂了该单独记 error 别混进 pass/fail。
  - **五题 quiz 全过**,统计显著性 + judge 校准答透(应届生盲区)。素材进 interview-notes「十三、评估体系」。

  **🚩 用户拍板（2026-08-10）：SFT 优先级提前**。原属"长期作战/研究向池（书 Ch7，第一轮投递不碰）"，
  现提前为**下一个主推课**（本条 supersede 上文 2026-07-29「Ch7 → 长期作战」的决策记录）。
  拟定形态（开课前和用户对一遍再定稿）：
  - 定位：**SFT 微调专项（对标书 Ch7 后训练，只取 SFT/LoRA 层，RL(PPO/DPO) 仍留长期）**。
  - 讲授：SFT 在后训练全景里的位置（预训练→SFT→RLHF/DPO）· 数据格式(chat template/loss mask 只算 assistant token) ·
    全参 vs LoRA/QLoRA 的取舍 · 何时微调 vs 何时 prompt/RAG 就够（面试必问的判断题）。
  - 动手（初步构想）：小开源模型（如 Qwen 系 0.5B–1.5B）上 LoRA 微调客服领域数据，
    **复用 `eval/` 金标集 + rubric_judge 做 before/after 评估**（回扣 L12，形成"训练→评估"闭环，这是招牌）。
  - ⚠️ 开课前先摸底：**硬件**（Windows 机有无可用 GPU？显存多大？否则 QLoRA/Colab/云 GPU）与训练框架选型
    （transformers+peft / LLaMA-Factory / unsloth）。
  - 求职逻辑：百度 JD3/JD4（智能体算法/大模型研发）微调是硬通货，"亲手 SFT 过 + 有评估闭环"比多数应届生突出。

  **⭐ 下次坐下从这里选（校招优先级，边投边学；2026-08-10 SFT 提前后的新排序）**：
  ① **SFT 微调专项**（书 Ch7，见上方拍板记录）——**下一个主推**。
  ② **L13 可观测/成本/延迟深化 + API 重试限流(429) + L13.5 Agent Harness**（JD2 整篇，Claude Code 锚点）——顺延。Langfuse 已实操,可深化(自定义 span/挂 LLM-judge 打分/dashboard)。
  ③ **L14 部署深化**（K8s，最小部署已做过 FastAPI+Docker）。
  ④ 其余研究向加分（书 Ch5 Coding/Ch8 self-improvement）：**Reflexion 重版**（跨 attempt 存 memory）· 代码审查加"真跑测试"执行反馈版（RLEF）· Skills 渐进披露实现（书 Ch2/4，L10 讲过没做）。
  ⑤ 未做的可选增强：反思**信号触发**门控（capstone）· 代码审查**语义去重** · rubric_judge 补 score 档位定义（§3 准则4）+ 扩金标集到 kappa ·
    三档 confidence-band 澄清路由（DESIGN 未来增强）· 各节 summary.pdf（阶段三简历包装时做）。

## 下一步（给下个 session 的明确指令）
- **开局顺序**：①`git pull` ②读本文件（**尤其正上方「阶段二 capstone 进度」+「L8 封版记录」**）
  ③读 `capstones/stage2-customer-service-agent/DESIGN.md`（capstone 施工图）④`uv sync`。
- **立刻要做**：**继续 capstone 第三轮 = 动手搭**。教练切第一刀，从空文件带着写第一条最小链路。
  用户仍在"面试进行中"的心态，保持面试官压力追问 + coaching 双模式，别放水。
- **锚点已完成**：smolagents 三栏笔记 `anchor-notes/L8-smolagents.md` 已落笔，勿重做。
- **L9 顺延到 capstone 裸 SDK 版做完之后**（v3 改法：裸 SDK vs LangGraph 两版对比 → ADR）。
- **L8 已讲完，供后续回扣**：ReAct=他 L2 手写的 loop；重规划频率轴；自主性是成本；
  "扇出目标运行时发现 vs P&E 规划期定死"；stop_reason 如实报闸门；工具层调用前 bind 校验 + 调用后三类分流。
- L8 教学要点（已讲完，供 summary 与后续回扣用）：**L8 路由 / ReAct / Planning**（JD 6/10）。**核心回扣**：
  他 L2 手写的 agent loop **本质就是 ReAct**（Reason→Act→Observe），L8 是给这个"涌现的循环"
  正式命名 + 讲清 ReAct vs Plan-and-Execute 取舍。**别让他觉得是全新东西——是给旧知识命名。**
  - v3 指定的锚点：**smolagents CodeAgent**（Python，≤90min，第一个锚点，做成模板）。
    引导问题见 v3 §L8：①"想→动→看"在 JSON tool-calling vs 代码即动作两种范式下各长什么样？
    ②代码即动作在受益于循环/组合的任务上减少轮次，代价是什么（沙箱/安全面/小模型崩坏）？
    ③**什么条件下显式规划有帮助？什么条件下它产生过时计划和多余延迟？**
    （为什么 pi/Claude Code 不内置 planner，而客服 agent 常要显式路由？）
  - 封版走**三条门禁**（pytest 那条：教练搭脚手架）。
- **⚠️ 环境已迁到 uv（L7 完成）**：跑代码用 `uv run python xxx.py`，装包用 `uv add X`，
  mac 端 `git pull` 后先 `uv sync` 复现环境。`.venv` 在仓库内、已 gitignore；pyproject/uv.lock 已入库。
  conda `agent` 环境暂留兜底。
- **保持生产规范**（用户硬要求，见「教学标准变更」）：默认生产级写法，简化必说明差距。
- **每节顺带**：讲到 JD 高频点就标"X/10 的 JD 要求"；踩坑与权衡随手记进 `interview-notes.md`。
- **macOS 上的 PDF 生成方式**与 Windows 不同，见下方「PDF 生成方式」一节。
- **仓库里新增的两份长期维护文件（每节课封版时一并更新）**：
  - [`interview-notes.md`](interview-notes.md) —— **面试素材本**，按"面试官会怎么问"组织，
    已沉淀 L1-L5 素材。**每封版一节课就回来补一次**（文末有待补清单）。
  - [`reference/模型选型.md`](reference/模型选型.md) —— 补 L1-L5 缺口：推理模型 vs 普通模型、
    模型选型 6 维度、主流厂商特性、面试答题框架。**L6 开头带他过一遍。**
- **求职相关的持续动作**（每节课都可顺带做）：
  - 讲到 JD 高频点时**明说"这条 X/10 的 JD 都要求"**，让他知道为什么学这个、面试会怎么问。
  - 攒**面试话术**：每节课的翻车与权衡都是面试素材（如"验收看 tool_calls 不看话术"、
    "路由用非思考模型"），提醒他记下来。
  - **简历素材**：他用 Claude Code 全程学 agent 开发这件事本身是加分项（拼多多/沃孚把
    "熟练使用 AI 编程工具/AI 原生思维"写进硬性要求），阶段三包装简历时务必用上。
- **需要注意（重要教训）**：**不要抢跑**——一节课收尾后停下等，不自动开下一课，不在答疑末尾催进度；
  只有用户明确说开始下一课才教。坚持 coaching 式给提示不给答案，但**作业用「带着盖楼」式引导手写**
（蓝图先行 + 从空文件带着写，不再是纯填空骨架，见 §三·补三与「🔴 教学标准变更②」）；
  materials 分时创建（notes/quiz 当场建，summary.pdf 封版才出）；每次 commit 后 `git push` 到 B6nux9。
- **commit 前记得** `git diff` 扫一眼（别把 .DS_Store / 临时调试值/ key 文件误提交——历史上已发生过一次
  误提交 deepseek_api.txt+.DS_Store 需回滚，.gitignore 已加，但仍要养成 add 前看一眼的习惯）。
