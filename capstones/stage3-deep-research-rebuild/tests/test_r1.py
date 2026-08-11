"""R1 测试:fake ChatModel + fake_search,拔网线跑绿。

跑法(在 stage3-deep-research-rebuild/ 目录下):
    uv run pytest tests/test_r1.py -v

建议 TDD:先跑一次看全红,每填一个 TODO 重跑,看红变绿的顺序。
"""

import asyncio

from langchain_core.messages import AIMessage

from deep_research import deep_researcher as dr


class FakeChatModel:
    """鸭子类型假模型:按脚本吐消息;bind_tools/with_retry/with_config 全返回自己。

    只要 deep_researcher 对模型的用法不超出这四个方法,测试就无需任何网络。
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
        return next(self._script)


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
    """happy path:第 1 轮调 fake_search → 第 2 轮不调工具(早退)→ 必经 compress → END。"""
    result = run_subgraph(monkeypatch, [
        ai_with_tool_call("fake_search", {"queries": ["langgraph subgraph"]}, "call_1"),
        AIMessage(content="研究完成,以下是我的总结……"),
    ])

    # 走到过 compress(R1 占位实现)
    assert "compressed_research" in result

    # reducer 追加合并:AI(带调用) + Tool(搜索结果) + AI(总结) = 3 条
    msgs = result["researcher_messages"]
    assert len(msgs) == 3
    assert msgs[1].type == "tool"
    assert msgs[1].tool_call_id == "call_1"
    assert "Results for: langgraph subgraph" in str(msgs[1].content)


def test_research_complete_signal_exits(monkeypatch):
    """happy path②:模型调用 ResearchComplete(纯协议,无执行体)→ 路由去压缩。"""
    result = run_subgraph(monkeypatch, [
        ai_with_tool_call("ResearchComplete", {}, "call_done"),
    ])
    assert "compressed_research" in result
    # ResearchComplete 也要有 ToolMessage 回执(否则消息历史里的 tool_call 悬空)
    msgs = result["researcher_messages"]
    assert msgs[-1].type == "tool"
    assert msgs[-1].tool_call_id == "call_done"


def test_budget_forces_exit(monkeypatch):
    """failure path①:模型永远想继续搜,预算 max_react_tool_calls=1 强制止损。

    脚本给了两轮工具调用,但预算只允许一轮 —— 第二条脚本消息不应被消费。
    """
    result = run_subgraph(
        monkeypatch,
        [
            ai_with_tool_call("fake_search", {"queries": ["q1"]}, "c1"),
            ai_with_tool_call("fake_search", {"queries": ["q2"]}, "c2"),
        ],
        configurable={"max_react_tool_calls": 1},
    )
    assert "compressed_research" in result
    # 只跑了一轮:AI + Tool = 2 条(第二条 AI 脚本没被消费)
    assert len(result["researcher_messages"]) == 2


def test_tool_error_becomes_observation(monkeypatch):
    """failure path②:工具执行炸了不许炸图 —— 错误变成 ToolMessage 喂回模型。"""
    result = run_subgraph(monkeypatch, [
        # queries 传了错误类型 → fake_search 参数校验抛异常 → execute_tool_safely 兜住
        ai_with_tool_call("fake_search", {"bad_arg": 123}, "c_err"),
        AIMessage(content="工具坏了,我直接总结。"),
    ])
    tool_msgs = [m for m in result["researcher_messages"] if m.type == "tool"]
    assert any("Error executing tool" in str(m.content) for m in tool_msgs)
