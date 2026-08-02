# 学习路线图 · Agent 开发

> 本文件是**全景地图**：我在哪、下一步、每一项从哪学。
> 实时断点/下一步以 [PROGRESS.md](PROGRESS.md) 为准；本文件相对静态，每次 push 随 README 一起更新。
> 最近更新：2026-07-29（capstone 裸 SDK 版封版 · L9 起步 · 引入对标书）

## 一句话策略

按目标岗位 JD 反排大纲为主干，引入对标教程
[bojieli/ai-agent-book](https://github.com/bojieli/ai-agent-book) 作**参照脊柱、按主题精读**——
只在重合主题把书当权威主线；书缺的工程硬需求（框架/部署/可观测性）按 JD 走。

> **⚠️ 定位更新（2026-07-29）**：**校招/应届为主（在校生），社招兼顾**。
> 新增 4 个**百度校招高优先岗**（AIDU 全栈/Agent Harness/智能体算法/大模型研发，见 `Requirements/百度2027校招-Agent岗位4则.txt`）。
> **影响**：研究向内容（RL/self-improvement/多模态 = 书 Ch7/8/9）从"长期作战"上调为**校招加分（投递前尽量碰）**；
> **加分项（开源贡献/论文/竞赛）纳入规划**。工程核心仍先走完保底。

## 图例（来源）

| 标记 | 含义 |
|---|---|
| 🟦 | **原有 JD 计划**——书里没有或不作主线 |
| 🟩 | **GitHub 书主线**——ai-agent-book 对应章为权威主线 + 跑它的项目 |
| 🟨 | **融合**——原计划主题，用书对应章大幅加厚 |
| ⬜ | **长期作战**——第一轮投递后再碰，多为书的研究向章 |

进度标记：✅ 完成 · 🚧 进行中 · ⬜ 待学

---

## 当前位置

```
Layman ─ Beginner ─ [Intermediate ✅ 已扎实] ─▶ [Advanced 🚧 当前, L9✅ → L10] ─ Expert(不追)
                     L1–L8 + 两个 capstone            框架/评估/部署/可观测
```

**手里的资产**：可写进简历的完整客服 Agent（三类能力 + 三道安全线 + 10 pytest + 封版）
+ **L9 框架对比 ADR**（裸 SDK vs LangGraph，`ADR-001-langgraph-vs-bare-sdk.md`，校招"能分析框架优劣"的直接证据）。

---

## 全景大纲

### ✅ 已完成（L1–L8 + 两个 capstone；均在引入书之前，纯原计划）

| 课 | 主题 | 来源 | 书对应(已学过,不重学) |
|---|---|---|---|
| L1 | 什么是 agent | 🟦 | Ch1 |
| L2 | 手写 agent loop（本质即 ReAct） | 🟦 | — |
| L3 | tool use 深入（多工具/链式/错误回传/循环上限） | 🟦 | Ch4 |
| L4 | 多工具编排 + **阶段一 capstone** | 🟦 | — |
| L5 | 记忆与状态（跨重启） | 🟦 | Ch3 |
| L6 | 上下文长度管理 + Prompt/结构化输出 | 🟦 | Ch2 |
| L7 | RAG 与向量数据库 | 🟦 | Ch3 |
| L8 | 路由/ReAct/Planning + smolagents 锚点 | 🟦 | — |
| 🎯 | **阶段二 capstone 客服 Agent（裸 SDK 版封版）** | 🟦 | — |

> 🔴 **L8 待追补（百度 JD 缺口）**：L8 讲了 ReAct + Plan-and-Execute，缺 **Reflection 反思**（JD1"Planning-Acting-**Reflection** 闭环"、JD3"反思"点名）。补 **Reflexion 范式**（执行后自我批判→修正），落地为 capstone 的 reflection 节点。接书 Ch8。

### 🚧 当前 / ⬜ 将学 · Core Track（封版即投递）

| 课 | 主题 | 来源 | 书对应 / 说明 |
|---|---|---|---|
| L9 ✅ | 框架对比：横扫 LangChain/LlamaIndex/AutoGen/CrewAI 定位 + LangGraph 重写切片 → **ADR** | 🟦 | 已封版：`agent_langgraph.py` + `ADR-001`（结论=编排层用裸 SDK） |
| **L10 🚧下一课** | **MCP 协议**与工具集成边界 | 🟩 书主线 | **Ch4**（7 项目：感知/执行/协作三类 + 事件驱动异步）——**第一个真从书学的课** |
| — | Core capstone 升级 + 最小部署 | 🟦 | — |

### ⬜ 将学 · Advanced Track（边投递边学）

| 课 | 主题 | 来源 | 书对应 |
|---|---|---|---|
| L11 | **Multi-Agent 多智能体协作** | 🟩 书主线 | **Ch10**（7 项目：协作框架/上下文共享隔离/Agent 社会） |
| L12 | **评估体系**（LLM-as-judge、工具准确率、任务完成率） | 🟨 融合·书加厚 | **Ch6**（11 项目：GAIA/SWE-bench/TAU2/OSWorld + 统计显著性） |
| L13 | 可观测性/成本/延迟 + **API 重试/超时/限流(429)** | 🟦 | 书缺，按 JD 走 |
| **L13.5 🆕** | **Agent Harness 专题**（沙箱/执行约束/上下文交接/compaction/可读可控可验证/长任务稳定/人-模-体反馈闭环） | 🟦 | 书缺；**JD2 整篇 + 沃孚 JD**，25 人在招 |
| L14 | 服务化部署 FastAPI+Docker（+**K8s** JD4 优先）+ Agent 安全（prompt 注入测试） | 🟦 | 书缺，按 JD 走 |
| 🎯 | **阶段三 capstone：上线 + 简历/面试包装** | 🟦 | — |

> 🆕 **L13.5 Agent Harness（新增专题，百度 JD2 + 沃孚 JD 两处点名）**：把散落的 compaction(L6)/可观测(L13)/沙箱安全(L14) **收拢成"Harness 设计"视角**——Agent 长时间高复杂度执行怎么做到可读、可控、可验证。**你正用 Claude Code（本身就是一个 harness）学 agent，是一手素材** → 做一个 **Claude Code 源码锚点**（读它怎么做 context 管理/sandbox/执行约束），既学 Harness 又是简历亮点。

### ⭐ 校招加分 · 研究向（**投递前尽量碰一层**，校招加分项，权重已上调）

| 主题 | 来源 | 书对应 | JD 出处 |
|---|---|---|---|
| Coding Agent（代码生成 / agent 自造工具） | 🟩 | **Ch5**（12 项目） | JD3 职责"代码生成" |
| 模型后训练 SFT / **RL(PPO/DPO)**、工具内化 | 🟩 | **Ch7**（16 项目） | JD3 加分 |
| 持续进化 / **Self-Improvement**（从执行轨迹学习） | 🟩 | **Ch8**（8 项目） | JD1 前沿 |
| 多模态 / 实时交互（语音/GUI/物理世界） | 🟩 | **Ch9**（7 项目） | JD1 前沿"多模态 Agent" |
| 规划算法 A* / MCTS · World Model · Tool Learning | 🟦/🟩 | Ch7/8 | JD1,3 前沿/加分 |

> 校招 3 个 AIDU 岗都是研究向，加分项含**顶会论文/开源贡献/竞赛**——上面这些"碰过一层、能讲"就比多数应届生突出。不求全精，求**有实验、有观点**。

### 🎖️ 加分项动作（非课程，贯穿始终）

- **开源贡献**：从已在读的 [smolagents](reference/repos/) / [ai-agent-book](reference/repos/) 入手，提 issue/PR（JD2/JD3 加分：开源 Agent 项目贡献）。
- **作品集**：capstone 本身就是；上线 + 写清 README/ADR = 面试可展示的项目。
- 竞赛 / 论文视精力，非必需。

### ⬜ 更远 · 选做（第一轮投递后）

| 主题 | 来源 | 书对应 |
|---|---|---|
| KV Cache 深度 · vLLM 推理优化 | 🟩/🟦 | Ch2 |
| 高并发分布式 · 前沿跟踪 | 🟦 | — |

---

## 已掌握 vs 接下来

**已成闭环**：Agent 本质与 ReAct loop · 多工具编排/路由 · 长期记忆 · 上下文压缩 · Prompt/结构化输出 ·
RAG 全链路 + 阈值分布标定 · 生产级判断（安全 hard-code、越权注入防线、终态工具+停机、单测/mock/可测性、门禁封版）。

**仍需盯的短板**：多部分任务"改一半/漏 return" · Python 基本功（`is` vs `==`）· 多文件项目结构心智（"带着盖楼"补中）。

**最近几步**：
1. ✅ **L9 框架**——横扫四大框架 + LangGraph 重写 `run()` 成图 → **ADR-001**（结论=编排层用裸 SDK）。🟦
2. 🚧 **L10 MCP**（下一课）——用书 **Ch4** 当主线精读 + 跑项目。🟩（第一个真正"从 GitHub 书学"的课）
3. ⬜ **Reflection 追补**（小）——给 capstone 加 reflection 节点（Reflexion 范式），补 JD1/3 反思闭环。🟦
4. ⬜ **L12 评估**——用书 **Ch6** 加厚，接上 L7 的 `eval/` 评估集。🟨

## 书怎么用（参照脊柱机制）

到 🟩/🟨 主题时，流程同"源码锚点"升级版：**精读书对应章 → 跑它的可运行项目 → 对照写进 interview-notes**。
浅克隆在 `reference/repos/ai-agent-book/`（`chapter1-10/`=项目，`book/`=中文讲义；已 gitignore 不入库）。
