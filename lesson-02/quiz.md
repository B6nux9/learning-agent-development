# L2 Quiz —（对齐 Beginner）

先作答，再看文末答案。

**Q1.** Agent loop 和 L1 的一次性调用 `hello_llm.py`，代码上最关键的两处不同是什么？

**Q2.** Tool use 的四步机制是哪四步？（按顺序说）

**Q3.** 模型返回的 `tool_call.function.arguments` 是什么类型？拿到它之后、真正调用你的
函数之前，必须先做什么？

**Q4.** 判断对错并说理由：「把工具结果塞回 messages 时，只要 `role` 写成 `"tool"`、把
结果字符串放进 `content` 就够了。」

**Q5.** 为什么 agent loop 里**一定要加一个「最大轮数上限」**？不加会怎样？

**Q6.（代码阅读）** 下面这段 loop 有一个 bug，会导致 API 报错。指出问题：
```python
while True:
    msg = call_llm(messages, tools)
    if msg.tool_calls:
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = available_tools[tc.function.name](**args)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
        continue
    else:
        print(msg.content)
        break
```

---

## 你的答案

（在这里作答）

---

---

## 参考答案（做完再看）

**A1.**（1）给模型配了 `tools` 参数，模型可以选择「调用工具」而非直接回答；
（2）外面套了 `while` 循环，模型每次要调工具就执行并把结果喂回、再问，直到给最终答案。

**A2.** ① 你声明工具（名字/描述/参数 schema）→ ② 模型返回「要调哪个工具、什么参数」→
③ 你的代码真正执行该工具 → ④ 把结果作为 `role:"tool"` 消息（带 `tool_call_id`）塞回
messages，再问模型。循环往复。

**A3.** 是一段 **JSON 字符串**（不是 dict）。真正调用函数前必须先用 `json.loads()` 把它
解析成 dict，才能 `**args` 展开成关键字参数。

**A4.** **错。** 还必须带上 `tool_call_id`（等于模型那次 `tool_call.id`），模型/API 靠它
把「这条结果」对应回「刚才哪次调用请求」。少了它会报错或对不上号。此外别忘了：在 append
这些 tool 结果**之前**，要先把模型那条 `msg`（调用请求）本身 append 回 messages。

**A5.** 因为模型可能陷入「反复调工具却始终不给最终答案」的死循环。不加上限，`while True`
会一直转，**狂烧 token / 花钱 / 卡死**。加个计数器，超过 N 轮就强制退出兜底。

**A6.** **bug：循环里少了 `messages.append(msg)`**——在 `for` 遍历工具结果之前，没有先把
模型那条「调用请求」消息（`msg`）追加回 messages。结果就是：messages 里出现了 `role:"tool"`
的消息，却没有它对应的 assistant 工具调用消息，API 会报错（tool 消息必须紧跟在包含该
`tool_call_id` 的 assistant 消息之后）。修法：`if msg.tool_calls:` 之后、`for` 之前，加一行
`messages.append(msg)`。
