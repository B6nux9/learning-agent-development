# 学习：Agent 开发

用「先摸底 → 二八原则切入 → 边做边测边留痕」的方式系统学习 Agent 开发。终点定在
**Advanced（第 4 级）**：能独立设计并搭出一个 production 级客服 Agent，懂每个组件的
权衡取舍，能在面试里讲透细节。为求职而学（**校招/应届为主、社招兼顾**），重项目细节与落地；
研究向内容按校招加分权重穿插。目标岗见 [Requirements/](Requirements/)。

- **学习者画像**：会 Python、调过大模型 API、懂 LLM 原理；工程基本功偏弱（环境管理、多文件项目结构）。
- **默认模型**：DeepSeek（OpenAI 兼容接口，写法可迁移到通义千问 / GPT）；RAG 的 embedding 用 OpenAI `text-embedding-3-small`。
- **节奏**：每周 5–10 小时，边做边讲。

> 📍 **实时进度、断点、下一步以 [PROGRESS.md](PROGRESS.md) 为准**（跨机交接文件）。本 README 是相对静态的总览。
> 🗺️ **全景路线图（我在哪 / 下一步 / 每项从哪学）见 [ROADMAP.md](ROADMAP.md)**。

## 五级阶梯

1. **Layman** — 说清 agent 与普通调 LLM 的区别（LLM + 工具 + 记忆 + 循环）。
2. **Beginner** — 手写 agent loop，让模型调用工具完成多步任务。← 核心 20%
3. **Intermediate** — 记忆、上下文长度管理、RAG、多工具编排、路由 / ReAct，搭出客服原型。 ✅（capstone 裸 SDK 版封版）
4. **Advanced** — 上下文工程、评估、错误处理、成本 / 延迟 / 可观测性、服务化，打磨成上线级项目。 **← 当前（L9 起）**，也是终点
5. **Expert** — 自研框架、前沿（本课不追，选做拓展）。

## 大纲与进度（两轨制，按 11 份目标岗位 JD 需求频次重排）

大纲于 2026-07 按目标岗位 JD 反向重排，详见 [Requirements/](Requirements/) 与 [COURSE-OVERVIEW-v3.md](COURSE-OVERVIEW-v3.md)。

### ✅ 已完成

| 课 | 内容 | 产出 |
|---|---|---|
| L1 | 什么是 agent | `lesson-01/` |
| L2 | 手写 agent loop（本质即 ReAct） | `lesson-02/` |
| L3 | tool use 深入（多工具 / 链式 / 错误回传 / 循环上限） | `lesson-03/` |
| L4 | 多工具编排 + **阶段一 capstone** | `lesson-04/homework/cli_agent.py` |
| L5 | 记忆与状态（跨重启记忆） | `lesson-05/` |
| L6 | 上下文长度管理 + Prompt / 结构化输出 | `lesson-06/` |
| L7 | RAG 与向量数据库（chunking / embedding / ChromaDB / grounding） | `lesson-07/` · `eval/` |
| L8 | 路由 / ReAct / Planning + **smolagents 源码锚点** | `lesson-08/` · `anchor-notes/L8-smolagents.md` |
| 🎯 阶段二 capstone | 简历级客服 Agent（**裸 SDK 版封版**，见下） | `capstones/stage2-customer-service-agent/` |

### 🎯 阶段二 capstone —— 简历级客服 Agent（**裸 SDK 版已封版** ✅）

模拟面试驱动：设计面两轮通过 → 第三轮「带着盖楼」动手搭。综合 L1–L8 全部能力。
代码见 [`capstones/stage2-customer-service-agent/`](capstones/stage2-customer-service-agent/)（[DESIGN.md](capstones/stage2-customer-service-agent/DESIGN.md) 是施工图）。

**能力三类**（查订单/物流 · 退款 · 政策答疑 RAG），**安全三道线**，端到端 6 场景 + 10 pytest 全绿：

- **`query_order`** — 归属校验（存在 / 越权 / 不存在三分）+ 出口字段塑形。
- **`dispatch` + 注入防线** — `user_id` 由会话代码注入、模型 args 一律不认（防越权，判据「按用户隔离才上锁」）。
- **`run()`** — 真 ReAct while-loop + `LoopGuard`（轮数上限 + 真实 `usage.prompt_tokens` 预算闸门）+ **通用 terminal 停机信号**。
- **`process_refund`** — 招牌菜：阈值 `≤¥200` **hard-code 在代码**（不让 LLM 判）+ 幂等防重复退 + 超阈值转人工。
- **`search_policy`（RAG）** — 相似度阈值 **1.15**（`calibrate_threshold.py` 从 eval 13 条分布标定）挡「没覆盖」转人工，防幻觉。
- **`escalate_to_human`** — 转人工做成**终态工具**：开审计工单（`_TICKETS` 台账）+ `terminal` 信号真正终止 loop，不靠话术。
- **测试**：`test_tools.py` / `test_policy.py` 共 10 条正反 + **mock/monkeypatch/惰性化可测性**（碰网络的 RAG 用测试替身隔离）。

封版走**门禁三条**：环境可复现 / 至少 1 正 1 反 pytest 绿 / 无调试残留。

### 🚧 进行中 / ⬜ 待学

- **L9 框架对比 ✅ 封版**：`agent_langgraph.py` 用 LangGraph 重写 `run()`（功能对等，tools.py 共用）+ [ADR-001](capstones/stage2-customer-service-agent/ADR-001-langgraph-vs-bare-sdk.md)（结论=编排层用裸 SDK；校招"能分析框架优劣"的证据）。
- **L10 MCP ✅ 封版**：`lesson-10/` 用官方 mcp SDK 建 MCP server/client（工具发现+调用）+ **安全身份注入**（user_id 由 server 侧注入，防 client 越权）+ 用 ACI 原则反哺 capstone 四个工具描述。第一个真从对标书 Ch4 学的课。
- **Reflection 反思范式 ✅ 封版**：给 capstone 补齐 **Planning-Acting-Reflection 闭环**（百度 JD1/3 点名）。新建 [`reflect.py`](capstones/stage2-customer-service-agent/reflect.py) LLM-as-judge 质检节点——答复发出前按红线自审、命中泄露/越权/编造则重写一次（`MAX_REFLECTIONS=1` 防 thrashing）；**质检层 fail-open + 依赖注入可测**，不拖垮已有三道 hard-code 安全线。门禁 13 测试绿（含 fail-open 兜底）。对标书 Ch8 入门形态。
- **最小部署 ✅ 完成**：capstone 服务化——[`app.py`](capstones/stage2-customer-service-agent/app.py) FastAPI `/chat`（认证注入身份、故障优雅降级）+ Dockerfile 容器化（亲手 build/run 打通，踩通镜像加速/保留端口/隐藏 key 依赖/惰性化）。给面试官看的 [capstone README](capstones/stage2-customer-service-agent/README.md) 已就绪。**≈ 投递-ready**。
- **L11 Multi-Agent ✅ 封版**（对标书 Ch10）：[`lesson-11/`](lesson-11/) 多 Agent 代码审查系统——管理者模式+隔离上下文+ThreadPoolExecutor 并行。核心判据=**协作是否引入单 Agent 拿不到的新信息**（故意让 reviewer 带 pyflakes 工具反馈而非堆同模型 LLM）。4 测试绿（含隔离性招牌测试）。呼应：上节 reflect=同模型自审=判据里"通常无效"那行。
- **L12 评估体系 ✅ 封版**（对标书 Ch6）：[`eval/rubric_judge.py`](eval/rubric_judge.py) 把 L7 子串匹配升级为**校准过的 Rubric LLM-as-Judge**（多维度+一票否决 veto），语义区分"确认 vs 纠正假前提"（子串匹配做不到）+ 金标集校准。讲授 Pass@k/Pass^k、统计显著性(标准误/配对分析)、可观测性回流评估资产。**可观测性已实操**：LangGraph 版接 [Langfuse](capstones/stage2-customer-service-agent/agent_langgraph.py) 全链路 tracing。
- **下一步（校招优先，边投边学）**：投递 + L13 可观测/成本/延迟深化 + Agent Harness（JD2）。
- **Advanced Track**（边投递边学）：L11 Multi-Agent · L12 评估（LLM-as-judge） · L13 可观测性/成本/延迟/重试限流 · **L13.5 Agent Harness**（沙箱/执行约束/上下文交接/长任务稳定，Claude Code 锚点）· L14 服务化与安全。
- **追补 + 校招加分**：L8 补 Reflection 反思范式；研究向（Coding Agent/RL/self-improvement/多模态 = 书 Ch5/7/8/9）按校招加分权重穿插；开源贡献纳入。

> 🎯 **完整大纲、当前位置、每项来源（JD 计划 / 对标书 / 校招加分）见 [ROADMAP.md](ROADMAP.md)。**

> 📚 **对标教程**：引入 [bojieli/ai-agent-book](https://github.com/bojieli/ai-agent-book)（10 章 / 93 项目 / 中文优先）作**参照脊柱、按主题精读**——L10 MCP ← Ch4 · L12 评估 ← Ch6 · L11 多智能体 ← Ch10。框架 / 部署 / 可观测性书未覆盖，仍按 JD 走。浅克隆在 `reference/repos/`（不入库）。

## 教学方法

1. **二八原则**：先攻覆盖 80% 场景的 20% 核心。
2. **coaching 式**：给提示不给答案；撞坑后「看真实值、找物证」debug——**翻车是核心教学资源**。
3. **作业「带着盖楼」**：先讲多文件蓝图 → 从空文件一小块一小块引导手写；教练只给接口契约（签名 + 输入输出 + 约束），实现由学习者补。重在建立**整体代码结构**的心智模型。
4. **每节封版三门禁**：环境可复现 / 至少 1 正 1 反测试绿 / 无调试残留。
5. **生产级规范**（学习者硬性要求）：不教玩具实现；确需简化必说明「生产怎么做、差距在哪」。
6. **求职嵌入**：讲到 JD 高频点标注「X/10 的 JD 要求」；踩坑与权衡沉淀进 [interview-notes.md](interview-notes.md)。
7. **节奏归学习者**：一节收尾即停，不抢跑。

## 技术环境

- **Python 3.12**，依赖管理用 **[uv](https://github.com/astral-sh/uv)**（已从 conda 迁移）。
- 复现环境：`uv sync`；跑代码：`uv run python xxx.py`；装包：`uv add X`。
- API key 走环境变量 `DEEPSEEK_API_KEY` 或本地 `deepseek_api.txt`（已 gitignore，不入库）。

## 目录结构

```
learning-agent-development/
├── PROGRESS.md              # 跨机交接：进度 + 画像 + 下一步（权威，续学先读）
├── README.md                # 本文件：静态总览
├── ROADMAP.md               # 全景路线图（大纲 + 当前位置 + 每项来源：JD 计划 / 对标书）
├── COURSE-OVERVIEW-v3.md    # 课程设计说明（两轨制，当前权威设计版）
├── interview-notes.md       # 面试素材本（按「面试官会怎么问」组织）
├── resources.md             # 精选信息渠道
├── Requirements/            # 11 份目标岗位 JD + 大纲反向调整分析
├── reference/               # 参考（模型选型等）
├── eval/                    # RAG 评估集（L7 起，养到 L12；含越权 / 无法回答 / 对抗分区）
├── anchor-notes/            # 源码锚点笔记（smolagents 等）
├── reference/repos/         # 浅克隆参照仓库（smolagents · ai-agent-book；gitignore 不入库）
├── lesson-01/ … lesson-08/  # 每节：notes.md · quiz.md · summary.pdf · homework/
└── capstones/
    └── stage2-customer-service-agent/   # 阶段二 capstone（裸 SDK 版封版）
        ├── DESIGN.md                    # 施工图 + 未来增强
        ├── tools.py / agent.py / policy_rag.py / main.py
        ├── calibrate_threshold.py       # RAG 阈值从 eval 分布标定
        └── test_tools.py / test_policy.py  # 10 条正反 + mock
```

## 续学入口

跨机（macOS / Windows 双机）同步：先 `git pull` → 读 [PROGRESS.md](PROGRESS.md) 确认断点 → `uv sync` → 按「下一步」行动 → 收尾 commit 后 `git push`。
