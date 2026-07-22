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
- 起始日期 / 最近更新：2026-07-13 / 2026-07-22（L6 进行中，跨机器交接）
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
- [~] **L6 上下文管理 + Prompt/Context Engineering** —— **进行中**　← **当前断点**
  - ✅ **讲授完成**（notes.md 完整）：上半场上下文管理（平方级增长、lost in the middle、
    上下文=预算表、四类策略）；下半场 Prompt Engineering（五块骨架、别用模糊限定词、
    点名禁掉失败模式）+ **结构化输出三层次**（补缺口 2 已完成）。
    模型选型 reference 已带他过了一遍。
  - ✅ **quiz 完成**（6 题）：Q2/Q3/Q5/Q6 满分；**Q1 补讲**了"单次线性 vs 累计平方"的区分；
    **Q4 让他重写了 prompt**，他第二版仍有两处问题（把 JSON 输出格式套到所有场景——
    违背了他自己刚答对的"给人看就用普通文本"；漏了负面约束），已给参考版本对照。
  - ⏳ **作业进行中** —— 见下方「L6 作业当前状态」

### ⚠️ L6 作业当前状态（跨机器接力要点）
`lesson-06/homework/` 下有**两套**，别搞混：
1. **`context_manager.py`（v1）—— 已废弃为「参考实现」，不要再让他做。**
   他做过一轮，撞了三个坑（都已讲透并修好，代码里有 `【改】` 注释）：
   ①混血列表 `AttributeError`（第 3 次犯）→ **根治法：在 `run_agent` 入口用
   `msg.model_dump(exclude_none=True)` 归一化**，下游全部免疫。金句已入 interview-notes：
   "同一个 bug 在多处重复出现，说明抽象层漏了——应在数据入口统一格式，而非每个使用点做防御"。
   ②切点逻辑方向反了（危险的是 **tool** 落在切点上，不是 assistant）。
   ③摘要 prompt 用了"不要丢失**重要**信息"这种模糊词。
   后又按他要求把 token 估算**升级成 `response.usage.prompt_tokens`**（见下方"生产规范"）。
2. **`v2/`（当前作业，他明天要做的）** —— 三文件分层：
   - `v2/context.py`：**纯逻辑**模块，TODO 1 `find_safe_cut_index`（纯函数）、
     TODO 2 `ContextManager`（三策略 + fail-fast 参数校验 + 不修改入参）
   - `v2/test_context.py`：**本次新肌肉 = 单元测试**。已给 5 个样板，
     TODO 3/4 各补 4 个。核心教学点：**依赖注入**（注入 fake_summarizer 使测试
     快/稳/免费/能测异常路径）、`exploding_summarizer` 测"某函数没被调用"的套路。
   - `v2/agent.py`：接线层（碰 LLM/网络），**已写好**，他只需读懂分层。
   - 跑测试：`pip install pytest` → `cd lesson-06/homework/v2 && pytest test_context.py -v`
     （**他机器上还没装 pytest**；文件底部有免 pytest 的自跑入口，但 `pytest.raises` 那题需要）
   - 对应 JD：蔚蓝"建立 Agent 任务的**评估与回归测试体系**"。

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
- [ ] **L7 RAG 与向量数据库** ——（**JD 8/10，第二高频，重中之重**）
- [ ] **L8 任务规划：ReAct 与 Plan-and-Execute** ——（JD 6/10，**新增**，原大纲完全没有）
- [ ] **L9 主流框架：用 LangChain 重写项目** ——（JD 6/10，**从 L14 大幅前移**；简历关键词）
- [ ] **L10 MCP 协议** ——（JD 4/10，**新增**；2025-26 热点，面试常问）
- [ ] 🎯 **阶段二 capstone：简历级客服 Agent 项目**（最重要产出，直接写进简历）

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
**已迈入 Intermediate 门槛**（阶段一收官）。除 L2/L3 能力外，L4 独立完成阶段一 capstone：能做
分组路由（代码编排）、会话内多轮记忆、LLM-as-router，并抓住「**能力来自工具、可靠性来自约束**」。
主动推导出 **记忆（L5）、上下文（L6）** 两个后续核心问题——超出 Beginner 深度。
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
- **Windows 环境变量（本节踩坑，已解决）**：永久设 key 用
  `[Environment]::SetEnvironmentVariable("DEEPSEEK_API_KEY","sk-...","User")`；
  **关键坑：VSCode 启动时就把环境变量拍了快照**，改注册表后新开终端标签也读不到，**必须完全重启 VSCode**。
  临时救急：`$env:DEEPSEEK_API_KEY = [Environment]::GetEnvironmentVariable("DEEPSEEK_API_KEY","User")`。
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

## 下一步（给下个 session 的明确指令）
- **⚠️ 先读上面「L6 作业当前状态」和「教学标准变更」两节。** L6 讲授和 quiz 都已完成，
  **不要重讲**，直接接作业。
- **立刻要做**：确认他 `v2/` 作业的进度（是否已实现 TODO 1-4、pytest 装了没）。
  他在 Windows 上还没装 pytest；换到 macOS 后可能也要先 `pip install pytest`。
  卡住就按老规矩：**给提示不给答案**，让他先跑先撞，撞了再一起看真实值/物证。
- **L6 封版流程**（作业跑通后）：出 summary.md + PDF → 更新 PROGRESS → 补 `interview-notes.md`
  （L6 素材：平方级增长、lost in the middle、依赖注入使 agent 可测、入口归一化根治混血列表、
  usage 而非自估 token）→ commit + push。
- **L6 里还没做的**：v1 的 **Part B「结构化输出路由」还空着**。可在 v2 作业完成后作为收尾小练习，
  或并入阶段二 capstone。**别忘了它——那是补缺口 2 的动手部分。**
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
