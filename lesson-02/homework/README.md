# L2 作业 —「亲手写出第一个 agent loop」

把 L1 task-A 里那个客服 loop 变成**真能跑的代码**：一个能查订单的迷你客服 agent。
不看完整答案，用下面的骨架自己填。卡住就把代码 + 报错发给教练。

## 目标

运行 `order_agent.py`，你在命令行问一句「A123 什么时候到？」，agent 能：
1. 自己判断要调用 `query_order` 工具；
2. 你的代码执行、返回订单状态；
3. agent 拿到结果，用自然语言回答你「您的订单已发货，预计明天下午送达」。

## 填空骨架（把 `TODO` 补上）

```python
import os, json
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

# 1) 工具的真实实现（先用假数据）
def query_order(order_id: str) -> str:
    fake = {"A123": "已发货，预计明天下午送达", "A999": "仍在打包中"}
    return fake.get(order_id, "查无此订单")

available_tools = {"query_order": query_order}

# 2) 声明工具的 schema —— 参考 notes.md 第 3 节 ①，把它补完整
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "TODO: 写清这个工具是干嘛的，模型靠它判断何时调用",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "TODO"},
                },
                "required": ["order_id"],
            },
        },
    }
]

# 3) 初始 messages
messages = [
    {"role": "system", "content": "你是一个电商客服助手，帮用户查询订单。"},
    {"role": "user", "content": "A123 什么时候到？"},
]

# 4) agent loop —— 核心，参考 notes.md 第 4 节
MAX_TURNS = 10
for turn in range(MAX_TURNS):          # 用 for + 上限，天然防死循环
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
    )
    msg = response.choices[0].message

    if msg.tool_calls:
        messages.append(msg)                       # TODO 想清楚为什么这行不能少
        for tc in msg.tool_calls:
            name = tc.function.name
            args = json.loads(tc.function.arguments)   # TODO 为什么要 json.loads
            result = available_tools[name](**args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,             # TODO 为什么必须带这个
                "content": str(result),
            })
        # TODO: 这里该做什么才能带着工具结果再问一次模型？
    else:
        print("Agent:", msg.content)
        break
```

## 进阶要求（做完基础版再挑战，可选）

1. **加打印**：每轮循环打印「模型这轮是在调工具还是给答案」，让你**看见** loop 在转。
   （提示：`if msg.tool_calls: print(f"[第{turn}轮] 调用工具:", ...)`）
2. **改成多轮对话**：把写死的 user 消息换成 `input()`，让你能连续问，agent 记得上下文。
3. **加第二个工具**：比如 `query_customer(customer_id)` 返回客户信息，看模型会不会在
   合适时机选对工具（这是 L4 多工具的预热）。

## 提交

把 `order_agent.py` 放进本文件夹，跑通后把**终端输出**贴给教练。看到 agent 真的
「先调工具、再用结果回答」，L2 就通关，你就正式会写 agent 了。
