"""
L10 · 最小 MCP client (mcp_client.py) —— 连上 server，发现工具，调用工具。

这就是 MCP 的 client-server 一个完整来回（我给你写全，你读+跑，看清机制）：
  1. 启动 server 子进程（stdio 传输：通过它的 stdin/stdout 通信）
  2. initialize —— 握手
  3. list_tools() —— **工具发现**：client 问 server「你有哪些工具？」，不用硬编码
  4. call_tool(...) —— 按 schema 传参调用

跑法：uv run python lesson-10/mcp_client.py
（Windows 中文报编码错就前缀 PYTHONUTF8=1）
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = str(Path(__file__).with_name("mcp_server.py"))


async def main() -> None:
    # 用当前解释器（.venv 里的 python，装了 mcp）启动 server 子进程
    params = StdioServerParameters(command=sys.executable, args=[SERVER])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()  # 握手

            # ① 工具发现：server 自报有哪些工具（description 来自 docstring，schema 来自类型注解）
            listed = await session.list_tools()
            print("=== 发现的工具（list_tools）===")
            for t in listed.tools:
                print(f"  工具名: {t.name}")
                print(f"  说明:   {t.description.splitlines()[0]}")
                print(f"  参数:   {list(t.inputSchema.get('properties', {}))}")

            # 注意：现在只传 order_id —— 身份 user_id 由 server 侧注入，client 无从指定

            # ② 正常：查自己的订单（server 绑定的 SESSION_USER_ID=u_zhang）
            print("\n=== call_tool: query_order(A123) ===")
            r1 = await session.call_tool("query_order", {"order_id": "A123"})
            print(" ", r1.content[0].text)

            # ③ 查别人的订单 C789（属于 u_li）——client 无从声明"我是 u_li" → forbidden
            print("\n=== call_tool: query_order(C789)  # 别人的订单 ===")
            r2 = await session.call_tool("query_order", {"order_id": "C789"})
            print(" ", r2.content[0].text)

            # ④ 作弊尝试：client 硬塞 user_id 想冒充 u_li —— 看 server 认不认
            print("\n=== 作弊: query_order(C789, user_id=u_li)  # 硬塞身份 ===")
            try:
                r3 = await session.call_tool("query_order", {"order_id": "C789", "user_id": "u_li"})
                print("  server 返回:", r3.content[0].text, " ← user_id 被无视，仍以 server 身份为准")
            except Exception as e:
                print("  被 schema 挡下:", type(e).__name__)


if __name__ == "__main__":
    asyncio.run(main())
