---
title: "L1 总结 — 什么是 Agent"
---

# L1 总结：什么是 Agent？

> 这是 L1 封版后的总结，既收录讲义要点，也记录了这节课**真实发生**的讨论、你的 quiz
> 表现，以及一段占了大半时间、非常有价值的环境排错实战。

## 一、核心概念（讲义要点）

- **Agent = LLM（大脑）+ Tools（手脚）+ Memory（记忆）+ Loop（循环）。** 核心是那个
  「想 → 做 → 看结果 → 再想」的循环。
- 普通调 LLM 是**一次性一问一答**；agent 是给一个**目标**，模型**多步自主决策、调用
  工具、按中间结果决定下一步**，直到完成。
- **铁律**：LLM 只会输出文字。所谓「调用工具」，是模型输出一段结构化请求，**由你的代码
  真正执行**。模型与真实世界之间永远隔着你写的一层。
- **不是所有任务都该上 agent**：能一次调用搞定的（翻译、摘要、分类）别绕。只有步骤数不
  确定、需动态决策、要与外部系统交互时才划算。这是面试里的工程判断力加分项。

## 二、你的 quiz 表现（5/5 达标）

整体概念非常扎实，4 题满分，1 题有一处关键纠正：

- **唯一被纠正的点**：你写「agent 调用 LLM 只有一次」——**错**。正确理解是：普通调用总共
  只调 1 次 LLM；**agent 的循环里每转一圈就调 1 次，一个任务可能调 3、5、10 次**。你在 Q5
  自己给的例子其实就调了 3 次。（这也是后面 L11 讲成本/延迟的伏笔——agent 贵就贵在反复调模型。）
- **满分亮点**：Q2 你答对「是 agent 的代码连的数据库，不是模型」，抓到了「隔一层」的本质；
  Q3 你还超纲说出了 **ReAct** 这个名字（Reasoning+Acting，loop 的经典套路）；Q4/Q5 判断和
  多轮循环描述都清楚。

## 三、作业亮点（task A）

你为客服场景设计 agent 时，自发冒出两个「超前意识」，值得记住：

1. **「客户的问题是否需要模糊处理？」** —— 用户不会照 QA 原文提问，字面匹配会失败。**这正是
   L7 RAG / 向量检索要解决的问题**，到时会点回这里。
2. **「QA 查不到就转人工」的兜底逻辑** —— 真实客服 agent 里「不知道就老实转人工」比硬编答案
   更重要，是安全设计。

## 四、这节课真正的大头：环境排错实战（务必内化）

作业「跑通 hello_llm.py」表面简单，你却踩遍了新手环境问题的全套坑。这段排错比代码本身更
值钱，因为真实开发天天要判断「我在用哪个 python、包装哪去了」。完整链路：

1. **症状**：`(agent)` 提示符明明在，`python3 hello_llm.py` 却报 `No module named 'openai'`，
   `pip install openai` 还提示装到了系统的 `Python314`。
2. **诊断武器**（这两条要记一辈子）：
   - `python -c "import sys; print(sys.executable)"` —— 看**真正在跑哪个 python**，
     提示符名字会骗人，可执行文件路径才是真相。
   - `conda info --envs` —— 列出所有 conda 环境及其真实路径。
3. **层层揭开的真相**：
   - `python` 指向 `C:\Python314\python.exe`（系统 Python），不是环境的。
   - 用的其实是 **conda 环境**（`$env:CONDA_DEFAULT_ENV=agent`），不是 venv。
   - **终极病根**：`E:\Anaconda\envs\agent` 里**根本没有 python.exe**，只有空的
     `conda-meta/` 和 `etc/`——环境是 `conda create -n agent` 建的**空壳**，于是 `python`
     顺着 PATH 落到系统 Python。
4. **两个必记结论**：
   - **`X -m pip install 某包` 一定装进 X 那个 python 的环境**；装包和运行必须用同一个 python。
   - **`conda create -n 名字` 不带 python**，conda 什么都要显式声明；正确姿势是
     `conda create -n 名字 python=3.12`。
5. **修复**：`conda install -n agent python=3.12` 给空环境补上 python → `conda init powershell`
   让 conda 真正接管 PowerShell → `pip install openai` → 跑通，模型回了句
   「Hello! How can I help you today?」。

## 五、一句话收束

Agent 不神秘：它就是**在一次性调用外面套一个循环、给模型配上工具**。模型只出主意，
干活的是你的代码。下节课（L2）你会把这句话变成真代码——亲手写出第一个 agent loop。
