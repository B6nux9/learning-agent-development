"""
L2 作业:查订单迷你客服 agent —— 手写 agent loop

目标:把下面标了 TODO 的 agent loop 补完整,让它能自动完成"四步握手":
  用户提问 → 模型点单(tool_calls) → 你的代码执行工具 → 结果塞回 → 模型给最终答复。

周边零件(客户端、工具 schema、假订单库、执行函数)已经给你搭好,
你只需要写中间那段循环逻辑。跑起来后试试这几句提问:
  - "我的订单 A123 到哪了?"        (要调一次工具)
  - "帮我看看 A123 和 B456 的状态"   (可能要调两次工具)
  - "你们几点下班?"                 (不需要工具,模型应直接回答)
"""

import os
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

# ---- 假的订单数据库(真实项目里这是一次数据库/API 查询)----
FAKE_ORDERS = {
    "A123": {"status": "运输中", "eta": "明天 18:00 前送达", "carrier": "顺丰"},
    "B456": {"status": "已签收", "eta": "已于昨天送达", "carrier": "京东"},
}


def query_order(order_id: str) -> str:
    """真正被执行的工具函数。返回一段 JSON 字符串给模型看。"""
    order = FAKE_ORDERS.get(order_id)
    if order is None:
        return json.dumps({"error": f"查无此订单:{order_id}"}, ensure_ascii=False)
    return json.dumps(order, ensure_ascii=False)


# ---- 工具 schema:这是"告诉模型有哪些工具可用"的说明书 ----
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "根据订单号查询订单的物流状态、预计送达时间和承运商",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "订单号,例如 A123",
                    }
                },
                "required": ["order_id"],
            },
        },
    }
]

# 把工具名映射到真正的 Python 函数,执行时用得上
AVAILABLE_TOOLS = {"query_order": query_order}


def run_agent(user_question: str) -> str:
    messages = [
        {"role": "system", "content": "你是一个电商客服助手。需要订单信息时,调用 query_order 工具查询,不要编造。"},
        {"role": "user", "content": user_question},
    ]

    # ========================= 你的 agent loop 从这里开始 =========================
    while True:
        # 1) 把当前 messages + 工具说明书发给模型
        #    提示:client.chat.completions.create(..., tools=TOOLS)
        response = client.chat.completions.create(  # TODO
            model="deepseek-v4-flash",
            messages=messages,
            tools=TOOLS,
            stream=False,
            reasoning_effort="medium",
            extra_body={"thinking": {"type": "enabled"}}
        )
        msg = response.choices[0].message

        # 2) 判断:模型这轮到底是"点单"还是"给最终答案"?
        #    提示:看 msg.tool_calls 是不是空的
        if not msg.tool_calls:  # TODO: 没有 tool_calls → 拿到最终答案了
            return msg.content  # 跳出循环,把答案返回

        # 3) 模型点单了。先把模型这条"点单"消息 append 回 messages
        #    (少了这一步,后面的 tool 结果会对不上号,API 会报错)
        messages.append(msg)  # 这一步已给你

        # 4) 逐个执行模型点的工具,把每个结果作为 role="tool" 的消息塞回去
        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)  # 模型传的参数是 JSON 字符串

            # TODO 4a: 用 AVAILABLE_TOOLS 找到真正的函数并执行,拿到 result 字符串
            result = AVAILABLE_TOOLS[name](**args)  # 执行工具,拿到结果字符串

            # TODO 4b: 把结果 append 成一条 tool 消息。三个字段缺一不可:
            tool_message = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result
            }
            #          role="tool"、tool_call_id=tool_call.id、content=result
            messages.append(tool_message)

        # 5) 循环回到第 1 步,带着工具结果再问模型一次
    # ========================= agent loop 到此结束 =========================


if __name__ == "__main__":
    print(run_agent("我的订单 A123 和 B456 到哪了？"))
