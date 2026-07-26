"""
L8 作业 · Part C：ReAct vs Plan-and-Execute 实测对比

===========================================================================
讲义 §3 那张对比表是**我告诉你的**。这一步是你自己把它跑出来。

面试里"你为什么选 ReAct 不选 Plan-and-Execute"这种问题，
答"因为我们场景短对话"是及格，答"我在同一组任务上实测过，
单步任务 P&E 多花 1 次 LLM 调用和 N ms 首延迟，收益为零"是加分。

⚠️ 本文件共有 **3 个 TODO**。
===========================================================================
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass

from openai import OpenAI

from executor import LoopGuard, RunResult, run_react
from planner import run_plan_execute
from tools import TOOL_IMPLS, TOOLS, reset_state

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是电商客服助手。需要订单信息时必须调用工具查询，绝不编造。"
    "判断是否延迟、赔付多少，必须以 check_delay 的返回为准，不要自己算。"
)


# ===========================================================================
# 任务集
# ===========================================================================
@dataclass
class Task:
    tid: str
    question: str
    shape: str          # 任务形状：single_step / parallel_fanout / branch_on_observation
    expectation: str    # 你预期哪种范式赢、为什么。**跑之前先写下来**，跑完再看打脸没有。


TASKS = [
    Task(
        tid="T1",
        question="我的订单 A123 到哪了？",
        shape="single_step",
        expectation="ReAct 赢：一步就完，P&E 白付一轮规划延迟。",
    ),
    Task(
        tid="T2",
        question="帮我看看 2026-06 的订单里有哪些延迟发货了，延迟的都申请赔付。",
        shape="parallel_fanout",
        expectation="P&E 赢：订单之间彼此独立，可并行；ReAct 要串行跑很多轮。",
    ),
    # TODO-C1: 加第三个任务 T3，形状是 branch_on_observation。
    #   设计要求：**规划期的信息不足以定计划**，必须先看到中间结果才知道后面怎么走。
    #   （回扣讲义 §4："中间结果决定后续分支" → 计划开头就是猜的）
    #   提示：用 tools.py 里的假数据设计一个"如果……就……否则……"的问题，
    #         而且要让"如果"的答案在提问时无法从字面判断。
    #   写完在 expectation 里先押注：你觉得 P&E 会怎么翻车？
]


# ===========================================================================
# 跑一轮
# ===========================================================================
@dataclass
class Measurement:
    tid: str
    mode: str
    stop_reason: str
    llm_calls: int
    prompt_tokens: int
    elapsed_s: float
    answer: str | None
    correct: bool | None = None  # 跑完人工判，填进 result.json


def measure(task: Task, mode: str, *, client) -> Measurement:
    reset_state()
    t0 = time.perf_counter()

    if mode == "react":
        result: RunResult = run_react(
            task.question,
            client=client,
            guard=LoopGuard(max_steps=15, no_progress_threshold=3, max_prompt_tokens=120_000),
            tools=TOOLS,
            tool_impls=TOOL_IMPLS,
            system_prompt=SYSTEM_PROMPT,
        )
    elif mode == "plan_execute":
        result = run_plan_execute(
            task.question,
            client=client,
            tools=TOOLS,
            tool_impls=TOOL_IMPLS,
            max_replans=2,
            auto_approve=True,
        )
    else:
        raise ValueError(f"未知模式：{mode}")

    return Measurement(
        tid=task.tid,
        mode=mode,
        stop_reason=result.stop_reason.value,
        llm_calls=result.steps,
        prompt_tokens=result.total_prompt_tokens,
        elapsed_s=round(time.perf_counter() - t0, 2),
        answer=result.final_answer,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

    rows: list[Measurement] = []
    for task in TASKS:
        for mode in ("react", "plan_execute"):
            logger.info("running task=%s mode=%s", task.tid, mode)
            rows.append(measure(task, mode, client=client))

    # TODO-C2: 输出一张对比表（markdown 格式，直接能贴进 findings.md）。
    #   列：任务 / 形状 / 模式 / stop_reason / LLM调用数 / prompt_tokens / 耗时 / 答案是否正确
    #   ⚠️ "答案是否正确"没法自动判 —— 先留空，跑完你自己填。
    #      （**这个"没法自动判"的痛点，就是 L12 要上 LLM-as-judge 的理由**。
    #        你 L7 建评估集时已经撞过一次"子串匹配区分不了确认与否认"，这是第二次。）
    #   把原始数据也存一份 JSON，方便复跑对比。
    raise NotImplementedError("TODO-C2")


if __name__ == "__main__":
    main()

# ===========================================================================
# TODO-C3（交付物）：跑完后写 `findings.md`，回答 4 个问题：
#   ① 三个任务各是哪种范式赢？和你跑之前的 expectation 一致吗？不一致的地方原因是什么？
#   ② T2 里 parallel_groups 分出了几层？如果真做并发，理论上能省多少墙钟时间？
#      （本作业没真并发，用"最长层数 × 单步耗时"估算即可，并说明估算的局限）
#   ③ T3 里 P&E 触发 replan 了吗？触发了几次？如果把 max_replans 设成 0 会怎样？
#      —— 把 max_replans=0 真跑一次，**这就是"机械执行过时计划"的现场**。
#   ④ 综合结论：你的客服 agent 该选哪种？给一段能直接讲给面试官听的话（≤150 字）。
#
#   findings.md 里的结论会摘进 interview-notes.md。
# ===========================================================================
