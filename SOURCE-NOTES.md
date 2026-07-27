# SOURCE-NOTES:开源项目源码解剖笔记

> 课程升级(2026-07-24)后新增。每解剖一个真实开源机制,就在这里记:项目 / 机制 / 关键源码位置 / 我的结论。
> 这份笔记本身就是面试前的复习材料——面试官问「你看过哪些 agent 的真实实现」,答案在这里。
>
> **纪律**:所有条目的源码位置都是**实际拉取核对过的**(带 commit SHA),不是凭记忆。行号以该 commit 为准,自己拉取时可能已漂移。

---

## 模块 2:记忆与上下文管理

### 锚点 A(精读):Aider 的历史摘要 `ChatSummary`
- **项目**:`Aider-AI/aider`(AI 结对编程 coding agent)
- **文件**:`aider/history.py`,类 `ChatSummary`
- **拉取版本**:`main` @ commit `19a7864`(2026-07-24 拉取);本地副本 `lesson-05/sources/aider_history.py`
- **机制一句话**:对话历史超过 token 预算时,**把老消息摘要成一条、近消息原样保留**(head/tail 切分),而不是无脑截断或全量塞。
- **关键源码位置**:
  - `too_big()` `history.py:15` —— 触发判断:`总 token > max_tokens` 才摘要(不是每轮都摘)。
  - `summarize_real()` `history.py:33` —— 核心切分逻辑。
  - head/tail 切分 `history.py:47-67` —— 从尾部往前累加,留下约 `max_tokens // 2` 的「近消息 tail」原样保留,其余「老消息 head」拿去摘要。
  - `history.py:60-61` —— **确保 head 结尾是 assistant 消息**再切(避免切断一对 tool_call/结果 —— 呼应 L2「append 顺序不能乱」)。
  - 递归 `history.py:95` —— 摘要后还超,`depth+1` 再摘一层(depth>3 兜底全摘)。
  - `summarize_all()` `history.py:98` —— 把选中消息拼成 USER/ASSISTANT 文本,交给 summarizer 模型出一条摘要。
- **我的结论**:(待学完补)

### 锚点 B(对照/略读):mem0
- **项目**:`mem0ai/mem0`(给任意 agent 加长期记忆的独立库)
- **文件**:`mem0/memory/main.py`(本地副本待补);拉取 @ `main`(2026-07-24)
- **机制一句话**:(待解剖)独立记忆层,LLM 从对话里**抽取事实**并 add/update/delete 到向量库,与主 agent 解耦。
- **我的结论**:(待补)

### 锚点 C(对照/略读):Letta(原 MemGPT)—— 记忆分层标杆
- **项目**:`letta-ai/letta`
- **机制一句话**:(待解剖)把「有限上下文窗口」类比操作系统的内存分页——core memory(常驻) vs archival memory(外部,需检索调入)。
- **我的结论**:(待补)

---

<!-- 后续模块条目往下加 -->
