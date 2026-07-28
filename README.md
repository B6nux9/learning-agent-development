# 学习：Agent 开发

用「先摸底 → 二八原则切入 → 边做边测边留痕」的方式系统学习 Agent 开发。终点定在
**Advanced（第 4 级）**：能独立设计并搭出一个 production 级客服 Agent，懂每个组件的
权衡取舍，能在面试里讲透细节。为**国内社招求职**而学，重项目细节与落地。

- **学习者画像**：会 Python、调过大模型 API、懂 LLM 原理；工程基本功偏弱（环境管理、多文件项目结构）。
- **默认模型**：DeepSeek（OpenAI 兼容接口，写法可迁移到通义千问 / GPT）；RAG 的 embedding 用 OpenAI `text-embedding-3-small`。
- **节奏**：每周 5–10 小时，边做边讲。

> 📍 **实时进度、断点、下一步以 [PROGRESS.md](PROGRESS.md) 为准**（跨机交接文件）。本 README 是相对静态的总览。

## 五级阶梯

1. **Layman** — 说清 agent 与普通调 LLM 的区别（LLM + 工具 + 记忆 + 循环）。
2. **Beginner** — 手写 agent loop，让模型调用工具完成多步任务。← 核心 20%
3. **Intermediate** — 记忆、上下文长度管理、RAG、多工具编排、路由 / ReAct，搭出客服原型。 **← 当前**
4. **Advanced** — 上下文工程、评估、错误处理、成本 / 延迟 / 可观测性、服务化，打磨成上线级项目。 **← 终点**
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

### 🎯 阶段二 capstone —— 简历级客服 Agent（施工中，**当前**）

模拟面试驱动：设计面两轮通过 → 第三轮「带着盖楼」动手搭。综合 L1–L8 全部能力。
代码见 [`capstones/stage2-customer-service-agent/`](capstones/stage2-customer-service-agent/)（[DESIGN.md](capstones/stage2-customer-service-agent/DESIGN.md) 是施工图）。

已盖完 4 块、端到端 4 场景跑绿：

- **`query_order`** — 归属校验（存在 / 越权 / 不存在三分）+ 出口字段塑形。
- **`dispatch`** — 注入落地：`user_id` 由会话代码注入、`order_id` 取模型 args，**两道防线**防越权。
- **`run()`** — 真 ReAct while-loop + `LoopGuard`（轮数上限 + 真实 `usage.prompt_tokens` 预算闸门）。
- **`process_refund`** — 招牌菜：阈值 `≤¥200` **hard-code 在代码**（不让 LLM 判）+ 幂等防重复退 + 超阈值转人工。

下一步：pytest 门禁（自己写）→ RAG 政策答疑 → 真 `escalate_to_human` 工具 → 意图路由。

### ⬜ 待学

- **Core Track**：L9 框架对比（裸 SDK vs LangGraph → ADR）· L10 MCP 与工具集成边界 · Core capstone 升级 + 最小部署。
- **Advanced Track**（边投递边学）：L11 Multi-Agent · L12 评估（LLM-as-judge） · L13 可观测性 / 成本 / 延迟 · L14 服务化与安全（含 prompt 注入测试）。

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
├── COURSE-OVERVIEW-v3.md    # 课程设计说明（两轨制，当前权威设计版）
├── interview-notes.md       # 面试素材本（按「面试官会怎么问」组织）
├── resources.md             # 精选信息渠道
├── Requirements/            # 11 份目标岗位 JD + 大纲反向调整分析
├── reference/               # 参考（模型选型等）
├── eval/                    # RAG 评估集（L7 起，养到 L12；含越权 / 无法回答 / 对抗分区）
├── anchor-notes/            # 源码锚点笔记（smolagents 等）
├── lesson-01/ … lesson-08/  # 每节：notes.md · quiz.md · summary.pdf · homework/
└── capstones/
    └── stage2-customer-service-agent/   # 阶段二 capstone：DESIGN.md + tools/agent/main.py
```

## 续学入口

跨机（macOS / Windows 双机）同步：先 `git pull` → 读 [PROGRESS.md](PROGRESS.md) 确认断点 → `uv sync` → 按「下一步」行动 → 收尾 commit 后 `git push`。
