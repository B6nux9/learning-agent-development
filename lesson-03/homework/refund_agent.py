"""
L3 作业:退款客服 agent —— tool use 深入

和 L2 相反:agent loop 直接给你(那是你已有的肌肉),这次挖空的是 L3 的新肌肉:
  TODO 1  从零写 apply_refund 的 TOOLS schema(重点:description 怎么写才能让模型"先查再退")
  TODO 2  用 try/except 包住工具执行,把异常变成回传给模型的错误 JSON(agent 自愈)
  TODO 3  实现循环次数上限(你在 L2 quiz 里自己提出的兜底)

跑通标准(三句都试):
  - "帮我退掉订单 B456,商品有破损"   → 链式:先查(已签收)→ 再退 → 成功
  - "帮我退掉订单 A123"              → 查到"运输中" → 不能退,模型解释原因
  - "帮我退掉订单 C999"              → 查无此订单 → 模型体面告知,程序不崩溃
"""

import os
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

# ---- 假订单库(比 L2 多了 refundable 相关信息)----
FAKE_ORDERS = {
    "A123": {"status": "运输中", "eta": "明天 18:00 前送达", "carrier": "顺丰"},
    "B456": {"status": "已签收", "eta": "已于昨天送达", "carrier": "京东"},
}

# 记录已发起的退款,防重复退
REFUNDED = set()


def query_order(order_id: str) -> str:
    """查订单。查不到时返回 error JSON(错误也是信息,不抛异常的写法)。"""
    order = FAKE_ORDERS.get(order_id)
    if order is None:
        return json.dumps({"error": f"查无此订单:{order_id}"}, ensure_ascii=False)
    return json.dumps(order, ensure_ascii=False)


def apply_refund(order_id: str, reason: str) -> str:
    """发起退款。注意:这个函数会【抛异常】——模拟真实系统里"你控制不了的下游服务"。
    业务规则:只有"已签收"的订单可以退;不存在/未签收/已退过 → 抛 ValueError。
    你不要改这个函数;要在 loop 那侧用 try/except 接住它。"""
    order = FAKE_ORDERS.get(order_id)
    if order is None:
        raise ValueError(f"退款失败:订单 {order_id} 不存在")
    if order["status"] != "已签收":
        raise ValueError(f"退款失败:订单 {order_id} 当前状态为「{order['status']}」,仅已签收订单可退款")
    if order_id in REFUNDED:
        raise ValueError(f"退款失败:订单 {order_id} 已提交过退款申请,请勿重复操作")
    REFUNDED.add(order_id)
    return json.dumps({"ok": True, "message": f"订单 {order_id} 退款已受理,理由:{reason},预计 3 个工作日到账"},
                      ensure_ascii=False)


# ---- 工具菜单 ----
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "根据订单号查询订单的物流状态、预计送达时间和承运商",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号,例如 A123"}
                },
                "required": ["order_id"],
            },
        },
    },
    # ============================ TODO 1 ============================
    # 从零写出 apply_refund 的 schema。要求:
    #   - name 和真实函数对上号
    #   - 两个参数:order_id(必填)、reason(必填,退款理由)
    #   - description 里除了"做什么",还要写清业务规则(仅已签收订单可退),
    #     并引导模型"不确定订单状态时先用 query_order 查询"——
    #     措辞好坏直接决定模型会不会乖乖"先查再退",自己试着调几版。
    {
        "type": "function",
        "function": {
            "name": "apply_refund",
            "description": "发起订单退款申请。仅已签收的订单可退，请先用 query_order 查询订单状态,再决定是否发起退款。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号,例如 A123"},
                    "reason": {"type": "string", "description": "退款理由,例如 商品破损"},
                },
                "required": ["order_id", "reason"],
            },
        },
    },
    # ================================================================
]

AVAILABLE_TOOLS = {"query_order": query_order, "apply_refund": apply_refund}

MAX_TURNS = 8  # TODO 3 会用到


def run_agent(user_question: str) -> str:
    messages = [
        {"role": "system", "content": "你是一个电商客服助手。用工具查询和操作订单,不要编造信息。"},
        {"role": "user", "content": user_question},
    ]

    # ==================== TODO 3:把这个 while True 改成有次数上限的循环 ====================
    # 要求:最多跑 MAX_TURNS 轮;超限时不要崩溃,返回一句给用户的兜底话术
    # (比如"抱歉,这个问题我暂时处理不了,已为您转接人工客服")。
    turn = 0
    while turn < MAX_TURNS:
        turn += 1
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            tools=TOOLS,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content

        messages.append(msg)

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            # ==================== TODO 2:错误也是信息 ====================
            # 现在这行裸调用:apply_refund 一抛异常整个程序就崩了。
            # 用 try/except 包住它:
            #   - 成功 → result 就是返回值
            #   - 抛异常 e → result = 一个含错误信息的 JSON 字符串
            #     (提示:json.dumps({"error": str(e)}, ensure_ascii=False))
            # 目标:无论成败,模型都能"看到发生了什么",自己决定下一步。
            try:
                result = AVAILABLE_TOOLS[name](**args)
            except Exception as e:
                result = json.dumps({"error": str(e)}, ensure_ascii=False)
            # ==============================================================

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })
    return "抱歉,这个问题我暂时处理不了,已为您转接人工客服"
    # ======================================================================================


if __name__ == "__main__":
    for q in [
        "帮我退掉订单 B456,商品有破损",
        "帮我退掉订单 A123",
        "帮我退掉订单 C999",
    ]:
        print(f"\n>>> 用户:{q}")
        print(f"客服:{run_agent(q)}")
