# L1 作业 —「拆解一个 agent」

L1 还没写代码，作业是**动脑 + 动手观察**，为 L2 手写 loop 做准备。

## 任务 A：给你身边的一个真实场景设计 agent（必做）

选一个你**工作中真实存在的痛点**（客服、查数据、写周报、整理邮件……任选）。用不超过
半页纸回答：

1. 目标是什么？（一句话）
2. 它需要哪些 **tools**？（列 2–4 个，写清每个工具「输入什么、输出什么」）
3. 画出它一次典型运行的 **loop**：至少 2 轮「想→做→看」，用中文描述每轮。
4. 灵魂拷问：这个任务**真的需要 agent 吗**？还是一次 LLM 调用 / 简单流程就够？给出你的
   判断和理由。

把答案写成 `homework/task-a.md`。

## 任务 B：环境准备（必做，为 L2 铺路）

1. 注册一个国内模型 API（推荐 DeepSeek：https://platform.deepseek.com/ ，注册送额度、
   便宜），拿到 API key。
2. 建一个 Python 虚拟环境，装好 SDK：
   ```bash
   pip install openai        # DeepSeek 兼容 openai 接口，用这个即可
   ```
3. 跑通一个「最小调用」：给模型发一句「你好」，打印它的回复。代码存成
   `homework/hello_llm.py`。
   > 提示：DeepSeek 用 openai 库时，`base_url="https://api.deepseek.com"`，
   > `model="deepseek-chat"`。**不要把 API key 硬编码进代码**，用环境变量读
   > （`os.environ["DEEPSEEK_API_KEY"]`）——这是个好习惯，面试也会看。

## 提交方式

把 `task-a.md` 和 `hello_llm.py` 放进本文件夹。完成后告诉我，我会给你反馈、判断能否进
L2。跑通任务 B 你就已经踩到 Beginner 的门槛了。
