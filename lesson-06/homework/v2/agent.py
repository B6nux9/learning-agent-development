"""接线层 —— 所有会碰 LLM / 网络的东西都关在这一层。

分层设计(这次作业的核心):
    context.py   纯逻辑,零依赖,100% 可测      ← 你实现 + 你写测试
    agent.py     碰 LLM、碰网络、碰终端         ← 本文件,给你写好
    test_context.py  只测 context.py           ← 你补齐

为什么这么分?因为 agent.py 里的东西【很难测】:要网络、要 key、要花钱、结果还随机。
而 context.py 里的东西【很好测】。把难测的和好测的分开,你就能用便宜的单元测试
覆盖住大部分真正容易出错的逻辑。

这就是面试里"你怎么保证 agent 的质量/怎么做回归测试"的标准答案之一。
"""

import os
import json
from dataclasses import dataclass

from openai import OpenAI

from context import ContextManager

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

MODEL = "deepseek-chat"
CHEAP_MODEL = "deepseek-chat"     # 摘要这种小活用便宜/快的模型(L4 的教训)
MAX_TURNS = 8
COMPACT_THRESHOLD = 1500          # 用 API 实测 prompt_tokens 判断
KEEP_RECENT = 6


# ── 业务工具 ────────────────────────────────────────────────────────
FAKE_ORDERS = {
    "A123": {"status": "运输中", "carrier": "顺丰", "eta": "明天 18:00 前"},
    "B456": {"status": "已签收", "carrier": "京东", "eta": "已于昨天送达"},
}


def query_order(order_id: str) -> str:
    order = FAKE_ORDERS.get(order_id)
    if order is None:
        return json.dumps({"error": f"查无此订单:{order_id}"}, ensure_ascii=False)
    return json.dumps(order, ensure_ascii=False)


TOOLS = [{"type": "function", "function": {
    "name": "query_order",
    "description": "根据订单号查询物流状态、承运商、预计送达时间",
    "parameters": {"type": "object", "properties": {
        "order_id": {"type": "string", "description": "订单号,如 A123"}},
        "required": ["order_id"]}}}]

AVAILABLE_TOOLS = {"query_order": query_order}

SYSTEM_PROMPT = (
    "你是电商客服助手。\n"
    "【必须】涉及订单状态、物流、送达时间时,必须调用 query_order 查询后再回答。\n"
    "【禁止】禁止编造任何未经工具查询的订单信息;"
    "禁止只在回复中声称已查询而未实际调用工具。\n"
    "【输出】简洁中文,不超过 3 句。"
)


# ── 用量统计 ────────────────────────────────────────────────────────
@dataclass
class SessionStats:
    last_prompt_tokens: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    llm_calls: int = 0

    def record(self, usage) -> None:
        """主对话链:既计成本,也更新压缩阈值的判断依据。"""
        if usage is None:
            return
        self.last_prompt_tokens = usage.prompt_tokens
        self._accumulate(usage)

    def record_side_call(self, usage) -> None:
        """旁路调用(摘要/路由):只计成本,不更新 last_prompt_tokens。
        因为那是另一组 messages 的用量,混进来会污染压缩决策。"""
        if usage is None:
            return
        self._accumulate(usage)

    def _accumulate(self, usage) -> None:
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.llm_calls += 1

    def summary(self) -> str:
        return (f"调用 {self.llm_calls} 次 | 累计输入 {self.total_prompt_tokens} "
                f"| 累计输出 {self.total_completion_tokens}")


stats = SessionStats()


# ── 真实的摘要器:这就是要注入给 ContextManager 的那个依赖 ──────────────
SUMMARY_SYSTEM = """你是对话摘要器。

【任务】把用户提供的客服对话压缩成一段摘要,该摘要将作为后续对话的背景信息使用。

【必须保留】
1. 用户的身份信息(姓名、联系方式)与偏好(如指定的快递公司)
2. 对话中出现过的所有订单号,以及每个订单已确认的状态
3. 用户已提出但尚未解决的诉求

【禁止】
1. 禁止编造对话中未出现的信息
2. 禁止省略"必须保留"中的任何一项,即使它看起来无关紧要

【输出】纯文本,不超过 200 字,不使用 Markdown。"""


def llm_summarizer(messages: list[dict]) -> str:
    """真调 LLM 的摘要器。签名和 test 里的 fake_summarizer 完全一致 ——
    所以两者可以互换,这正是依赖注入能work的前提。"""
    lines = [f"{m.get('role', '')}: {m.get('content') or ''}"
             for m in messages if m.get("content")]
    response = client.chat.completions.create(
        model=CHEAP_MODEL,
        messages=[{"role": "system", "content": SUMMARY_SYSTEM},
                  {"role": "user", "content": "\n".join(lines)}],
        temperature=0,
        max_tokens=1024,
    )
    stats.record_side_call(response.usage)
    return response.choices[0].message.content


ctx = ContextManager(
    summarizer=llm_summarizer,      # ← 注入真实实现;测试里注入假的
    threshold=COMPACT_THRESHOLD,
    keep_recent=KEEP_RECENT,
    strategy="hybrid",
)


def run_agent(messages: list[dict]) -> str:
    for _ in range(MAX_TURNS):
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        stats.record(response.usage)
        msg = response.choices[0].message

        # 入口归一化:SDK 对象 -> dict,避免下游出现"混血列表"
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            return msg.content

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            try:
                result = AVAILABLE_TOOLS[name](**args)
            except Exception as e:
                result = json.dumps({"error": str(e)}, ensure_ascii=False)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
    return "抱歉,这个问题我暂时处理不了,已为您转接人工客服"


def main():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("(多聊几轮观察 [ctx] 日志;输入 退出 结束)")
    while True:
        user_input = input("你> ")
        if user_input.lower() in ("quit", "exit", "退出"):
            print(f"[ctx] 本次会话:{stats.summary()}")
            break

        messages.append({"role": "user", "content": user_input})

        result = ctx.compact(messages, current_tokens=stats.last_prompt_tokens)
        messages = result.messages
        if result.compacted:
            print(f"[ctx] 已压缩:{result.dropped_count} 条旧消息 -> 摘要,"
                  f"保留 {result.kept_count} 条原文")

        print(f"客服助手: {run_agent(messages)}")
        print(f"[ctx] 本轮实测输入 {stats.last_prompt_tokens} tokens | {stats.summary()}")


if __name__ == "__main__":
    main()
