# R1 · Quiz(讲评版)

> ⚠️ **状态:未亲答**。当天信息量到顶,学习者选择听讲评("今天我负责记忆"),四题由教练作答讲解。
> **按课程规矩,R2 开工前先过 4 道变式题,过了 R1 才算 quiz 关闭。**下面是原题 + 参考答案。

## Q1:researcher ⇄ researcher_tools 之间为什么零条 add_edge?LangGraph 靠什么知道边存在?

路由决定权在节点手里(`Command(goto=...)` 运行时才定),静态边无法表达"有时回循环、有时去压缩"。编译期靠**返回类型注解** `Command[Literal["researcher", "compress_research"]]`——框架读 Literal 注册可能目的地。`add_edge` 声明静态边,Command + 类型注解声明动态边。

## Q2:误删 researcher_messages 的 reducer,哪个测试最先挂、断言什么值时挂?

变覆盖语义,每次 update 替换整个列表:`[AI₁]` → `[Tool₁]`(AI₁ 没了)→ `[AI₂]` → 早退。最先挂 `test_happy_path_search_then_finish` 的 `assert len(msgs) == 3`,实际值 **1**。注意 `test_research_complete` 会侥幸通过(只断言末条是 tool 回执)——单条断言探不出状态管理的病,要靠"数总数"的全局断言。

## Q3:think_tool 一行拼接,价值在哪?与 stage2 reflect.py 的本质区别?

价值在位置和时机:bind_tools 把"反思"变成模型的合法动作,模型被迫把"找到什么/还缺什么/继不继续"显式写进参数,随回执进入消息历史——塑造下一轮决策,且可审计可回放。一句话:**think_tool 是行动之间的强制停顿,改善决策过程(事前、循环内);reflect.py 是产出之后的质检员,拦截坏结果(事后、循环外)**。

## Q4:把 +1 挪到 researcher_tools(执行完才计数),行为什么变化?哪个测试变?

①名实相符了(早退轮不计数);②但检查读到的是本轮增量未合并的旧值——`max=1` 时第 1 轮读 0 不退、第 2 轮才读到 1,**多跑一整轮**(off-by-one)。`test_budget_forces_exit` 挂:2 条消息变 4 条。记忆点:**计数点和检查点的相对位置就是预算的松紧**;源码"researcher 计数、researcher_tools 检查"= 检查时增量已合并,预算精确。

---

## 附:课中辩题(已由学习者参与推导)

- 热身 1(Command vs add_edge):答对一半——"researcher 里干活的是 update"正确;Command 优势的完整论证(动态路由 + 决策在信息处)课上补齐。
- 热身 2(预算检查前置 vs 后置):方向(厚道)对,机制错(误用 token 论证)——正解:消息历史完整性 + 最后一轮结果不浪费。
- 辩题(覆盖+全量 vs reducer 等价性):**学习者自己推出"删 reducer 后交全量等价"**,教练补 R3 并发场景下等价性碎裂(InvalidUpdateError)。此条质量高,记 findings。
