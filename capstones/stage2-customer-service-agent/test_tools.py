"""
阶段二 Capstone · 工具层单元测试 (test_tools.py)

门禁第二条：至少 1 正 1 反，全绿。这套测试也是后面改 RAG/prompt 时的**回归网**。

为什么先测 tools 层：它是**纯逻辑、不碰网络**——同样输入永远同样输出，测起来又快又稳。
（碰网络的 run() 要用「测试替身」，你 L8 学过那手法，留到后面测。）

pytest 约定（记住这几条就够起步）：
  - 文件名 test_*.py、函数名 test_* → pytest 自动发现，不用注册。
  - 每个 test 函数里用 assert 断言；assert 为假 → 这条测试红。
  - 一个 test 只测一个行为，函数名就是这个行为的描述。

跑法：
    uv run pytest capstones/stage2-customer-service-agent/ -v
"""

from __future__ import annotations

import pytest

import tools as tools_mod
from tools import process_refund, query_order, escalate_to_human


# ===========================================================================
# fixture：测试隔离。process_refund / escalate_to_human 会写全局台账
# (_REFUNDS / _TICKETS)，不清理会互相污染、产生执行顺序依赖 (flaky test)。
# 拆两个 autouse fixture 各管一个台账（单一职责、名字自解释）：每个测试前后各清一次。
# ===========================================================================
@pytest.fixture(autouse=True)
def reset_refunds():
    tools_mod._REFUNDS.clear()
    yield
    tools_mod._REFUNDS.clear()


@pytest.fixture(autouse=True)
def reset_tickets():
    tools_mod._TICKETS.clear()
    yield
    tools_mod._TICKETS.clear()
# ===========================================================================
# query_order —— 正例模板（happy path）
# ===========================================================================
def test_query_order_owner_sees_own_order():
    # Arrange：u_zhang 是 A123 的主人（见 FAKE_ORDERS）
    # Act：本人查自己的订单
    result = query_order("u_zhang", "A123")
    # Assert：应查到，且金额是订单里的真值
    assert result["ok"] is True
    assert result["amount"] == 199.0


# ===========================================================================
# query_order 两个反例（AAA 模板）
# ===========================================================================
def test_query_order_forbidden_for_others_order():
    """反例①·越权：u_zhang 查 C789（属于 u_li）。
    契约：应返回 ok=False，且 reason == "forbidden"（不是 not_found）。
    """
    result = query_order("u_zhang", "C789")
    assert result["ok"] is False
    assert result["reason"] == 'forbidden'


def test_query_order_not_found_for_missing_order():
    """反例②·不存在：查一个 FAKE_ORDERS 里没有的订单号（如 "Z999"）。
    契约：应返回 ok=False，且 reason == "order_not_found"。
    """
    result = query_order("u_zhang", "Z999")
    assert result["ok"] is False
    assert result["reason"] == 'order_not_found'


# ===========================================================================
# process_refund —— 招牌菜（正例：阈值内自动退）
# ===========================================================================
def test_process_refund_auto_approves_under_limit():
    # Arrange + Act：u_zhang 退 A123（199 ≤ 200，本人）
    result = process_refund("u_zhang", "A123")
    # Assert：应自动退，金额是订单真值
    assert result["ok"] is True
    assert result["refunded"] == 199.0


def test_process_refund_needs_human_over_limit():
    """反例·超阈值：u_zhang 退 D999（699 > 200，本人）。
    契约：ok=False，reason == "needs_human"（阈值闸拦下，转人工）。
    """
    result = process_refund("u_zhang", "D999")
    assert result["ok"] is False
    assert result["reason"] == 'needs_human'


def test_process_refund_idempotent_blocks_double_refund():
    """幂等·防重复退：对 A123 连退两次。
    契约：第一次 ok=True；**第二次** ok=False 且 reason == "already_refunded"。
    （这条测试故意在一个测试里调两次——正好验证 fixture 让它和别的测试互不干扰。）
    """
    first_result = process_refund("u_zhang", "A123")
    assert first_result["ok"] is True
    assert first_result["refunded"] == 199.0

    second_result = process_refund("u_zhang", "A123")
    assert second_result["ok"] is False
    assert second_result["reason"] == 'already_refunded'


def test_escalate_to_human_records_ticket():
    """转人工：调用 escalate_to_human 后，_TICKETS 应该记录一条工单。
    契约：调用后 _TICKETS 里应有一条记录，且 reason/summary 与调用时一致。
    """
    result = escalate_to_human("u_zhang", "over_refund_limit", "要退D999超限")
    assert result["ok"] is True
    assert result.get("terminal") is True
    assert result.get("ticket_id") == "T0001"
    assert len(tools_mod._TICKETS) == 1
    assert tools_mod._TICKETS[0]["reason"] == "over_refund_limit"
    assert tools_mod._TICKETS[0]["user_id"] == "u_zhang"

    second_result = escalate_to_human("u_li", "policy_not_covered", "问的政策没覆盖")
    assert len(tools_mod._TICKETS) == 2
    assert second_result.get("ticket_id") == "T0002"
    assert tools_mod._TICKETS[1]["reason"] == "policy_not_covered"
    assert tools_mod._TICKETS[1]["user_id"] == "u_li"