"""
阶段二 Capstone · 电商售后智能客服 Agent —— 工具层 (tools.py)

┌─────────────────────────────────────────────────────────────────────┐
│ 全项目文件蓝图 (蓝图先行，先看整栋楼，再盖第一层)                     │
│                                                                       │
│   tools.py    ← 工具层：query_order / query_logistics /               │
│                 search_policy / process_refund / escalate_to_human    │
│                 【纪律】user_id 由代码从会话注入，绝不接受模型给的 id  │
│   session.py  ← 会话/记忆层：已登录用户是谁、预加载的客户信息、        │
│                 对话历史 (复用 L5 记忆 + L6 上下文预算)                │
│   agent.py    ← 核心循环 + 编排：意图路由(模型) → 分派工具 → 观察      │
│                 (复用 L8 executor 三类分流)                            │
│   main.py     ← 入口/实验：命令行跟 agent 对话                         │
│   test_agent.py ← 测试：至少 1 正 1 反 (门禁第二条)                    │
│                                                                       │
│ 写作顺序：由内向外。今天只纵切「查订单」一条最小可跑链路：            │
│   tools.query_order  →  agent 里最小 loop  →  main 里问一句           │
│ 打通看到它转起来，再逐层加厚 (退款阈值 → RAG → 转人工)。              │
└─────────────────────────────────────────────────────────────────────┘

本文件今天的任务：只写 query_order 一个函数 (block 1)。
数据(FAKE_ORDERS)我给你，你不用管；把精力放在**归属校验**这个设计要点上。
"""

from __future__ import annotations


# --------------------------------------------------------------------------
# 假数据（真实项目里是数据库表；这里给全，不用你写）
# 注意每条订单都带 user_id —— 这是「越权校验」能被测出来的前提。
# --------------------------------------------------------------------------
FAKE_ORDERS = {
    "A123": {"user_id": "u_zhang", "status": "运输中", "shipped_at": "2026-07-20", "amount": 199.0},
    "B456": {"user_id": "u_zhang", "status": "已签收", "shipped_at": "2026-07-18", "amount": 89.0},
    "C789": {"user_id": "u_li",    "status": "运输中", "shipped_at": "2026-07-22", "amount": 899.0},
    "D999": {"user_id": "u_zhang", "status": "已签收", "shipped_at": "2026-07-15", "amount": 699.0},
}


# --------------------------------------------------------------------------
# block 1 —— 你来写：query_order
# --------------------------------------------------------------------------
def query_order(user_id: str, order_id: str) -> dict:
    """查一笔订单。

    接口契约 (coach 给你签名+输入输出+约束，函数体你写)：
      输入
        user_id  : str  —— **由代码从已登录会话注入**，不是模型给的
        order_id : str  —— 模型/用户给的订单号，如 "A123"
      输出 (统一返回 dict，别抛异常给上层——上层要把它回传给模型)
        命中且属于本人 : {"ok": True,  "order": {...该订单字段...}}
        订单不存在     : {"ok": False, "reason": "order_not_found"}
        订单存在但不属于本人 : {"ok": False, "reason": "forbidden"}
      约束 (这是本 block 的考点，别写漏)
        1. 只有「订单存在」且「order.user_id == 传入的 user_id」才返回数据。
        2. 「不存在」和「不属于本人」要分成两个不同 reason
           —— 想想为什么不能合并成一个？(面试追问，写完回答我)
    """
    # TODO(你来写): 按上面契约实现
    order = FAKE_ORDERS.get(order_id)
    if order is None:
      return {"ok": False, "reason": "order_not_found"}
    if order["user_id"] != user_id:
      return {"ok": False, "reason": "forbidden"}
    return {"ok": True, "status": order["status"], "shipped_at": order["shipped_at"], "amount": order["amount"]}


# --------------------------------------------------------------------------
# block 4 —— 你来写：process_refund（高危写操作，招牌菜）
# --------------------------------------------------------------------------
REFUND_AUTO_LIMIT = 200.0  # 阈值 hard-code 在代码，不让 LLM 判（可靠性来自约束）

# 已退款的账（真实项目里是数据库表；退款是不可逆写操作，要能查重防重复退）
_REFUNDS: dict[str, float] = {}


def process_refund(user_id: str, order_id: str) -> dict:
    """发起退款。**高危写操作**——能不能退、退多少，全由代码定，不信模型。

    接口契约：
      输入
        user_id  : str  —— 会话注入（继续锁死来源）
        order_id : str  —— 模型/用户给的订单号
        （注意：**没有 amount 参数**。金额是真值，代码从订单查，不接受模型报数。）
      规则（按顺序，每条都是一道闸）
        1. 归属+存在校验：**复用 query_order** —— 它已经做了「存在 + 属于本人」并返回真实 amount。
           不 ok 就把它的结果**原样透传**（order_not_found / forbidden 自动就对了）。
        2. 幂等防重复退：order_id 已在 _REFUNDS 里 → {"ok": False, "reason": "already_refunded"}。
        3. 金额取真值：amount 用第 1 步查回来的，**不是模型给的**。
        4. 阈值闸（hard-code）：amount > REFUND_AUTO_LIMIT → 不自动退，
           返回 {"ok": False, "reason": "needs_human", "amount": amount}（交给上层转人工）。
        5. 放行：记账 _REFUNDS[order_id] = amount，返回 {"ok": True, "refunded": amount}。
      面试追问（写完答我）：第 4 步为什么必须是代码里的 if，而不是写进 SYSTEM_PROMPT 让模型「注意别退超 200」？
    """
    # TODO(你来写): 按契约实现
    order = query_order(user_id, order_id)
    if not order["ok"]:
      return order
    if order_id in _REFUNDS:
       return {"ok": False, "reason": "already_refunded"}
    amount = order["amount"]
    if amount > REFUND_AUTO_LIMIT:
      return {"ok": False, "reason": "needs_human", "amount": amount}
    _REFUNDS[order_id] = amount
    return {"ok": True, "refunded": amount}
