# L2 讲义:手写 agent loop

> 讲义 = 教学时的「课本」,边学边对照回看。真实课堂里展开的例子、追问也收进来。

## 0. 本节目标
从零手写一个**能用的 agent loop**——让模型能「先用工具、拿到真实结果、再回答」,并自动重复多轮直到问题解决。落地场景:查订单迷你客服 agent。

## 1. L1 的代码为什么还不算 agent?
L1 的 `hello_llm.py` 只有「LLM」一个部件,缺了工具、记忆、循环。它像只会背书的客服:需要「去查订单系统」时只能抓瞎、只能编。

Agent loop 要解决的一句话:
> 让模型能「先去用个工具、拿到真实结果、再回答」,而且这个过程能自动重复多轮,直到问题真正解决。

## 2. 核心机制:function calling 的「四步握手」(本节最重要的 20%)
以「用户问:订单 A123 到哪了」为例:

```
第1步  你 → 模型:   用户问题 + 工具说明书("你有个工具 query_order(order_id)")
第2步  模型 → 你:   不直接答,而是"点单":要调 query_order,参数 order_id='A123'
第3步  你(本地)：   真的执行 query_order("A123") → {"status":"运输中","eta":"明天"}
第4步  你 → 模型:   把结果塞回 messages → 模型这才给最终答复
```

**命脉分工**:模型负责「决策」(点哪个单、传什么参),你的代码负责「行动」(真正执行)。模型**不会**自己连数据库。

## 3. 循环在哪里?——agent loop 骨架
一次工具不一定够(调完 A 工具可能还要调 B)。把第 2~4 步包进 `while`:

```
while True:
    发 messages(+tools)给模型
    若这轮【没有】tool_calls  → 拿到最终答案,break/return
    若【有】tool_calls        → 逐个执行工具,结果 append 回 messages,继续下一轮
```

三个关键点:
1. **`messages` 数组 = agent 的记忆/状态**。用户问题、模型点单、工具结果、模型回答,每步都 append 进去。→ 这个数组会越滚越长,正是 L6「上下文长度管理」的源头。
2. **停止条件**:靠「模型不再点单」跳出(`if not msg.tool_calls: return`)。生产里再加**循环次数上限**兜底,防死循环烧 token。
3. **append 顺序不能乱**:模型的 `tool_calls` 消息、和对应的 `tool` 结果消息,必须成对按序进数组,否则 API 报错。

## 4. 课堂追问:TOOLS schema 到底是什么?
```python
TOOLS = [{
    "type": "function",
    "function": {
        "name": "query_order",           # 靠它和真实函数对上号(路由的线)
        "description": "根据订单号查询物流状态...",  # 给模型看的"何时该用我",决定调不调
        "parameters": {                  # 一段 JSON Schema,描述"要传什么参数"
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "订单号,例如 A123"}},
            "required": ["order_id"],
        },
    },
}]
```
- schema 是给**模型**看的「菜单」,本身**不执行**任何东西;真正干活的是 `def query_order`。
- `description` 不是注释,是**指令**——写得越准,模型「该调不调 / 不该调乱调」的决策越准(面试考点:如何提升工具调用准确率 → 打磨 description)。
- `parameters` 里的参数名(`order_id`)必须和真函数签名一致,否则 `**args` 拆开时对不上。
- 串联:`def query_order` ↔(name)↔ TOOLS schema →(发给模型)→ 模型点单 → `AVAILABLE_TOOLS[name](**args)` 执行。
  一句话:**schema 是菜单,AVAILABLE_TOOLS 是后厨路由表,name 是对上号的那根线**。

## 5. 课堂追问:环境变量里怎么设 API key?(延续 L1 环境短板)
- **Windows PowerShell**:`$env:DEEPSEEK_API_KEY="sk-..."`(临时,关窗即失);永久用 `setx DEEPSEEK_API_KEY "sk-..."`(设完要**新开**终端才生效)。
- **macOS zsh**:`export DEEPSEEK_API_KEY="sk-..."`(临时);永久写进 `~/.zshrc`。
- **铁律**:`os.environ[...]` 读的是**运行 python 那个终端**的环境变量 → 设 key 和跑代码必须在**同一个终端会话**。最常见翻车:A 窗口设 key、B 窗口跑代码 → KeyError。
- 验证:PowerShell `echo $env:DEEPSEEK_API_KEY` / zsh `echo $DEEPSEEK_API_KEY`。

## 6. 关键心智模型(本节最该带走的一条)
**你和 LLM 之间没有「持续连接」**。每次 `create(...)` 都是独立、无状态的一次性请求,模型天生不记得上一轮。它「看起来记得」,是因为**你每轮把整个 messages 重新发了一遍**。
→ 记忆不在模型那边,在**你手里的 messages 数组**。谁维护记忆?你。这是 L5「记忆与状态」的地基。

## 7. 作业
见 `homework/order_agent.py`:周边零件已搭好(客户端、TOOLS schema、假订单库、执行函数),**agent loop 挖空**留给学习者补。跑通标准:单订单能查、双订单能查(一轮两次点单)、「几点下班」不调工具直接答。
