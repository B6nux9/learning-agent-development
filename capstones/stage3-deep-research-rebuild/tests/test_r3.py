"""R3 测试 —— supervisor 子图(状态协议 / supervisor 节点 / 拦截与 fan-out / 预算)。

Group A:状态协议(override_reducer / ConductResearch / SupervisorState)。
Group B:supervisor 节点(直接调函数测,子图 Group C/D 才编译)。
Group C:supervisor_tools 拦截与 fan-out + 子图编译(researcher_subgraph 用假货,
        隔离层级:这里只测 supervisor 层的转手逻辑,researcher 内部 R1/R2 已测过)。
"""

import asyncio
from typing import get_args, get_type_hints

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from pydantic import ValidationError

from deep_research import deep_researcher as dr
from deep_research.state import ConductResearch, SupervisorState, override_reducer


class TestOverrideReducer:
    """双语义 reducer:普通值走追加,{"type": "override"} 信封走整体替换。"""

    def test_add_mode_appends(self):
        # 普通 list 走 operator.add 老路
        assert override_reducer([1, 2], [3]) == [1, 2, 3]

    def test_override_mode_replaces(self):
        # override 信封:旧值整个丢弃
        assert override_reducer([1, 2], {"type": "override", "value": [9]}) == [9]

    def test_override_empty_list_resets(self):
        # R1 quiz 的老问题"add reducer 无法清空字段"——override 信封做到了
        assert override_reducer([1, 2], {"type": "override", "value": []}) == []


class TestConductResearch:
    """派活协议工具:带字段的那种(对比 ResearchComplete 的空壳)。"""

    def test_research_topic_field_exists(self):
        cr = ConductResearch(research_topic="quantum computing impact on cryptography")
        assert cr.research_topic == "quantum computing impact on cryptography"

    def test_research_topic_required(self):
        # 派活单不许空着交
        with pytest.raises(ValidationError):
            ConductResearch()

    def test_field_description_is_model_facing(self):
        # Field(description=...) 会进 bind_tools 生成的 schema——是写给模型的填表说明
        desc = ConductResearch.model_fields["research_topic"].description
        assert desc and "topic" in desc.lower()


class TestSupervisorState:
    """supervisor 子图状态:5 字段,3 个挂 override_reducer。"""

    def test_field_set(self):
        assert set(SupervisorState.__annotations__) == {
            "supervisor_messages",
            "research_brief",
            "notes",
            "research_iterations",
            "raw_notes",
        }

    def test_override_reducer_attached(self):
        hints = get_type_hints(SupervisorState, include_extras=True)
        for field in ("supervisor_messages", "notes", "raw_notes"):
            assert override_reducer in get_args(hints[field]), f"{field} 应挂 override_reducer"


###################
# Group B:supervisor 节点(不经图,直接调函数)
###################

class RecordingFakeModel:
    """test_r1.FakeChatModel 同款鸭子类型,外加记录 bind_tools 收到了什么。"""

    def __init__(self, scripted: list[AIMessage]):
        self._script = iter(scripted)
        self.bound_tools = None

    def bind_tools(self, tools, **kwargs):
        self.bound_tools = tools
        return self

    def with_retry(self, **kwargs):
        return self

    def with_config(self, config):
        return self

    async def ainvoke(self, messages):
        self.last_input = messages
        return next(self._script)


def seeded_state(iterations: int = 0) -> dict:
    """R3 手动 seed:R4 之前没有 write_research_brief,system prompt 由测试代劳。"""
    return {
        "supervisor_messages": [
            SystemMessage(content="You are a research supervisor..."),
            HumanMessage(content="研究 LangGraph 的 reducer 机制"),
        ],
        "research_brief": "研究 LangGraph 的 reducer 机制",
        "research_iterations": iterations,
    }


def run_supervisor(monkeypatch, state):
    fake = RecordingFakeModel([AIMessage(content="", tool_calls=[
        {"name": "ConductResearch", "args": {"research_topic": "reducer 机制,详述..."}, "id": "c1"},
    ])])
    monkeypatch.setattr(dr, "configurable_model", fake)
    cmd = asyncio.run(dr.supervisor(state, config={"configurable": {}}))
    return cmd, fake


class TestSupervisorNode:
    """镜像 ReAct 的"思考"半步:三件套协议、不拼 system prompt、计数 +1。"""

    def test_routes_to_supervisor_tools_and_appends_response(self, monkeypatch):
        cmd, fake = run_supervisor(monkeypatch, seeded_state())
        assert cmd.goto == "supervisor_tools"
        msgs = cmd.update["supervisor_messages"]
        assert len(msgs) == 1 and msgs[0].tool_calls[0]["name"] == "ConductResearch"

    def test_binds_exactly_three_protocol_tools(self, monkeypatch):
        _, fake = run_supervisor(monkeypatch, seeded_state())
        names = {getattr(t, "__name__", None) or getattr(t, "name", None) for t in fake.bound_tools}
        assert names == {"ConductResearch", "ResearchComplete", "think_tool"}

    def test_no_system_prompt_assembled_in_node(self, monkeypatch):
        # supervisor 直接吃 state 里的 supervisor_messages——节点内不新增 SystemMessage
        state = seeded_state()
        _, fake = run_supervisor(monkeypatch, state)
        assert fake.last_input == state["supervisor_messages"]

    def test_research_iterations_increments(self, monkeypatch):
        cmd, _ = run_supervisor(monkeypatch, seeded_state(iterations=3))
        assert cmd.update["research_iterations"] == 4


###################
# Group C:supervisor_tools 拦截与 fan-out(跑编译好的 supervisor_subgraph)
###################

class FakeResearcherSubgraph:
    """researcher_subgraph 的替身:记录派活单,吐防火墙同款的两键 dict。"""

    def __init__(self):
        self.calls = []

    async def ainvoke(self, state, config=None):
        self.calls.append(state)
        topic = state["research_topic"]
        return {"compressed_research": f"提炼稿[{topic}]", "raw_notes": [f"raw[{topic}]"]}


def ai_calls(*calls: tuple[str, dict]) -> AIMessage:
    return AIMessage(content="", tool_calls=[
        {"name": name, "args": args, "id": f"call_{i}"}
        for i, (name, args) in enumerate(calls)
    ])


def run_supervisor_subgraph(monkeypatch, scripted, configurable=None, iterations=0):
    """跑整个 supervisor 子图:假 supervisor 模型按剧本吐,researcher 子图换替身。"""
    class ScriptedModel:
        def __init__(self, script):
            self._script = iter(script)
        def bind_tools(self, tools, **kwargs):
            return self
        def with_retry(self, **kwargs):
            return self
        def with_config(self, config):
            return self
        async def ainvoke(self, messages):
            return next(self._script)

    fake_researcher = FakeResearcherSubgraph()
    monkeypatch.setattr(dr, "configurable_model", ScriptedModel(scripted))
    monkeypatch.setattr(dr, "researcher_subgraph", fake_researcher)
    result = asyncio.run(
        dr.supervisor_subgraph.ainvoke(
            {
                "supervisor_messages": [
                    SystemMessage(content="You are a research supervisor..."),
                    HumanMessage(content="研究 LangGraph 的 reducer 机制"),
                ],
                "research_brief": "研究 LangGraph 的 reducer 机制",
                "research_iterations": iterations,
            },
            config={"configurable": configurable or {}},
        )
    )
    return result, fake_researcher


class TestSupervisorTools:
    """三类拦截 + 前置退出:全按名字转手,零真实执行。"""

    def test_no_tool_calls_exits_and_harvests_notes(self, monkeypatch):
        # 模型不调工具(纯文字)→ 退出条件 b;已有的 ToolMessage 内容被收割进 notes
        result, fake = run_supervisor_subgraph(monkeypatch, [
            ai_calls(("ConductResearch", {"research_topic": "话题甲"})),
            ai_calls(),  # 第二轮:零 tool_calls → 退出
        ])
        assert fake.calls, "第一轮应真的派了活"
        assert result["notes"] == ["提炼稿[话题甲]"], "退出时应收割对话里全部 ToolMessage"

    def test_research_complete_exits(self, monkeypatch):
        # 第一轮直接喊收工 → 退出条件 c,researcher 一次都不该被调
        result, fake = run_supervisor_subgraph(monkeypatch, [
            ai_calls(("ResearchComplete", {})),
        ])
        assert fake.calls == []
        assert result["notes"] == []

    def test_budget_precheck_blocks_execution(self, monkeypatch):
        # 前置检查的语义:预算已超时,哪怕模型这轮想派活,也一个都不执行。
        # (对比 researcher_tools 的后置:先执行完本轮才查预算——"厚道"与否的成本结构差异)
        result, fake = run_supervisor_subgraph(
            monkeypatch,
            [ai_calls(("ConductResearch", {"research_topic": "来不及了"}))],
            configurable={"max_researcher_iterations": 1},
            iterations=1,  # supervisor 节点 +1 后 =2 > 1 → 前置退出
        )
        assert fake.calls == [], "前置检查下,超预算这轮的派活单必须一张都不执行"

    def test_think_tool_inlined_not_executed(self, monkeypatch):
        # think_tool 内联造 ToolMessage,前缀 "Reflection recorded"
        result, _ = run_supervisor_subgraph(monkeypatch, [
            ai_calls(("think_tool", {"reflection": "先摸清概念再派活"})),
            ai_calls(),
        ])
        tool_msgs = [m for m in result["supervisor_messages"] if isinstance(m, ToolMessage)]
        assert len(tool_msgs) == 1
        assert tool_msgs[0].name == "think_tool"
        assert "Reflection recorded" in tool_msgs[0].content
        assert "先摸清概念再派活" in tool_msgs[0].content

    def test_fanout_two_topics_and_raw_notes_aggregated(self, monkeypatch):
        # 一轮两张派活单 → 并发两个子图调用;ToolMessage 与 tool_call_id 对齐;raw_notes 聚合
        result, fake = run_supervisor_subgraph(monkeypatch, [
            ai_calls(
                ("ConductResearch", {"research_topic": "话题甲"}),
                ("ConductResearch", {"research_topic": "话题乙"}),
            ),
            ai_calls(),
        ])
        assert [c["research_topic"] for c in fake.calls] == ["话题甲", "话题乙"]
        assert all(
            isinstance(c["researcher_messages"][0], HumanMessage) for c in fake.calls
        ), "派活单应以 HumanMessage 形式塞进 researcher 的对话"
        tool_msgs = [m for m in result["supervisor_messages"] if isinstance(m, ToolMessage)]
        assert {m.content for m in tool_msgs} == {"提炼稿[话题甲]", "提炼稿[话题乙]"}
        assert {m.tool_call_id for m in tool_msgs} == {"call_0", "call_1"}
        assert result["raw_notes"] == ["raw[话题甲]\nraw[话题乙]"], \
            "所有 researcher 的 raw_notes 应拼成一整条再装单元素 list"


###################
# Group D:预算切片 + 超发教育 + except 兜底
###################

class ExplodingResearcherSubgraph:
    """替身之二:一被派活就炸,用来验证 except 兜底不许把图炸穿。"""

    async def ainvoke(self, state, config=None):
        raise RuntimeError("researcher exploded mid-flight")


class TestSupervisorBudget:
    """三重预算的中间那道:单轮并发上限。超发不执行、不沉默、不炸图。"""

    def test_overflow_not_executed_but_answered(self, monkeypatch):
        # 预算 2,一轮派 3 张单:只跑前 2 张;第 3 张不执行但必须有教育性回执
        result, fake = run_supervisor_subgraph(
            monkeypatch,
            [
                ai_calls(
                    ("ConductResearch", {"research_topic": "话题甲"}),
                    ("ConductResearch", {"research_topic": "话题乙"}),
                    ("ConductResearch", {"research_topic": "话题丙"}),
                ),
                ai_calls(),
            ],
            configurable={"max_concurrent_research_units": 2},
        )
        assert [c["research_topic"] for c in fake.calls] == ["话题甲", "话题乙"], \
            "只允许执行预算内的前 N 张派活单"
        tool_msgs = [m for m in result["supervisor_messages"] if isinstance(m, ToolMessage)]
        assert {m.tool_call_id for m in tool_msgs} == {"call_0", "call_1", "call_2"}, \
            "每个 tool_call 都必须得到应答——包括被裁掉的"
        overflow_msg = next(m for m in tool_msgs if m.tool_call_id == "call_2")
        assert "Error" in overflow_msg.content and "2 or fewer" in overflow_msg.content, \
            "超发回执应是教育性的:告诉模型预算数字,让它下轮自我修正"

    def test_overflow_notes_not_polluted(self, monkeypatch):
        # 教育性回执是 ToolMessage,会被退出时的 get_notes_from_tool_calls 收割——
        # 这是源码的真实行为,先如实断言(它该不该被收进 notes,留给 R5 辩)
        result, _ = run_supervisor_subgraph(
            monkeypatch,
            [
                ai_calls(
                    ("ConductResearch", {"research_topic": "话题甲"}),
                    ("ConductResearch", {"research_topic": "话题乙"}),
                ),
                ai_calls(),
            ],
            configurable={"max_concurrent_research_units": 1},
        )
        assert len(result["notes"]) == 2, "notes = 1 份提炼稿 + 1 份超发回执(源码如实行为)"
        assert result["notes"][0] == "提炼稿[话题甲]", "预算 1:只有第一张单真的跑了"
        assert "Error: Did not run this research" in result["notes"][1], \
            "第二张单的教育性回执也进了 notes——源码如实行为,该不该留给 R5 辩"

    def test_researcher_exception_ends_gracefully(self, monkeypatch):
        # researcher 半路爆炸 → 不炸图,优雅收工,research_brief 保住
        class ScriptedModel:
            def __init__(self, script):
                self._script = iter(script)
            def bind_tools(self, tools, **kwargs):
                return self
            def with_retry(self, **kwargs):
                return self
            def with_config(self, config):
                return self
            async def ainvoke(self, messages):
                return next(self._script)

        monkeypatch.setattr(dr, "configurable_model", ScriptedModel([
            ai_calls(("ConductResearch", {"research_topic": "注定失败的话题"})),
        ]))
        monkeypatch.setattr(dr, "researcher_subgraph", ExplodingResearcherSubgraph())
        result = asyncio.run(
            dr.supervisor_subgraph.ainvoke(
                {
                    "supervisor_messages": [
                        SystemMessage(content="You are a research supervisor..."),
                        HumanMessage(content="研究一个注定失败的话题"),
                    ],
                    "research_brief": "研究一个注定失败的话题",
                    "research_iterations": 0,
                },
                config={"configurable": {}},
            )
        )
        assert result["research_brief"] == "研究一个注定失败的话题", "烂尾也要把 brief 带出墙"
        assert result["notes"] == [], "本轮没有任何成功回礼,notes 应为空"
