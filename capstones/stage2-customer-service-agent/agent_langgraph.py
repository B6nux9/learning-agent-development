"""
L9 · LangGraph 版客服 agent (agent_langgraph.py)

把封版的裸 SDK `run()` 循环用 LangGraph 重写。**工具层 tools.py 原样复用**——换的只是"怎么编排"。
核心对照（裸 SDK → LangGraph）：
  run() 里的 while 循环         → 一张图 StateGraph（节点 + 边）
  messages（循环里累积的状态）  → State（图在节点间传，add_messages 帮你累积）
  "调 LLM 拿 tool_calls"        → agent 节点
  "逐个 dispatch 工具"          → tools 节点
  if not tool_calls: return     → agent 后的条件边（route_after_agent）
  tools 执行完回到 while 顶      → tools → agent 的回边
  if result.get("terminal")     → tools 后的条件边（route_after_tools → END）
  LoopGuard.max_steps           → recursion_limit（注意：超限是 raise，需 try/except 兜底）

选型结论见同目录 ADR-001-langgraph-vs-bare-sdk.md（本项目编排层采用裸 SDK，agent.py）。

跑法：uv run python capstones/stage2-customer-service-agent/agent_langgraph.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agent import SYSTEM_PROMPT, TOOLS, dispatch  # 复用裸 SDK 版的 schema/prompt/dispatch


# ── LLM（DeepSeek，LangChain 封装版 ChatOpenAI）──
def _key() -> str:
    return os.environ.get("DEEPSEEK_API_KEY") or (
        Path(__file__).resolve().parents[2] / "deepseek_api.txt"
    ).read_text().strip()


llm = ChatOpenAI(
    model="deepseek-v4-flash",
    api_key=_key(),
    base_url="https://api.deepseek.com",
    temperature=0,
).bind_tools(TOOLS)  # 把工具 schema 绑上去，模型才知道有哪些工具


# ── State：图在节点间传递的东西。就是你 run() 里的 messages ──
# Annotated[list, add_messages]：告诉 LangGraph 这个字段用「append 累积」而不是「覆盖」。
class State(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: str  # 会话注入的已登录用户（对应裸 SDK 版 run() 的 session_user_id 参数）
    escalated: bool  # 工具是否报了 terminal 停机信号（对应裸 SDK run() 的 result.get("terminal")）


# ══════════════════════════════════════════════════════════════════════
# agent 节点 —— 就是裸 SDK 版 run() 里 create(...) 那一步
# ══════════════════════════════════════════════════════════════════════
def agent_node(state: State) -> dict:
    """调一次 LLM。

    契约（对照你 run() 里 `resp = client.chat.completions.create(...)`）：
      1. 取 state["messages"]（LangGraph 已把 system + 历史 + 工具结果累积好了）。
      2. 调 llm：`resp = llm.invoke(state["messages"])`（llm 已 bind_tools，无需再传 tools）。
      3. 返回**增量** `{"messages": [resp]}`——add_messages 会把 resp append 进 state，
         **不要**返回整个列表（那是覆盖）。
    """
    resp = llm.invoke(state["messages"])
    return {"messages": [resp]}


# ══════════════════════════════════════════════════════════════════════
# tools 节点 —— 就是裸 SDK 版 run() 里 dispatch 那段 for 循环
# ══════════════════════════════════════════════════════════════════════
def tools_node(state: State) -> dict:
    """执行上一条 AI 消息里的所有 tool_calls。

    契约：
      1. last = state["messages"][-1]；它的 `.tool_calls` 是一个 list，每项是 dict，含
         "name" / "args" / "id"。**注意：LangChain 已把 args 解析成 dict 了，不用再 json.loads**
         （比裸 SDK 省一步——裸 SDK 里 args 是 JSON 字符串）。
      2. 对每个 call：`result = dispatch(call["name"], call["args"], state["user_id"])`
         ——**复用裸 SDK 的 dispatch**！user_id 从 State 注入（对应你 run() 的 session_user_id）。
      3. 每个结果包成 `ToolMessage(content=json.dumps(result, ensure_ascii=False), tool_call_id=call["id"])`。
      4. 返回 {"messages": [...收集的所有 ToolMessage...]}。
    """
    last = state["messages"][-1]
    total = []
    escalated = False  # 本轮有没有工具报 terminal 停机
    for call in last.tool_calls:
        result = dispatch(call["name"], call["args"], state["user_id"])
        if result.get("terminal"):
            escalated = True
        total.append(ToolMessage(
            content=json.dumps(result, ensure_ascii=False),
            tool_call_id=call["id"],
        ))
    return {"messages": total, "escalated": escalated}

# ══════════════════════════════════════════════════════════════════════
# 条件路由 —— 就是裸 SDK 版 `if not msg.tool_calls: return` 那个判断
# ══════════════════════════════════════════════════════════════════════
def route_after_agent(state: State) -> str:
    """agent 之后往哪走。

    契约：
      - last = state["messages"][-1]
      - last 有 tool_calls → 返回字符串 "tools"（去执行工具）
      - 没有 → 返回 END（结束，模型已给最终答复）
    """
    last = state["messages"][-1]
    if last.tool_calls:
        return "tools"
    return END


# ══════════════════════════════════════════════════════════════════════
# tools 之后的路由 —— 就是裸 SDK 版终止 loop 的判断
# ══════════════════════════════════════════════════════════════════════
def route_after_tools(state: State) -> str:
    """tools 执行完往哪走。

    契约（对照裸 SDK run() 里工具跑完后的 `if result.get("terminal"): return`）：
      - state 的 escalated 为真（转人工停机）→ 返回 END（终态，不再回 agent，不给模型改口机会）
      - 否则 → 返回 "agent"（回边，继续循环）
    """
    if state.get("escalated"):
        return END
    return "agent"


# ── 建图（第三刀：加 terminal 终止 = tools 后的第二个条件边）──
def build_graph():
    g = StateGraph(State)
    g.add_node("agent", agent_node)
    g.add_node("tools", tools_node)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", route_after_agent, ["tools", END])  # agent →（tools 或 END）
    g.add_conditional_edges("tools", route_after_tools, ["agent", END])  # tools →（回 agent 或 END 终止）
    return g.compile()


if __name__ == "__main__":
    import json as _json

    from langgraph.errors import GraphRecursionError

    app = build_graph()

    def run(user_message: str, user_id: str = "u_zhang") -> str:
        try:
            state = app.invoke(
                {
                    "user_id": user_id,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                },
                {"recursion_limit": 8},  # = 裸 SDK 的 LoopGuard.max_steps；超了会 raise（下面 catch）
            )
        except GraphRecursionError:
            # ⚠️ ADR 点：LangGraph 到上限是 RAISE，不像你 LoopGuard 优雅返回 → 要自己 catch 兜底
            return "这个问题我先帮你转接人工客服，请稍等哦～"
        if state.get("escalated"):  # 转人工终态：给带工单号的话术（对应裸 SDK 的 HANDOFF_REPLY）
            ticket = _json.loads(state["messages"][-1].content).get("ticket_id")
            return f"这个问题我已为您转接人工客服，工单号 {ticket}，请稍候人工跟进～"
        return state["messages"][-1].content

    for q in ["我的订单 A123 到哪了？", "那帮我退了 D999 吧"]:  # A123 正常查；D999 超限→转人工终止
        print(f"\n用户: {q}\n客服: {run(q)}")
