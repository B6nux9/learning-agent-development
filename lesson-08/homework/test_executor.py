"""
L8 作业 · 测试脚手架

===========================================================================
分工（按之前定的门禁期安排）：**假客户端和测试骨架我搭好了，断言你来补。**
capstone 时你会从零自己写整套测试，现在先把"怎么测一个碰网络的 loop"这个手法学会。

核心手法叫 **test double（测试替身）**：
    run_react 的 client 是注入进来的 → 测试时塞一个按脚本回答的 FakeClient
    → 于是"模型会怎么答"变成了**你说了算**，才能稳定复现 MAX_STEPS / NO_PROGRESS
      这些平时撞不到的路径。
    这就是 executor.py 里 client 和 guard 都走参数注入的原因 —— 不是为了好看，
    是为了**可测**。

跑法：
    uv run pytest lesson-08/homework -v

v3 门禁条件 2 只要求"1 个正常路径 + 1 个失败路径且绿"，
但下面 8 个位置都值得补齐 —— 每一个都对应一种真实线上故障。
===========================================================================
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

import tools as tools_mod
from executor import LoopGuard, RunResult, StopReason, ToolCallRecord, _execute_tool, run_react
from tools import TOOL_IMPLS, TOOLS

SYSTEM_PROMPT = "你是电商客服助手。"


# ===========================================================================
# 测试替身（已给你，不用改）
# ===========================================================================
def _tool_call(call_id: str, name: str, arguments: str):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _message(content=None, tool_calls=None):
    msg = SimpleNamespace(role="assistant", content=content, tool_calls=tool_calls)

    def model_dump(exclude_none: bool = False, **_kw):
        d: dict = {"role": "assistant", "content": content}
        if tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ]
        if exclude_none:
            d = {k: v for k, v in d.items() if v is not None}
        return d

    msg.model_dump = model_dump
    return msg


def fake_response(*, content=None, tool_calls=None, prompt_tokens: int = 100):
    """造一个长得像 OpenAI SDK 返回值的假 response。"""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=_message(content, tool_calls))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens),
    )


class FakeClient:
    """按脚本依次返回预设 response；脚本用完后**重复最后一条**（方便测死循环路径）。"""

    def __init__(self, script: list):
        self._script = list(script)
        self._i = 0
        self.calls: list[dict] = []  # 记录每次调用的入参，断言时可以查

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._i < len(self._script):
            resp = self._script[self._i]
            self._i += 1
            return resp
        return self._script[-1]


def make_guard(**overrides) -> LoopGuard:
    defaults = dict(max_steps=5, no_progress_threshold=3, max_prompt_tokens=10_000)
    defaults.update(overrides)
    return LoopGuard(**defaults)


def run(client, guard=None) -> RunResult:
    return run_react(
        "测试问题",
        client=client,
        guard=guard or make_guard(),
        tools=TOOLS,
        tool_impls=TOOL_IMPLS,
        system_prompt=SYSTEM_PROMPT,
    )


@pytest.fixture(autouse=True)
def _reset_tool_state():
    tools_mod.reset_state()
    yield
    tools_mod.reset_state()


# ===========================================================================
# ① 正常路径 —— 这个我写全了，当模板看
# ===========================================================================
def test_final_answer_without_tools():
    """模型第一轮就直接作答（不需要工具）→ FINAL_ANSWER。"""
    client = FakeClient([fake_response(content="我们 18 点下班。", prompt_tokens=120)])

    result = run(client)

    assert result.stop_reason is StopReason.FINAL_ANSWER
    assert result.final_answer == "我们 18 点下班。"
    assert result.steps == 1
    assert result.total_prompt_tokens == 120
    assert len(client.calls) == 1


def test_tool_then_final_answer():
    """一轮工具调用 → 第二轮给最终答案。这是最典型的 ReAct 两拍。"""
    client = FakeClient(
        [
            fake_response(
                tool_calls=[_tool_call("c1", "query_order", json.dumps({"order_id": "A123"}))],
                prompt_tokens=200,
            ),
            fake_response(content="A123 正在运输中。", prompt_tokens=350),
        ]
    )

    result = run(client)

    # TODO-T1: 补断言。至少覆盖 3 件事：
    #   ① stop_reason 是什么
    #   ② steps 是几（想清楚：一次"调工具"算不算一步？你 LoopGuard 里怎么定义的？）
    #   ③ total_prompt_tokens 应该是多少（提示：**两轮都要算**，别只算最后一轮）
    assert result.stop_reason is StopReason.FINAL_ANSWER
    assert result.final_answer == "A123 正在运输中。"
    assert result.steps == 2
    assert result.total_prompt_tokens == 200 + 350
    assert len(client.calls) == 2


# ===========================================================================
# ② 被迫结束的四条路径 —— 断言你来补
# ===========================================================================
def test_max_steps_exceeded():
    """模型每轮都点单、永远不给最终答案 → 应该被 max_steps 掐掉。

    注意脚本里每轮点的是**不同**订单号，避免误触发 NO_PROGRESS ——
    这两条路径要能分得开，否则测试就没意义了。
    """
    script = [
        fake_response(
            tool_calls=[_tool_call(f"c{i}", "query_order", json.dumps({"order_id": oid}))],
            prompt_tokens=100 * (i + 1),
        )
        for i, oid in enumerate(["A123", "B456", "C789", "D012", "A123", "B456", "C789"])
    ]
    client = FakeClient(script)

    result = run(client, make_guard(max_steps=3, no_progress_threshold=99))

    # TODO-T2: 补断言。除了 stop_reason，**还要断言 final_answer 是什么** ——
    #          这是本节的核心：被迫结束时上层拿到的是什么？想清楚再写。
    assert result.stop_reason is StopReason.MAX_STEPS
    assert result.final_answer == None
    assert result.steps == 3
    assert result.total_prompt_tokens == 100 + 200 + 300
    assert len(client.calls) == 3


def test_no_progress_detected():
    """模型连续点同一个工具、同样的参数 → 原地转圈，应该在 max_steps 之前就被掐掉。"""
    stuck = fake_response(
        tool_calls=[_tool_call("c1", "query_order", json.dumps({"order_id": "A123"}))],
        prompt_tokens=150,
    )
    client = FakeClient([stuck])  # 脚本只有一条 → 会一直重复

    result = run(client, make_guard(max_steps=20, no_progress_threshold=3))

    # TODO-T3: 补断言。除了 stop_reason，**还要断言 steps** ——
    #          验证它确实是在第 3 轮左右停的，而不是跑到 20 才停。
    #          （如果只断言 stop_reason，检测阈值写错成 10 你也发现不了。）
    assert result.stop_reason is StopReason.NO_PROGRESS
    assert result.steps == 3
    assert result.total_prompt_tokens == 150 * 3
    assert len(client.calls) == 3


def test_tool_fatal_stops_immediately():
    """工具抛 FatalError（数据库连不上）→ 立刻终止，不给模型自愈的机会。"""
    tools_mod.set_db_available(False)
    client = FakeClient(
        [
            fake_response(
                tool_calls=[_tool_call("c1", "query_order", json.dumps({"order_id": "A123"}))],
                prompt_tokens=200,
            ),
            fake_response(content="不该走到这一轮", prompt_tokens=300),
        ]
    )

    result = run(client)

    # TODO-T4: 补断言。**最关键的一条**：断言 client 只被调用了 1 次 ——
    #          证明 fatal 之后没有再去问模型（否则就是在白烧钱）。
    #          提示：len(client.calls)
    assert result.stop_reason is StopReason.TOOL_FATAL
    assert result.steps == 1
    assert result.total_prompt_tokens == 200
    assert len(client.calls) == 1


def test_budget_exceeded():
    """累计 prompt_tokens 超预算 → BUDGET_EXCEEDED。"""
    script = [
        fake_response(
            tool_calls=[_tool_call(f"c{i}", "query_order", json.dumps({"order_id": oid}))],
            prompt_tokens=4_000,
        )
        for i, oid in enumerate(["A123", "B456", "C789", "D012"])
    ]
    client = FakeClient(script)

    result = run(client, make_guard(max_steps=99, no_progress_threshold=99, max_prompt_tokens=9_000))

    # TODO-T5: 补断言。
    assert result.stop_reason is StopReason.BUDGET_EXCEEDED
    assert result.final_answer == None
    assert result.steps == 3
    assert result.total_prompt_tokens == 4_000 * 3
    assert len(client.calls) == 3


# ===========================================================================
# ③ 你的老毛病专项测试
# ===========================================================================
def test_content_none_is_handled():
    """模型返回 content=None 且没有 tool_calls（真事，你 L6 debug 路由时撞过）。

    这个测试存在的唯一理由：**逼你写兜底**。
    你的头号短板"多部分任务只做一半"已经出现 5 次，这次用测试钉住。
    """
    client = FakeClient([fake_response(content=None, prompt_tokens=100)])

    result = run(client)

    # TODO-T6: 补断言。先想清楚**你希望**发生什么：
    #   选项 A：当成 FINAL_ANSWER，final_answer 给一句兜底文案
    #   选项 B：当成异常情况，用某个 stop_reason 标记出来
    #   两种都是合理设计，**选一个、在注释里写理由、然后让实现和断言对齐**。
    #   唯一不可接受的是：final_answer 是 None 而 stop_reason 是 FINAL_ANSWER
    #   —— 那上层会把 None 直接发给用户。
    assert result.stop_reason is StopReason.FINAL_ANSWER
    assert result.final_answer == ""
    assert result.steps == 1
    assert result.total_prompt_tokens == 100
    assert len(client.calls) == 1


# ===========================================================================
# ④ 工具执行层的 5 条路径
# ===========================================================================
def test_execute_tool_invalid_json():
    """模型吐出非法 JSON（截断/多余逗号）—— 高频事件，你 quiz 里自己指出来的那条。"""
    result, fatal = _execute_tool("query_order", '{"order_id": "A123"', TOOL_IMPLS)

    # TODO-T7: 补断言。两件事：
    #   ① fatal 应该是什么（模型能自愈吗？）
    #   ② result 必须是**字符串**且能被 json.loads 解析出 error 字段
    #      —— 硬约束：每个 tool_call_id 必须有且仅有一条对应回复，所以任何路径都要返回字符串。
    assert fatal is False
    error_obj = json.loads(result)
    assert "error" in error_obj
    assert isinstance(error_obj["error"], str)


def test_execute_tool_unknown_tool_name():
    """模型幻觉出一个不存在的工具名。"""
    result, fatal = _execute_tool("refund_everything", "{}", TOOL_IMPLS)

    # TODO-T8: 补断言。想清楚：这算业务错误还是致命错误？
    #          （提示：把"没有这个工具"回传给模型，它有没有可能换个工具重来？）
    assert fatal is False
    error_obj = json.loads(result)
    assert "error" in error_obj
    assert isinstance(error_obj["error"], str)


# ===========================================================================
# ⑤ Part B 的纯逻辑：并行分组
# ===========================================================================
def test_parallel_groups_basic():
    """s1 → (s2, s3) → s4：中间那层能并行。"""
    from planner import Plan, PlanStep, parallel_groups

    plan = Plan(
        steps=[
            PlanStep(id="s1", tool="list_recent_orders", arguments={"month": "2026-06"}),
            PlanStep(id="s2", tool="check_delay", arguments={"order_id": "A123"}, depends_on=["s1"]),
            PlanStep(id="s3", tool="check_delay", arguments={"order_id": "C789"}, depends_on=["s1"]),
            PlanStep(id="s4", tool="apply_compensation", arguments={}, depends_on=["s2", "s3"]),
        ]
    )

    groups = parallel_groups(plan)

    # TODO-T9: 补断言。注意 s2/s3 的**顺序不该被要求** —— 用 set 比较，
    #          否则你的测试会依赖实现的遍历顺序（脆弱测试）。
    assert len(groups) == 3
    assert groups[0] == {"s1"}
    assert set(groups[1]) == {"s2", "s3"}
    assert groups[2] == {"s4"}


def test_parallel_groups_detects_cycle():
    """模型吐出环形依赖 s1→s2→s1。"""
    from planner import Plan, PlanStep, parallel_groups

    plan = Plan(
        steps=[
            PlanStep(id="s1", tool="query_order", arguments={}, depends_on=["s2"]),
            PlanStep(id="s2", tool="query_order", arguments={}, depends_on=["s1"]),
        ]
    )

    # TODO-T10: 补断言。你在 planner.py TODO-2 里决定了"撞到环怎么办"，
    #           这里按那个决定断言（抛异常就用 pytest.raises，返回空就断言返回值）。
    with pytest.raises(ValueError):
        parallel_groups(plan)