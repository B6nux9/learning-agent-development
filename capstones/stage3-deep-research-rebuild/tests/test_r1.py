"""R1 测试:fake ChatModel + fake_search,拔网线跑绿。

跑法(在 stage3-deep-research-rebuild/ 目录下):
    uv run pytest tests/test_r1.py -v

R2 防火墙后,本文件断言全部走公开契约(raw_notes/compressed_research),不再窥探内部 state。
"""

import asyncio

from langchain_core.messages import AIMessage

from deep_research import deep_researcher as dr


class FakeChatModel:
    """鸭子类型假模型:按脚本吐消息;bind_tools/with_retry/with_config 全返回自己。

    只要 deep_researcher 对模型的用法不超出这四个方法,测试就无需任何网络。
    剧本项若是 Exception 实例则抛出(用于测试重试)。
    """

    def __init__(self, scripted: list[AIMessage]):
        self._script = iter(scripted)

    def bind_tools(self, tools, **kwargs):
        return self

    def with_retry(self, **kwargs):
        return self

    def with_config(self, config):
        return self

    async def ainvoke(self, messages):
        item = next(self._script)
        if isinstance(item, Exception):
            raise item
        return item


def ai_with_tool_call(name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def run_subgraph(monkeypatch, scripted, configurable=None):
    monkeypatch.setattr(dr, "configurable_model", FakeChatModel(scripted))
    return asyncio.run(
        dr.researcher_subgraph.ainvoke(
            {"researcher_messages": [], "research_topic": "LangGraph 子图机制"},
            config={"configurable": configurable or {}},
        )
    )


def test_happy_path_search_then_finish(monkeypatch):
    """happy path:第 1 轮调 fake_search → 第 2 轮不调工具(早退)→ 必经 compress → END。

    防火墙后循环行为经 raw_notes 审计通道观察。
    """
    result = run_subgraph(monkeypatch, [
        ai_with_tool_call("fake_search", {"queries": ["langgraph subgraph"]}, "call_1"),
        AIMessage(content="研究完成,以下是我的总结……"),
        AIMessage(content="压缩稿:子图要点。"),
    ])

    assert result["compressed_research"] == "压缩稿:子图要点。"
    assert "Results for: langgraph subgraph" in result["raw_notes"][0]
    assert "研究完成" in result["raw_notes"][0]


def test_research_complete_signal_exits(monkeypatch):
    """happy path②:模型调用 ResearchComplete(纯协议,无执行体)→ 路由去压缩。

    能拿到压缩稿即证明路由到了 compress。
    """
    result = run_subgraph(monkeypatch, [
        ai_with_tool_call("ResearchComplete", {}, "call_done"),
        AIMessage(content="压缩稿:信号退出。"),
    ])
    assert result["compressed_research"] == "压缩稿:信号退出。"


def test_budget_forces_exit(monkeypatch):
    """failure path①:模型永远想继续搜,预算 max_react_tool_calls=1 强制止损。

    脚本给了两轮工具调用,但预算只允许一轮 —— q2 的搜索从未发生。
    注意:预算=1 时 compress 消费的其实是脚本第二条(q2 那条 AIMessage),
    所以这里不断言 compressed_research 的值。
    """
    result = run_subgraph(
        monkeypatch,
        [
            ai_with_tool_call("fake_search", {"queries": ["q1"]}, "c1"),
            ai_with_tool_call("fake_search", {"queries": ["q2"]}, "c2"),
            AIMessage(content="压缩稿"),
        ],
        configurable={"max_react_tool_calls": 1},
    )
    assert "Results for: q1" in result["raw_notes"][0]
    assert "Results for: q2" not in result["raw_notes"][0]


def test_tool_error_becomes_observation(monkeypatch):
    """failure path②:工具执行炸了不许炸图 —— 错误变成 ToolMessage 喂回模型。"""
    result = run_subgraph(monkeypatch, [
        # queries 传了错误类型 → fake_search 参数校验抛异常 → execute_tool_safely 兜住
        ai_with_tool_call("fake_search", {"bad_arg": 123}, "c_err"),
        AIMessage(content="工具坏了,我直接总结。"),
        AIMessage(content="压缩稿"),
    ])
    assert "Error executing tool" in result["raw_notes"][0]
