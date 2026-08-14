"""R2 测试:防火墙 → 压缩 → 韧性,分组递增(与课程分组对应)。

跑法:uv run pytest tests/test_r2.py -v
Group A 只需通过防火墙测试;B/C 的测试随骨架追加。
"""

import asyncio

from langchain_core.messages import AIMessage

from deep_research import deep_researcher as dr
from test_r1 import FakeChatModel, ai_with_tool_call


# ---------- Group A · 防火墙 ----------

def test_output_firewall_filters_state(monkeypatch):
    """子图返回值必须只含 output schema 的两个字段——researcher_messages 等一律留在墙内。

    这是 DESIGN.md 决策 1 的可执行版本:context isolation 是结构保证,不是消费方自觉。
    """
    monkeypatch.setattr(dr, "configurable_model", FakeChatModel([
        ai_with_tool_call("fake_search", {"queries": ["q"]}, "c1"),
        AIMessage(content="总结完毕。"),
        AIMessage(content="压缩稿:LangGraph 子图要点……"),
    ]))
    result = asyncio.run(
        dr.researcher_subgraph.ainvoke(
            {"researcher_messages": [], "research_topic": "t"},
            config={"configurable": {}},
        )
    )
    assert set(result.keys()) == {"compressed_research", "raw_notes"}, (
        f"过墙的字段应该只有两个,实际拿到: {sorted(result.keys())}"
    )


# ---------- Group B · 压缩工人 ----------

def test_compress_produces_summary_and_raw_notes(monkeypatch):
    """压缩节点消费第三条脚本消息作为压缩稿;raw_notes 保全 tool+ai 原始内容。"""
    monkeypatch.setattr(dr, "configurable_model", FakeChatModel([
        ai_with_tool_call("fake_search", {"queries": ["langgraph"]}, "c1"),
        AIMessage(content="初步总结:子图可作为父图节点。"),
        AIMessage(content="压缩稿:要点一二三。"),
    ]))
    result = asyncio.run(
        dr.researcher_subgraph.ainvoke(
            {"researcher_messages": [], "research_topic": "t"},
            config={"configurable": {}},
        )
    )
    assert result["compressed_research"] == "压缩稿:要点一二三。"
    # raw_notes 是单元素列表,内容拼接了 tool 与 ai 消息
    assert len(result["raw_notes"]) == 1
    assert "Results for: langgraph" in result["raw_notes"][0]   # tool 消息内容在
    assert "初步总结" in result["raw_notes"][0]                  # ai 消息内容在


# ---------- Group C · 韧性自救 ----------

class BadRequestError(Exception):
    """模拟 openai.BadRequestError:is_token_limit_exceeded 是模式匹配,
    光有报错文案不够——类名必须是 BadRequestError、模块名得含 'openai'
    (实测:纯 Exception 带任何文案都返回 False)。
    对 "deepseek:deepseek-chat"(provider=None → 全分支嗅探)和 "openai:" 前缀均返回 True。
    """
    __module__ = "openai"


def test_remove_up_to_last_ai_message_unit():
    """单元:截断到最后一条 AI 消息之前;无 AI 时原样返回;不改原列表。"""
    from langchain_core.messages import HumanMessage, ToolMessage
    from deep_research.utils import remove_up_to_last_ai_message
    msgs = [AIMessage(content="r1"), ToolMessage(content="t1", tool_call_id="a"),
            AIMessage(content="r2"), ToolMessage(content="t2", tool_call_id="b"),
            HumanMessage(content="请压缩")]
    out = remove_up_to_last_ai_message(msgs)
    assert [m.content for m in out] == ["r1", "t1"]
    assert len(msgs) == 5  # 纯函数:原列表未被修改
    only_tools = [ToolMessage(content="t", tool_call_id="x")]
    assert remove_up_to_last_ai_message(only_tools) == only_tools

def test_token_limit_retry_then_success(monkeypatch):
    """压缩第一口噎住(token 超限)→ 剪一轮重试 → 成功。"""
    monkeypatch.setattr(dr, "configurable_model", FakeChatModel([
        ai_with_tool_call("fake_search", {"queries": ["q"]}, "c1"),
        AIMessage(content="总结。"),
        BadRequestError("Error code: 400 - This model's maximum context length is 65536 tokens, "
                        "however you requested 70000 tokens. Please reduce the length of the messages."),
        AIMessage(content="压缩稿:重试成功。"),
    ]))
    result = asyncio.run(dr.researcher_subgraph.ainvoke(
        {"researcher_messages": [], "research_topic": "t"}, config={"configurable": {}}))
    assert result["compressed_research"] == "压缩稿:重试成功。"

def test_compress_gives_up_but_raw_notes_survive(monkeypatch):
    """3 次全败 → 兜底错误文案;raw_notes 照样过墙(降级通道)。"""
    monkeypatch.setattr(dr, "configurable_model", FakeChatModel([
        ai_with_tool_call("fake_search", {"queries": ["q"]}, "c1"),
        AIMessage(content="总结。"),
        Exception("boom"), Exception("boom"), Exception("boom"),
    ]))
    result = asyncio.run(dr.researcher_subgraph.ainvoke(
        {"researcher_messages": [], "research_topic": "t"}, config={"configurable": {}}))
    assert "Error synthesizing research report" in result["compressed_research"]
    assert "Results for: q" in result["raw_notes"][0]


# ---------- Group D · 真搜索开关 ----------
# 注:不测 search_api="tavily" 分支——实测 TavilySearch(max_results=3) 在无
# TAVILY_API_KEY 环境下实例化即抛 ValidationError,拔网线(无 key)跑不绿,
# 违反单测离线纪律。tavily 路径由 tests/smoke/smoke_r2.py 联网冒烟验证。

def test_search_api_defaults_to_fake():
    """不配 search_api 时工具箱含 fake_search——离线纪律是默认态。"""
    from deep_research.utils import get_all_tools
    tools = asyncio.run(get_all_tools({"configurable": {}}))
    names = [t.name for t in tools]
    assert "fake_search" in names
    assert len(tools) == 3
