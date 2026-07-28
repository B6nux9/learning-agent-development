"""
阶段二 Capstone · 核心循环 + 编排 (agent.py)

今天纵切「查订单」最小链路：main 问一句 → run() 起 loop → 模型决定调
query_order → dispatch 执行(注入 user_id) → 模型给最终答复。

分工：
  - client 加载 / SYSTEM_PROMPT / TOOLS(工具 schema) / run() 循环骨架
    —— 我给你(都是你 L8 写过的形状，不重造轮子)。
  - dispatch()  —— **block 2，你来写**。本项目纪律的落地点。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from tools import process_refund, query_order


# --------------------------------------------------------------------------
# client 加载（生产小习惯：env 优先，回落到本地 key 文件；不硬编码 key）
# --------------------------------------------------------------------------
def get_client() -> OpenAI:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        # 仓库根的 deepseek_api.txt（已 gitignore）
        key = (Path(__file__).resolve().parents[2] / "deepseek_api.txt").read_text().strip()
    return OpenAI(api_key=key, base_url="https://api.deepseek.com")


SYSTEM_PROMPT = (
    "你是电商售后客服助手。需要订单信息或办理退款时必须调用工具，"
    "绝不编造，绝不自行判断能否退款——一切以工具返回为准。\n"
    "按工具返回的 reason 措辞回复用户：\n"
    "- order_not_found / forbidden：统一回复「没查到这笔订单哦～」，不解释原因。\n"
    "- refunded：告知已退款成功及金额。\n"
    "- needs_human：致歉并说明这笔需人工审核、已为其转接人工，不要承诺退款结果。\n"
    "- already_refunded：告知该订单已退过款，无需重复申请。"
)


# --------------------------------------------------------------------------
# 工具 schema —— 给模型看的「说明书」
# ⚠️ 注意：这里**故意没有 user_id 这个参数**。模型只能给 order_id。
#    为什么？—— 这是 block 2 的面试追问，写完 dispatch 回答我。
# --------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "查询一笔订单的状态、发货时间、金额。用户问订单/物流时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号，如 A123"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_refund",
            # ⚠️ 同样只暴露 order_id：不给 amount。能不能退、退多少由代码定，不信模型报数。
            "description": "为一笔订单发起退款。用户明确要求退款时调用。是否放行由系统按金额阈值决定。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "要退款的订单号，如 A123"},
                },
                "required": ["order_id"],
            },
        },
    },
]


# --------------------------------------------------------------------------
# block 2 —— 你来写：dispatch（把模型的一次工具调用落地执行）
# --------------------------------------------------------------------------
def dispatch(tool_name: str, args: dict, session_user_id: str) -> dict:
    """执行模型请求的一次工具调用。

    接口契约：
      输入
        tool_name        : str  —— 模型要调的工具名（目前只有 "query_order"）
        args             : dict  —— 模型给的参数，如 {"order_id": "A123"}
                                     ⚠️ 注意 args 里**没有也不该有** user_id
        session_user_id  : str  —— **代码从已登录会话注入**的当前用户 id
      输出：直接返回被调工具的 dict（query_order 已经是 {"ok":...} 形状）
      约束（block 2 考点）
        1. 只认识 "query_order"；其他工具名返回 {"ok": False, "reason": "unknown_tool"}。
        2. 调 query_order 时：user_id 用 session_user_id（代码给的），
           order_id 用 args["order_id"]（模型给的）。**绝不从 args 里取 user_id。**
    """
    if tool_name == "query_order":
        return query_order(session_user_id, args["order_id"])
    # TODO(block 4 你来加): 加一条 "process_refund" 的路由。
    #   —— 跟上面一个模式：user_id 用 session_user_id（注入），order_id 取 args。
    if tool_name == "process_refund":
        return process_refund(session_user_id, args["order_id"])
    return {"ok": False, "reason": "unknown_tool"}


# --------------------------------------------------------------------------
# 闸门（我给你）—— 循环的安全带：轮数上限 + token 预算
# max_steps 对应 DESIGN ④「8 轮未解决 → 转人工」
# max_prompt_tokens 用**真实 token 数**(resp.usage.prompt_tokens)，不是 len//2 (L6 教训)
# --------------------------------------------------------------------------
@dataclass
class LoopGuard:
    max_steps: int = 8
    max_prompt_tokens: int = 60_000

    def tripped(self, step: int, prompt_tokens: int) -> str | None:
        """闸门有没有被触发。没触发返回 None，触发返回原因字符串。"""
        if step >= self.max_steps:
            return "step_limit"
        if prompt_tokens > self.max_prompt_tokens:
            return "token_limit"
        return None


ESCALATION_REPLY = "这个问题我先帮你转接人工客服，请稍等哦～"  # 闸门触发时的兜底话术


# --------------------------------------------------------------------------
# block 3 —— 你来写：run()，把「两段式」升级成真 while-loop
# --------------------------------------------------------------------------
def run(user_message: str, session_user_id: str, guard: LoopGuard | None = None) -> str:
    """跑一轮客服对话，返回给用户的最终答复。

    接口契约：
      输入
        user_message     : str        —— 用户这句话
        session_user_id  : str        —— 代码注入的已登录用户 id（继续往 dispatch 传）
        guard            : LoopGuard  —— 闸门；None 时用默认 LoopGuard()
      输出：str，最终要对用户说的话

    你要写的 while 循环（对照 L8 run_react 的形状，自己盖）：
      1. messages 起手 = [system, user]；step 计数从 0 开始。
      2. 进 while：step += 1。
         **每一轮都要 create(messages, tools=TOOLS, temperature=0)**
         —— 这正是两段式的 bug：它第二次没带 tools，所以只能调一轮。
      3. 唯一的正常出口：模型这次**没有 tool_calls** → return msg.content。
      4. 有 tool_calls → 把 msg append 进 messages，逐个 dispatch(注入 session_user_id)，
         每个结果按 {"role":"tool","tool_call_id":..,"content":json} append，然后**回到 while 顶再问一次**。
      5. 闸门：每轮拿 resp.usage.prompt_tokens 喂给 guard.tripped(step, prompt_tokens)；
         一旦返回非 None → return ESCALATION_REPLY（别 raise，生产要优雅降级/转人工）。
    """
    client = get_client()
    guard = guard or LoopGuard()
    # TODO(你来写): 按契约写 while 循环
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},    
    ]
    step = 0
    prompt_tokens = 0
    while True: 
        tripped_reason = guard.tripped(step, prompt_tokens) 
        if tripped_reason is not None:
            return ESCALATION_REPLY

        step += 1

        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            tools=TOOLS,
            temperature=0,
        )
        prompt_tokens = resp.usage.prompt_tokens

        msg = resp.choices[0].message

        if not msg.tool_calls:
            return msg.content

        messages.append(msg)
        for call in msg.tool_calls:
            result = dispatch(call.function.name, json.loads(call.function.arguments), session_user_id)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

        
