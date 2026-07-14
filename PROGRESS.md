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
- 起始日期 / 最近更新：2026-07-13 / 2026-07-14
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
- [ ] **L3 tool use 深入** —— **未开始**，等用户开口才教（勿抢跑）  ← **当前断点**
- [ ] L4 多工具编排　→ 阶段一 capstone：命令行多工具 agent
- [ ] L5 记忆与状态 · L6 上下文长度管理 · L7 RAG · L8 客服原型　→ 阶段二 capstone
- [ ] L9 评估 · L10 错误处理 · L11 成本/延迟/可观测性 · L12 打磨　→ 阶段三 capstone（求职主力）
- [ ] L13-15 拓展（多智能体/框架/前沿）
- capstone 状态：均未开始

## 当前掌握等级评估
**Beginner 稳固，局部触到 Intermediate 的思考**。已能**独立手写 agent loop**（L2 作业一次跑通，
function calling 四步、多工具单轮调用、停止条件、messages append 顺序都对），并主动推导出
**记忆（L5）与上下文（L6）** 两个后续核心问题——超出 Beginner 该有的深度。
工程/环境基本功仍是需持续留意的短板（L2 又问了 env 变量怎么设、终端会话一致性），
但 L1 的坑（哪个 python、包装哪了）已能用 `sys.executable` / `conda info --envs` 自查。

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
- **流程改进（本次确立，已存记忆 material-creation-timing）**：三份材料分时创建——notes 讲授时就建、
  quiz 出题时就建、**只有 summary.pdf 等封版才生成**。以后每节照此，别再堆到封版一起做。
- **PDF 生成方式（本机 macOS）**：无 pandoc/weasyprint；用 base anaconda 的 `markdown` 库转 HTML，
  再用 Chrome headless `--print-to-pdf`（中文字体渲染最稳）。命令见 L2 封版记录。
- **途中的决定/调整**：模型定 DeepSeek（国内求职）；工作路径与仓库从 `E:\CAS\展望` 迁到
  `E:\Agent`；GitHub 账号从误用的 el4435 改为指定的 **B6nux9**（el4435 上的旧副本待用户手动删）。

## 下一步（给下个 session 的明确指令）
- **立刻要做**：**什么都不要做，等用户说"开始 L3 / 继续"**。L2 已封版，主动权在用户手里。
  用户开口后再生成并教学 **L3 tool use 深入**（在 L2 单工具 loop 的基础上往深走：多工具、
  参数校验/报错处理、`description` 如何影响调用准确率、并行 vs 串行工具调用等；具体大纲开课时定）。
- **需要注意（重要教训）**：**不要抢跑**——一节课收尾后停下等，不自动开下一课，不在答疑末尾催进度；
  只有用户明确说开始下一课才教。坚持 coaching 式给提示不给答案（用填空骨架，让他自己补核心逻辑）；
  materials 分时创建（notes/quiz 当场建，summary.pdf 封版才出）；每次 commit 后 `git push` 到 B6nux9。
