# 学习：Agent 开发

用「先摸底 → 二八原则切入 → 边做边测边留痕」的方式系统学习 Agent 开发。
终点定在 **Advanced(第 4 级)**：能独立设计并搭出一个 production 级客服 agent，
懂每个组件的权衡，能在面试里讲透细节。

- **学习者画像**：会 Python、调过大模型 API、懂 LLM 原理。为求职而学，重项目细节与落地。
- **默认模型**：DeepSeek（OpenAI 兼容接口，写法可迁移到通义千问/GPT）。
- **节奏**：每周 5–10 小时，边做边讲。

## 五级阶梯

1. **Layman** — 说清 agent 与普通调 LLM 的区别（LLM + 工具 + 记忆 + 循环）。
2. **Beginner** — 手写 agent loop，让模型调用工具完成多步任务。← 核心 20%
3. **Intermediate** — RAG、记忆与上下文长度管理、多工具编排，搭出客服原型。
4. **Advanced** — 上下文工程、评估、错误处理、成本/延迟/可观测性，打磨成上线级项目。
5. **Expert** — 多智能体、自研框架、前沿（本课不覆盖，拓展）。

## 课程大纲与进度

| 阶段 | 等级 | 课程 | Capstone | 状态 |
|---|---|---|---|---|
| 一 | Layman→Beginner | ~~L1 什么是 agent~~ ✅ · L2 手写 agent loop · L3 tool use · L4 多工具 | 命令行多工具 agent | 🔵 进行中 |
| 二 | →Intermediate | L5 记忆与状态 · L6 上下文长度管理 · L7 RAG · L8 客服原型 | 知识库客服 agent 原型 | ⚪ 未开始 |
| 三 | →Advanced | L9 评估 · L10 错误处理 · L11 成本/延迟/可观测性 · L12 打磨 | 可部署客服 agent（求职主力） | ⚪ 未开始 |
| 四 | 拓展 | L13 多智能体 · L14 框架对比 · L15 前沿 | 选做 | ⚪ 未开始 |

## 当前进度

- **当前等级**：Beginner（起步）
- **当前课程**：L2 — 手写 agent loop
- **已完成**：L1 什么是 agent（quiz 5/5 达标，环境跑通 hello_llm.py）
- **最近更新**：2026-07-13

## 目录结构

```
learning-agent-development/
├── README.md          # 本文件：大纲、进度、等级追踪
├── resources.md       # 5 个精选信息渠道
├── lesson-01/
│   ├── notes.md       # 讲义
│   ├── quiz.md        # 题目与答案
│   ├── summary.pdf    # 本节 PDF 总结
│   └── homework/      # 作业与解答
└── capstones/         # 各阶段 capstone 项目
```
