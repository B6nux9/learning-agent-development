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
- 起始日期 / 最近更新：2026-07-13 / 2026-07-26（L7 封版）
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
- **学习偏好**：边做边讲、理论实践平衡；**不想直接看答案**，喜欢用填空骨架自己动手
  （coaching 式教学，给提示不给答案）。

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
> 求职定位：**社招**，1-3 个月投一轮，不排除长期作战。JD 原文存在 `Requirements/`。

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
- [x] **L7 RAG 与向量数据库** —— 已完成，达标（quiz 3题过；作业 `rag.py` 端到端跑通：
  切块+OpenAI embedding+ChromaDB+grounding；口语/近义命中、库外问题 grounding 挡幻觉；
  **亲手验证 chunking 决定 RAG 上限**：固定窗口 vs 按标题切对比，检索与答案质量都上台阶）
- [~] **L8 路由 / ReAct / Planning** —— **进行中**（JD 6/10）　← **当前断点**
      讲授 ✅ · quiz ✅ 达标 · 作业进行中（Part A 写了一半）。详见文末「L8 交接细节」。
- [ ] **L9 主流框架：用 LangChain 重写项目** ——（JD 6/10，**从 L14 大幅前移**；简历关键词）
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
- [ ] 高并发与分布式深化 · 模型微调(SFT/RLHF，多为加分项) · 多模态 · KV Cache/vLLM 推理优化 ·
      Agent 安全深水区(沙箱执行) · 前沿跟踪

- capstone 状态：阶段一 ✅ 已完成；阶段二/三 未开始
- **时间估算**：阶段二 5 节 + 阶段三 4 节 ≈ 9 节 × ~3h + 两个 capstone ≈ **50 小时**；
  按每周 5-10 小时 → **5-10 周**，落在 1-3 个月窗口内，可行但要保持节奏。

## 当前掌握等级评估
**Intermediate 稳步推进（阶段二进行中，已完成 L5/L6）**。除阶段一能力外，已掌握长期记忆存取闭环、
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

## 🔶 L8 交接细节（2026-07-26 晚，用户明天换到 **macOS** 继续）

> 状态：**讲授 ✅ · quiz ✅ 达标 · 作业 Part A 进行中。未封版。**
> mac 上开工先 `git pull` 然后 `uv sync`。

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

### 下一步（mac 上继续时）
1. `git pull` → `uv sync` → 让他先修 `record_step` 那个 bug（**别代劳**）
2. 继续 TODO-3 → TODO-6 → TODO-7，跑通 `uv run python lesson-08/homework/executor.py`
3. 再做 planner.py → 补测试断言 → compare.py → findings.md
4. 作业跑通后做**锚点 smolagents CodeAgent**（≤90min，v3 第一个锚点，做成模板）
5. 走门禁三条封版 → 出 summary.pdf → 补 interview-notes → 更新本文件

---

## 下一步（给下个 session 的明确指令）
- **开局顺序**：①`git pull` ②读本文件（**尤其上面的「L8 交接细节」**）
  ③**读 `COURSE-OVERVIEW-v3.md`**（权威大纲）④确认环境：`uv sync`。
- **立刻要做**：接上面「L8 交接细节 → 下一步」。**L8 未封版，作业进行中。**
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
  只有用户明确说开始下一课才教。坚持 coaching 式给提示不给答案（用填空骨架，让他自己补核心逻辑）；
  materials 分时创建（notes/quiz 当场建，summary.pdf 封版才出）；每次 commit 后 `git push` 到 B6nux9。
- **commit 前记得** `git diff` 扫一眼（别把 .DS_Store / 临时调试值/ key 文件误提交——历史上已发生过一次
  误提交 deepseek_api.txt+.DS_Store 需回滚，.gitignore 已加，但仍要养成 add 前看一眼的习惯）。
