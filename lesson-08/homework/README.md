# L8 作业：生产级 ReAct executor + Plan-and-Execute 对比

## 这个作业在练什么

Quiz Q4 你找出了 4 个通用工程问题，但**本节课刚讲的 4 条一个没提**（`stop_reason`、
fatal 分流、no-progress、print 残留）。这个作业就是把那 4 条从"读过"变成"写过"。

---

## 环境（门禁条件 1：环境可复现）

```bash
uv sync
```

需要的环境变量：

| 变量 | 用途 |
|---|---|
| `DEEPSEEK_API_KEY` | 对话与规划模型 |

检查一下（Windows PowerShell）：

```bash
uv run python -c "import os; print(bool(os.environ.get('DEEPSEEK_API_KEY')))"
```

跑测试：

```bash
uv run pytest lesson-08/homework -v
```

跑对比实验（Part C，会真调 API 花钱）：

```bash
uv run python lesson-08/homework/compare.py
```

---

## 文件分工

| 文件 | 谁写 | 说明 |
|---|---|---|
| `tools.py` | **我给全** | 四个假工具 + 三类错误异常（`BusinessError` / `TransientError` / `FatalError`） |
| `executor.py` | **你写**（7 个 TODO） | Part A：`LoopGuard`（纯逻辑）+ `run_react`（接线） |
| `planner.py` | **你写**（5 个 TODO） | Part B：`PLAN_SCHEMA` + `parallel_groups`（纯逻辑）+ `run_plan_execute` |
| `test_executor.py` | **我搭骨架，你补断言**（10 个 TODO-T） | 假客户端已写好，断言你来补 |
| `compare.py` | **半给**（3 个 TODO-C） | Part C：实测对比 |
| `findings.md` | **你写** | 对比结论，会摘进 `interview-notes.md` |

---

## 建议顺序

**Part A → 测试跑绿 → Part B → Part C。** 别跳。

Part A 做完就能跑 `python executor.py` 看到真实效果，先拿正反馈；
测试绿了再往下走，否则 Part B 会在一个没验证过的地基上盖楼。

---

## 关键提示（不给答案，给方向）

1. **`LoopGuard` 里不许 import openai。** 一旦它碰了网络，就没法用纯单测覆盖。
   这条是 Part A 的设计红线，也是 L6 你已经练过的手法。
2. **token 用 `response.usage.prompt_tokens` 真实值。** 不许估算——你自己提的要求。
3. **每条退出路径都要 return。** 这是你出现 5 次的头号短板，`test_content_none_is_handled`
   就是专门钉它的。
4. **规划那次 LLM 调用的 token 也要算进总数。** 不算的话 Part C 的对比就是自欺欺人。
5. 撞上端点不支持 `response_format: json_schema` 别慌，降级到 `json_object` + 自己校验，
   **把这个过程记下来**——这是很好的面试素材。

---

## 封版自检清单（v3 三条门禁，不满足不封版）

跑之前先 `grep -rn "TODO" lesson-08/homework` 数一遍还剩几个。

- [ ] **门禁 1 · 环境可复现**：`uv sync` 后按本 README 能一次跑通；key 从环境变量读，
      没有硬编码；`compare.py` 和 `executor.py` 都能跑起来
- [ ] **门禁 2 · 测试通过**：`uv run pytest lesson-08/homework -v` 全绿，
      且至少含 1 个正常路径 + 1 个失败路径（实际应该远不止）
- [ ] **门禁 3 · 无调试残留**：`grep -rn "print(" lesson-08/homework/*.py` 应该只在
      README 里出现；无注释掉的死代码；无硬编码 key
- [ ] `executor.py` 7 个 TODO、`planner.py` 5 个、`test_executor.py` 10 个、
      `compare.py` 3 个 —— **共 25 个，逐一确认处理完**
- [ ] `findings.md` 四个问题都回答了
- [ ] `git diff` 扫一眼再 commit（历史上误提交过 key 文件）

---

## 交付物

1. `executor.py` / `planner.py` 实现完整
2. `test_executor.py` 断言补齐、全绿
3. `findings.md`：对比数据表 + 四问回答 + 一段 ≤150 字的面试话术
4. （可选但推荐）跑一次 `max_replans=0`，把"机械执行过时计划"的现场截下来放进 findings

---

## 卡住了怎么办

按顺序自查，别一上来就问我：

1. **环境问题**：`uv run python -c "import sys; print(sys.executable)"` 确认在哪个 python
2. **API 问题**：先 `repr` 打出真实返回值再判断（L6 你就是这么找到 `content=''` 的）
3. **测试红了**：先看断言里**期望值**是不是你自己写错了，再怀疑实现
4. 卡超过 30 分钟再来问我，但**带上你试过什么、看到了什么真实值**
