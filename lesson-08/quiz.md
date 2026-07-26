# L8 Quiz：路由 / ReAct / Planning

> 出题原则：**考"能不能推"，不考"背没背下来"**。
> 除 Q4 的代码外，其余都可以只靠 §0 的三个锚点推出来。允许翻讲义，但先自己推一遍再翻。

---

**Q1（锚点①·协议化）**
你 L2 的 `order_agent.py` 是一个 function-calling 版 ReAct。现在要把它迁到一个
**只支持纯文本补全、不支持 function calling** 的开源模型上。
① Action 和 Observation 这两个环节，各要改成什么形式？
② 改完之后最容易出的**新故障**是什么？（提示：想想原版 ReAct 那个年代的日常）

---

**Q2（锚点②·推导）**
**不要翻对比表**，只用"重规划频率"这条轴推：
① 为什么 Plan-and-Execute 的执行阶段**可以并行**，而 ReAct **天然串行**？
② 由此，两者的**延迟特征**分别长什么样？（哪种延迟在前、哪种在累加）

---

**Q3（锚点③·场景判断）**
下面三个任务，各自该落在"确定性 ↔ 自主性"轴的哪个位置？每个给**一句**理由。
- a) 客服：用户说"帮我把上个月所有延迟发货的订单都申请赔付"（涉及 10+ 订单）
- b) 客服：用户说"我的 A123 到哪了"
- c) 数据分析 agent：给它一个 CSV 和一句"找出异常并出报告"

---

**Q4（生产工程·代码题，本 quiz 最硬）**
下面这段 loop 能跑通 demo，但**不能上生产**。指出**至少 4 个**问题，
并对每个说清**它会在什么情况下咬人**。

```python
def run_agent(user_question: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_question},
    ]
    while True:
        response = client.chat.completions.create(
            model="deepseek-v4-flash", messages=messages, tools=TOOLS
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content

        messages.append(msg)
        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            try:
                result = AVAILABLE_TOOLS[name](**args)
            except Exception as e:
                result = json.dumps({"error": str(e)}, ensure_ascii=False)
            print(f"[debug] 调用 {name} -> {result}")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })
```

---

**Q5（区分题·最容易糊的点）**
L3 学过"**错误也是信息**"——工具报错要包成 JSON 回传给模型，让它自愈。
但 L8 说 `TOOL_FATAL` 要**直接终止 loop**。
① 这两条冲突吗？
② 各举一个具体例子（客服场景）。
③ **判断标准是什么**——拿到一个异常，你怎么决定它属于哪一类？
