# 课程说明：Agent 开发（面向国内社招求职）

> 用途：课程的稳定版说明，供在外部工具里优化课程时作输入，也便于优化后 diff。
> 权威进度以 `PROGRESS.md` 为准；本文件是面向"优化课程设计"的高层概述。

## 一、主题与目标
从零到能独立设计、搭建 **production 级客服 Agent**。终点定在五级体系第 4 级 **Advanced**：
懂每个组件的权衡取舍，面试能讲透细节，能处理非标准情况、能做设计决策。不追第 5 级 Expert。

## 二、学习者画像
- 基础：会写 Python、调过大模型 API、懂 LLM 原理；**工程基本功偏弱**（环境管理、代码完整性）。
- 动机：**国内社招求职**唯一目标，1-3 个月投一轮，不排除长期作战。重视"简历能写、面试能讲透"。
- 时间：每周 5-10 小时。
- 偏好：**边做边学、不看答案、用填空骨架自己补核心逻辑（coaching 式，给提示不给答案）**。

## 三、教学方法（核心，勿改）
1. 二八原则：先攻覆盖 80% 场景的 20% 核心。
2. coaching 式：作业给填空骨架，撞坑后"看真实值、找物证"debug——**翻车是核心教学资源**。
3. 每节固定节奏：讲授 → quiz → 作业 → 确认封版 → PDF 总结 → commit 留痕。
4. 节奏归学习者：一节收尾即停，不抢跑，等他说"开始下一课"。
5. **生产级规范（学习者硬性要求）**：不教玩具实现；确需简化必说明"生产怎么做、差距在哪"。
6. 求职嵌入：讲到 JD 高频点标注"X/10 的 JD 要求"；踩坑沉淀进 `interview-notes.md`。
7. JD 反向优化：大纲按 11 份目标岗位 JD 需求频次重排（社招为主，大厂校招 JD 作参考系）。

## 四、掌握等级（学习者当前在第 3 级，目标第 4 级）
1 Layman → 2 Beginner → **3 Intermediate（当前）** → **4 Advanced（终点）** → 5 Expert（不追）

## 五、大纲与进度
### ✅ 阶段一（完成）
L1 什么是 agent · L2 手写 loop · L3 tool use · L4 多工具编排 + capstone（命令行多工具客服 agent）
### 🔵 阶段二（进行中）
- ✅ L5 记忆与状态　- ✅ L6 上下文管理 + Prompt/结构化输出
- 🔶 **L7 RAG 与向量数据库（当前：讲授完成，quiz/作业未做）** JD 8/10 最高频
- ⬜ L8 任务规划 ReAct/Plan-and-Execute · L9 用 LangChain 重写项目 · L10 MCP
- 🎯 阶段二 capstone：简历级客服 Agent（remember+压缩+RAG+路由+单元测试合体）
### 🟢 阶段三（未开始）
L11 Multi-Agent · L12 评估 · L13 可观测性/成本/延迟（含 API 层重试/超时/限流）·
L14 服务化部署 FastAPI+Docker（含 Agent 安全基础）· 🎯 capstone：上线 + 简历/面试包装
### ⚪ 长期作战
高并发深化 · 模型微调 · 多模态 · 推理优化 · 沙箱安全

## 六、技术环境
- **对话模型**：DeepSeek 系。**当前端点仅 `deepseek-v4-pro` / `deepseek-v4-flash`**（无 deepseek-chat）；
  OpenAI 兼容接口，写法可迁移。key：`DEEPSEEK_API_KEY`。
- **OpenAI（新增，可选）**：学习者已开通 OpenAI API。用途：DeepSeek 端点**没有 embedding 接口**，
  故 **L7 RAG 的 embedding 用 OpenAI `text-embedding-3-small`**；也可整体切到 OpenAI（`gpt-4o-mini` 等）。
  key：`OPENAI_API_KEY`。**embedding 与生成解耦，可用不同厂商——这是地道的生产模式。**
- Python 3.12，conda 环境 `agent`；两台机器（macOS `/Users/el4435/...` + Windows `E:\Agent\...`）共用远端仓库 B6nux9 接力。
- 留痕：本地 git，每节 `lesson-XX/{notes,quiz,summary.pdf,homework}`；跨 session 交接靠 `PROGRESS.md`。

## 七、学习者短板（优化时重点关注）
1. **多部分任务只做一半**（头号，出现 4 次）：漏兜底 return、校验了没存值、改一半。
2. 混血 messages 列表（dict + SDK 对象）。
3. 调试残留忘清理。
4. 环境管理（哪个 python / key 在不在 / VSCode 环境快照坑）。

## 八、产出物
- 每节：`lesson-XX/{notes.md, quiz.md, summary.pdf, homework/}`
- 全局：`PROGRESS.md`（进度交接）、`interview-notes.md`（面试素材）、`reference/模型选型.md`、
  `Requirements/`（11 份 JD + 分析）、本文件 `COURSE-OVERVIEW.md`
