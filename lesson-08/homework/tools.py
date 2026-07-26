"""
L8 作业 · 共用工具层（**本文件已给全，不需要你改**）

这里把 Q5 那道题的"三类错误"落成了代码：

    BusinessError   业务性错误 → 包成 JSON 回传给模型，模型有机会自愈
    TransientError  瞬时性错误 → 应由代码层重试（**本节不实现**，L13 / capstone 收）
    FatalError      致命错误   → 直接终止 loop，对应 StopReason.TOOL_FATAL

作业里你要在 executor 里把 BusinessError 和 FatalError **分流**处理。
TransientError 本节按 FatalError 处理即可，但要在代码里留 `# TODO(L13): 重试` 标记。
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# 三类工具异常
# --------------------------------------------------------------------------
class ToolError(Exception):
    """所有工具异常的基类。"""


class BusinessError(ToolError):
    """业务性错误：参数不合法、数据不存在。模型换个参数/问用户就能绕开。"""


class TransientError(ToolError):
    """瞬时性错误：超时、限流、网络抖动。重试有用，回传给模型没用。"""


class FatalError(ToolError):
    """致命错误：依赖不可用、配置错、权限缺失。重试和回传都没用，只能终止 + 告警。"""


# --------------------------------------------------------------------------
# 假数据 + 故障开关（测试 TOOL_FATAL 用）
# --------------------------------------------------------------------------
FAKE_ORDERS = {
    "A123": {"status": "运输中", "shipped_at": "2026-06-18", "promised_days": 3, "actual_days": 9, "amount": 299.0},
    "B456": {"status": "已签收", "shipped_at": "2026-06-20", "promised_days": 3, "actual_days": 2, "amount": 158.0},
    "C789": {"status": "运输中", "shipped_at": "2026-06-22", "promised_days": 5, "actual_days": 11, "amount": 899.0},
    "D012": {"status": "已签收", "shipped_at": "2026-06-25", "promised_days": 3, "actual_days": 3, "amount": 49.9},
}

# 已提交的赔付（真实项目里这是数据库表；这里只为演示"不可逆写操作"）
_COMPENSATIONS: dict[str, float] = {}

# 故障注入开关：置 False 模拟"订单数据库连不上"
_DB_AVAILABLE = True


def set_db_available(available: bool) -> None:
    """测试/演示用：模拟依赖不可用。"""
    global _DB_AVAILABLE
    _DB_AVAILABLE = available


def reset_state() -> None:
    """测试用：清空赔付记录、恢复数据库可用。"""
    _COMPENSATIONS.clear()
    set_db_available(True)


# --------------------------------------------------------------------------
# 工具实现
# --------------------------------------------------------------------------
def query_order(order_id: str) -> str:
    if not _DB_AVAILABLE:
        raise FatalError("订单数据库连接失败（模拟故障）")
    order = FAKE_ORDERS.get(order_id)
    if order is None:
        raise BusinessError(f"查无此订单：{order_id}")
    return json.dumps(order, ensure_ascii=False)


def check_delay(order_id: str) -> str:
    """判断订单是否延迟发货，以及可赔付金额（承诺天数的每超 1 天赔 1% 订单额，上限 20%）。"""
    if not _DB_AVAILABLE:
        raise FatalError("订单数据库连接失败（模拟故障）")
    order = FAKE_ORDERS.get(order_id)
    if order is None:
        raise BusinessError(f"查无此订单：{order_id}")

    over = order["actual_days"] - order["promised_days"]
    delayed = over > 0
    rate = min(over * 0.01, 0.20) if delayed else 0.0
    return json.dumps(
        {
            "order_id": order_id,
            "delayed": delayed,
            "over_days": max(over, 0),
            "compensable_amount": round(order["amount"] * rate, 2),
        },
        ensure_ascii=False,
    )


def apply_compensation(order_id: str, amount: float) -> str:
    """提交赔付申请。**不可逆写操作** —— 注意它没有幂等键（capstone 的检查表会补）。"""
    if not _DB_AVAILABLE:
        raise FatalError("赔付服务不可用（模拟故障）")
    if order_id not in FAKE_ORDERS:
        raise BusinessError(f"查无此订单：{order_id}")
    if amount <= 0:
        raise BusinessError("赔付金额必须大于 0")

    _COMPENSATIONS[order_id] = _COMPENSATIONS.get(order_id, 0.0) + amount
    logger.info("compensation_applied order_id=%s amount=%.2f", order_id, amount)
    return json.dumps(
        {"order_id": order_id, "applied": amount, "total_applied": _COMPENSATIONS[order_id]},
        ensure_ascii=False,
    )


def list_recent_orders(month: str) -> str:
    """列出某月的订单号。month 形如 '2026-06'。"""
    if not _DB_AVAILABLE:
        raise FatalError("订单数据库连接失败（模拟故障）")
    ids = [oid for oid, o in FAKE_ORDERS.items() if o["shipped_at"].startswith(month)]
    if not ids:
        raise BusinessError(f"{month} 没有订单记录")
    return json.dumps({"month": month, "order_ids": ids}, ensure_ascii=False)


TOOL_IMPLS = {
    "query_order": query_order,
    "check_delay": check_delay,
    "apply_compensation": apply_compensation,
    "list_recent_orders": list_recent_orders,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_order",
            "description": "根据订单号查询订单状态、发货日期、承诺时效和订单金额",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string", "description": "订单号，例如 A123"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_delay",
            "description": "判断某订单是否延迟发货，并算出可赔付金额。判断是否该赔付时用这个，不要自己算。",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string", "description": "订单号，例如 A123"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_compensation",
            "description": "为延迟订单提交赔付申请。这是不可逆的写操作，只在 check_delay 确认延迟后调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号"},
                    "amount": {"type": "number", "description": "赔付金额，取 check_delay 返回的 compensable_amount"},
                },
                "required": ["order_id", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_recent_orders",
            "description": "列出某个月份的所有订单号，month 形如 '2026-06'",
            "parameters": {
                "type": "object",
                "properties": {"month": {"type": "string", "description": "月份，格式 YYYY-MM"}},
                "required": ["month"],
            },
        },
    },
]
