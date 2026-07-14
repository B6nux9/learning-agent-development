"""
阶段一 Capstone:命令行多工具客服 agent

把三节课的肌肉综合成一个能在终端【多轮对话】的客服 agent:
  L2  agent loop(已有)
  L3  多工具 / 错误自愈 / 循环上限(已有)
  L4  分组路由:不要把所有工具一股脑全给模型,按用户意图只暴露相关的一组(本课新肌肉)

已经给你的(你已有的肌肉,别重写):
  - 5 个工具的实现 + 各自 schema
  - 工具按场景分好的三组 TOOL_GROUPS
  - 内层 agent loop:调用模型、执行工具、错误 JSON 回传、MAX_TURNS 兜底

要你补的三个 TODO(L4 新肌肉 + capstone 整合):
  TODO 1  route():输入用户这句话,判断它属于哪个场景,返回该暴露的工具组名
  TODO 2  在内层 loop 里,用 route() 的结果决定这一轮把【哪些工具】传给模型
  TODO 3  外层 REPL:多轮对话——维护一份贯穿整个会话的 messages,循环读用户输入、
          调 agent、打印回复,直到用户输入 quit/exit/退出

跑通标准(在一个终端会话里连续输入,验证它记得上下文 + 路由正确):
  你> 查一下订单 B456
  你> 那帮我把它退了,商品破损        <- 要记得"它"=B456(多轮记忆)
  你> 我有多少积分?                  <- 路由切到账户组
  你> 退出
"""

import os
import json
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
)

MODEL = "deepseek-v4-flash"
MAX_TURNS = 8

# ============================================================
#  假数据
# ============================================================
FAKE_ORDERS = {
    "A123": {"status": "运输中", "eta": "明天 18:00 前送达", "carrier": "顺丰", "address": "北京市海淀区中关村大街 1 号"},
    "B456": {"status": "已签收", "eta": "已于昨天送达", "carrier": "京东", "address": "上海市浦东新区世纪大道 100 号"},
}
REFUNDED = {}          # order_id -> reason
POINTS = {"default_user": 3200}

# ============================================================
#  工具实现(5 个,均返回 JSON 字符串;错误也走 JSON,不抛异常给用户)
# ============================================================
def query_order(order_id: str) -> str:
    """查订单:物流状态、预计送达、承运商、收货地址。"""
    order = FAKE_ORDERS.get(order_id)
    if order is None:
        return json.dumps({"error": f"查无此订单:{order_id}"}, ensure_ascii=False)
    return json.dumps(order, ensure_ascii=False)


def apply_refund(order_id: str, reason: str) -> str:
    """发起退款:仅已签收可退,重复退/查无此单会抛异常(模拟真实下游)。"""
    order = FAKE_ORDERS.get(order_id)
    if order is None:
        raise ValueError(f"退款失败:订单 {order_id} 不存在")
    if order["status"] != "已签收":
        raise ValueError(f"退款失败:订单 {order_id} 当前「{order['status']}」,仅已签收可退")
    if order_id in REFUNDED:
        raise ValueError(f"退款失败:订单 {order_id} 已申请过退款,请勿重复")
    REFUNDED[order_id] = reason
    return json.dumps({"ok": True, "message": f"订单 {order_id} 退款已受理,预计 3 个工作日到账"}, ensure_ascii=False)


def query_refund_status(order_id: str) -> str:
    """查退款进度。"""
    if order_id not in REFUNDED:
        return json.dumps({"error": f"订单 {order_id} 没有退款记录"}, ensure_ascii=False)
    return json.dumps({"order_id": order_id, "state": "退款处理中", "reason": REFUNDED[order_id]}, ensure_ascii=False)


def change_address(order_id: str, new_address: str) -> str:
    """改收货地址:已签收的不能改。"""
    order = FAKE_ORDERS.get(order_id)
    if order is None:
        raise ValueError(f"改地址失败:订单 {order_id} 不存在")
    if order["status"] == "已签收":
        raise ValueError(f"改地址失败:订单 {order_id} 已签收,无法修改")
    order["address"] = new_address
    return json.dumps({"ok": True, "message": f"订单 {order_id} 收货地址已改为:{new_address}"}, ensure_ascii=False)


def query_points(user_id: str = "default_user") -> str:
    """查会员积分。"""
    return json.dumps({"user_id": user_id, "points": POINTS.get(user_id, 0)}, ensure_ascii=False)


# ---- 每个工具的 schema ----
S_QUERY_ORDER = {"type": "function", "function": {
    "name": "query_order", "description": "根据订单号查询物流状态、预计送达、承运商、收货地址",
    "parameters": {"type": "object", "properties": {"order_id": {"type": "string", "description": "订单号,如 A123"}}, "required": ["order_id"]}}}

S_APPLY_REFUND = {"type": "function", "function": {
    "name": "apply_refund", "description": "发起订单退款。仅已签收可退,不确定状态先用 query_order 查",
    "parameters": {"type": "object", "properties": {
        "order_id": {"type": "string", "description": "订单号"}, "reason": {"type": "string", "description": "退款理由"}}, "required": ["order_id", "reason"]}}}

S_REFUND_STATUS = {"type": "function", "function": {
    "name": "query_refund_status", "description": "查询某订单的退款处理进度",
    "parameters": {"type": "object", "properties": {"order_id": {"type": "string", "description": "订单号"}}, "required": ["order_id"]}}}

S_CHANGE_ADDR = {"type": "function", "function": {
    "name": "change_address", "description": "修改订单收货地址。已签收订单不可改",
    "parameters": {"type": "object", "properties": {
        "order_id": {"type": "string", "description": "订单号"}, "new_address": {"type": "string", "description": "新收货地址"}}, "required": ["order_id", "new_address"]}}}

S_QUERY_POINTS = {"type": "function", "function": {
    "name": "query_points", "description": "查询当前会员的积分余额",
    "parameters": {"type": "object", "properties": {}, "required": []}}}

# ============================================================
#  L4 核心:工具分组
#  已按场景分好三组。注意 query_order 作为"通用查询"底座,出现在多个组里
#  (呼应 quiz Q5:共享工具可跨组——这就是"共享底座 + 场景增量")。
# ============================================================
TOOL_GROUPS = {
    "order":   [S_QUERY_ORDER],                                  # 查询类
    "refund":  [S_QUERY_ORDER, S_APPLY_REFUND, S_REFUND_STATUS], # 售后类(带上查询底座)
    "account": [S_QUERY_ORDER, S_CHANGE_ADDR, S_QUERY_POINTS],   # 账户类(带上查询底座)
}

AVAILABLE_TOOLS = {
    "query_order": query_order,
    "apply_refund": apply_refund,
    "query_refund_status": query_refund_status,
    "change_address": change_address,
    "query_points": query_points,
}

VALID_GROUPS = set(TOOL_GROUPS.keys())

# ============================================================
#  TODO 1:路由 —— 判断用户这句话属于哪个场景,返回组名
# ============================================================
def route_keyword(user_text: str) -> str:
    """输入用户最新一句话,返回 'order' / 'refund' / 'account' 之一。

    两种实现思路,任选(先跑通再优化):
      (A) 关键词匹配:'退款/退货/退' -> refund;'积分/地址/改' -> account;其余 -> order。
          简单、零成本、可控,但硬编码、覆盖不全。
      (B) LLM 分类:再开一次便宜的 model 调用,让它把 user_text 归到三类之一,只返回组名。
          灵活、能懂同义/口语,但多一次调用、要防它返回组名以外的字。

    先用 (A) 跑通,行有余力再换 (B) 体会两种路由的权衡。
    返回值必须是 TOOL_GROUPS 里存在的键。
    """
    # 你的代码:
    if any(keyword in user_text for keyword in ["退款", "退货", "退"]):
        return "refund"
    elif any(keyword in user_text for keyword in ["积分", "地址", "改"]):
        return "account"
    else:
        return "order"

def route_llm(user_text: str) -> str:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": (
                "你是一个意图分类器。把用户这句话归到且仅归到下面三类之一,"
                "只输出类别名本身,不要任何解释、标点、引号或多余的字:\n"
                "order   = 查订单 / 查物流\n"
                "refund  = 退款 / 退货 / 查退款进度\n"
                "account = 改地址 / 查积分 / 账户相关"
            )},
            {"role": "user", "content": user_text},
        ],
        temperature=0,
        max_tokens=5,
    )
    raw = response.choices[0].message.content
    label = (raw or "").strip().lower()
    return label if label in VALID_GROUPS else "order"

USE_LLM_ROUTER = True  # True 切换到 LLM 路由,False 用关键词路由
def route(user_text: str) -> str:
    return route_llm(user_text) if USE_LLM_ROUTER else route_keyword(user_text)

def run_agent(messages: list, user_text: str) -> str:
    """内层 agent loop(L2/L3 已有肌肉,基本给全)。
    注意:messages 是【外部传进来的、贯穿整个会话的历史】,不是每次新建——这是多轮记忆的关键。
    """
    # ---- TODO 2:决定这一轮暴露哪些工具 ----
    # 提示:拿【本轮用户最新一句话】(messages 里最后一条 role == 'user' 的 content)喂给 route(),
    #       得到组名,再从 TOOL_GROUPS 取出对应的工具列表,传给下面的 tools=...。
    #       想清楚:为什么按"最新一句用户话"路由,而不是按整段历史?
    tools_this_turn = TOOL_GROUPS[route(user_text)]

    turn = 0
    while turn < MAX_TURNS:
        turn += 1
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools_this_turn,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            messages.append(msg)         # 把最终回复也存进历史(多轮记忆)
            return msg.content

        messages.append(msg)
        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            try:
                result = AVAILABLE_TOOLS[name](**args)      # 错误也是信息:异常 -> 错误 JSON 回传
            except Exception as e:
                result = json.dumps({"error": str(e)}, ensure_ascii=False)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})

    return "抱歉,这个问题我暂时处理不了,已为您转接人工客服"


# ============================================================
#  TODO 3:外层 REPL —— 多轮对话
# ============================================================
def main():
    """终端多轮客服。要求:
      - 维护一份【贯穿整个会话】的 messages,开头放一条 system 提示。
      - 循环:读用户输入 -> 把它以 {'role':'user',...} 追加进 messages -> 调 run_agent(messages)
              -> 打印客服回复。因为 messages 一直累积,agent 天然记得上文("它"指哪个订单)。
      - 用户输入 quit / exit / 退出 时结束循环。
    """
    # 你的代码:
    messages = [
        {"role": "system", "content": "你是一个电商客服助手。用工具查询和操作订单,不要编造信息。"}
    ]

    while True:
        user_input = input("你> ")
        if user_input.lower() in ["quit", "exit", "退出"]:
            print("客服助手: 感谢使用，再见！")
            break

        messages.append({"role": "user", "content": user_input})
        response = run_agent(messages, user_input)
        print(f"客服助手: {response}")


if __name__ == "__main__":
    main()


# 你> 查一下订单 B456
# 你> 那帮我把它退了,商品破损        <- 要记得"它"=B456(多轮记忆)
# 你> 我有多少积分?                  <- 路由切到账户组
# 你> 退出