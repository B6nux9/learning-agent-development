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
- 起始日期 / 最近更新：2026-07-13 / 2026-07-15（L4 + 阶段一 capstone 封版）
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
- [ ] **L5 记忆与状态** —— **未开始**，等用户开口才教（勿抢跑）　← **当前断点**
- [ ] L6 上下文长度管理 · L7 RAG · L8 客服原型　→ 阶段二 capstone
- [ ] L9 评估 · L10 错误处理 · L11 成本/延迟/可观测性 · L12 打磨　→ 阶段三 capstone（求职主力）
- [ ] L13-15 拓展（多智能体/框架/前沿）
- capstone 状态：均未开始

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
- **立刻要做**：**什么都不要做，等用户说"开始 L5 / 继续"**。L4 + 阶段一 capstone 已封版，主动权在用户手里。
  用户开口后进入 **阶段二**，先教 **L5 记忆与状态**。L5 直接回扣 capstone：他已亲手做了「会话内多轮记忆」
  （累积 messages），L5 讲它的**边界**——messages 越滚越长怎么办、跨会话/重启后记忆怎么留、
  短期(对话)vs长期(用户档案)记忆之分。明确点回"这就是你 L2 就想到、L4 又亲手搭的问题"。
- **需要注意（重要教训）**：**不要抢跑**——一节课收尾后停下等，不自动开下一课，不在答疑末尾催进度；
  只有用户明确说开始下一课才教。坚持 coaching 式给提示不给答案（用填空骨架，让他自己补核心逻辑）；
  materials 分时创建（notes/quiz 当场建，summary.pdf 封版才出）；每次 commit 后 `git push` 到 B6nux9。
- **commit 前记得** `git diff` 扫一眼（别把 .DS_Store / 临时调试值/ key 文件误提交——历史上已发生过一次
  误提交 deepseek_api.txt+.DS_Store 需回滚，.gitignore 已加，但仍要养成 add 前看一眼的习惯）。
