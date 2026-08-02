"""
L10 · 最小 MCP server (mcp_server.py) —— 把工具用 MCP 标准暴露出来。

书 Ch4 用官方 mcp SDK 的 FastMCP：**一个普通函数 + @mcp.tool() = 一个 MCP 工具**。
  - 函数的 docstring → 工具的 description（模型看的"什么时候用"说明书）
  - 函数的类型注解 → 参数的 JSON Schema（模型看的参数约束）
这正是书里"工具描述的艺术"：描述和 schema 决定模型用得准不准。

⚠️ stdio 传输：这个 server 从标准输入读请求、标准输出写响应。
   **绝对不要在本文件往 stdout print！** 那会污染协议（要调试用 stderr）。

一般不直接跑，由 client 启动（见 mcp_client.py）。
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("order-service")  # 给这个 MCP server 起个名

# 假订单库（同你 capstone 的 FAKE_ORDERS，最小版；真实项目是数据库）
FAKE_ORDERS = {
    "A123": {"user_id": "u_zhang", "status": "运输中", "amount": 199.0},
    "C789": {"user_id": "u_li", "status": "运输中", "amount": 899.0},
}


# ══════════════════════════════════════════════════════════════════════
# 你来写：把 query_order 暴露成一个 MCP 工具
#   —— 逻辑你写过好几遍；这里的新东西只有上面那行 @mcp.tool()
# ══════════════════════════════════════════════════════════════════════
SESSION_USER_ID = "u_zhang"  # 假设当前会话的用户是 u_zhang

@mcp.tool()
def query_order(order_id: str) -> dict:
    """查询一笔订单的状态和金额。用户询问订单或物流时调用。

    契约（同你 capstone 的 query_order）：
      - 订单不存在        → {"ok": False, "reason": "order_not_found"}
      - 存在但不属于本人  → {"ok": False, "reason": "forbidden"}
      - 命中且属于本人    → {"ok": True, "status": ..., "amount": ...}
    """
    order = FAKE_ORDERS.get(order_id)
    if not order:
        return {"ok": False, "reason": "order_not_found"}

    if order["user_id"] != SESSION_USER_ID:
        return {"ok": False, "reason": "forbidden"}

    return {"ok": True, "status": order["status"], "amount": order["amount"]}


if __name__ == "__main__":
    mcp.run()  # 默认 stdio 传输
