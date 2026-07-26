"""
L8 作业 · Part A：把玩具 loop 升级成生产级 ReAct executor

===========================================================================
你要做的事：把 quiz Q4 里那段 `while True` 改造成能上生产的东西。
核心是两件：**终止语义显式化** + **纯逻辑与副作用分离**。

分层（回扣 L6 的 context.py / agent.py 手法）：
    LoopGuard   纯逻辑，不碰网络 —— 只回答"该不该继续、为什么停"。这是 pytest 的靶子。
    run_react   接线层，碰 API 和工具 —— 只负责编排，判断全部委托给 LoopGuard。

⚠️ 本文件共有 **7 个 TODO**（TODO-1 ~ TODO-7）。
   做完请 `grep -n "TODO-" executor.py` 数一遍是不是全处理完了。
   （"多部分任务只做一半"是你出现 5 次的头号短板，这次用数数来治。）
===========================================================================
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum

from tools import BusinessError, FatalError, ToolError, TransientError

logger = logging.getLogger(__name__)


# ===========================================================================
# 1) 终止语义：显式枚举，而不是"返回一个字符串"
# ===========================================================================
class StopReason(str, Enum):
    """loop 为什么停下来。上层要靠它决定怎么兜底 —— 这也是 L13 trace 的字段来源。"""

    FINAL_ANSWER = "final_answer"        # 正常：模型不再点单
    HANDOFF = "handoff"                  # 正常：主动转人工
    MAX_STEPS = "max_steps"              # 被迫：步数没了
    NO_PROGRESS = "no_progress"          # 被迫：进展没了（原地转圈）
    BUDGET_EXCEEDED = "budget_exceeded"  # 被迫：钱没了
    TOOL_FATAL = "tool_fatal"            # 被迫：工具死了


@dataclass(frozen=True)
class ToolCallRecord:
    """一次工具调用的**指纹**。no-progress 检测靠比对它。

    注意 arguments 存的是模型给的**原始 JSON 字符串**，不是解析后的 dict ——
    dict 不可哈希，而且这里要的就是"字面上一模一样"。
    """

    name: str
    arguments: str


@dataclass
class RunResult:
    """一次 run 的完整结果。注意 final_answer 可能是 None（被迫结束时）。"""

    stop_reason: StopReason
    final_answer: str | None = None
    steps: int = 0
    total_prompt_tokens: int = 0
    elapsed_seconds: float = 0.0
    trace: list[dict] = field(default_factory=list)


# ===========================================================================
# 2) LoopGuard —— 纯逻辑，pytest 的主要靶子
# ===========================================================================
class LoopGuard:
    """只回答一个问题：**现在该不该停、为什么停。**

    它只负责三种"被迫结束"：MAX_STEPS / NO_PROGRESS / BUDGET_EXCEEDED。
    另外三种（FINAL_ANSWER / HANDOFF / TOOL_FATAL）由接线层判定 —— 因为它们
    要看模型返回和工具异常，不是"计数"能得出的。

    ⚠️ 本类不允许 import openai、不允许发网络请求。它必须能被纯单测覆盖。
    """

    def __init__(
        self,
        *,
        max_steps: int = 8,
        no_progress_threshold: int = 3,
        max_prompt_tokens: int = 60_000,
    ) -> None:
        """
        no_progress_threshold: 连续多少轮"工具调用指纹完全相同"算原地转圈。
                               注意是**连续**，不是累计。

        TODO-1: 存好三个阈值，并初始化你需要的内部状态。
                提示：你至少需要 ① 已走步数 ② 累计 prompt_tokens
                ③ 历史指纹列表（用来判断"连续 N 轮相同"）。
                ——三样，写完数一遍。
        """
        self.max_steps = max_steps
        self.no_progress_threshold = no_progress_threshold
        self.max_prompt_tokens = max_prompt_tokens
        self._steps = 0
        self._total_prompt_tokens = 0
        self._history_fingerprints: list[list[ToolCallRecord]] = []

    def record_step(self, tool_calls: list[ToolCallRecord], prompt_tokens: int) -> None:
        """记录刚刚走完的一步。

        参数 tool_calls 是这一轮模型点的所有工具（可能为空列表 = 没点单）。
        prompt_tokens 用 `response.usage.prompt_tokens` —— **真实值，不许估算**
        （L6 你自己指出过 len()//2 太幼稚，而且系统性偏低）。

        TODO-2: 更新步数、累计 token、追加本轮指纹。
                指纹怎么表示？想清楚"两轮算不算相同"：
                模型这轮点了 [query_order(A123), query_order(B456)]，
                下轮点了 [query_order(B456), query_order(A123)]，算不算相同？
                （没有标准答案，选一个并在注释里写清你的理由 —— 面试会问。）
        """
        #我认为两轮的工具调用顺序不同，应该算作不同的指纹，因为顺序可能影响执行逻辑和结果。
        self._steps += 1
        self.total_prompt_tokens += prompt_tokens
        self._history_fingerprints.append(tool_calls)

    def should_stop(self) -> StopReason | None:
        """该停就返回停的原因，不该停返回 None。

        TODO-3: 实现三个判断。**注意检查顺序 —— 这是个设计决策，不是随便排的**：
                如果同一时刻既超了步数又超了预算，你希望 trace 里记哪个？
                想清楚再排，并在注释里写一句理由。
        """
        raise NotImplementedError("TODO-3")

    # --- 下面两个只读属性给接线层拼 RunResult 用，已给你 ---
    @property
    def steps(self) -> int:
        return self._steps

    @property
    def total_prompt_tokens(self) -> int:
        return self._total_prompt_tokens


# ===========================================================================
# 3) 接线层 —— 碰 API 和工具，判断全部委托出去
# ===========================================================================
def _normalize(msg) -> dict:
    """把 SDK 的 message 对象归一化成 dict。

    TODO-4: 一行搞定。回扣 L6 的结论 —— 混血 messages 列表（dict + SDK 对象）
            是你出现过的短板 2，在**入口**就归一化能根治。
            提示：`model_dump(exclude_none=True)`。
    """
    return msg.model_dump(exclude_none=True)


def _execute_tool(name: str, raw_arguments: str, tool_impls: dict) -> tuple[str, bool]:
    """执行一个工具，返回 (给模型看的结果字符串, 是否致命)。

    这是 Q5 三类错误的落地点：
      - JSON 解析失败 / BusinessError → 包成 error JSON 回传，模型有机会自愈，fatal=False
      - FatalError                    → fatal=True，接线层要据此终止 loop
      - TransientError                → 本节按 fatal 处理，但留 TODO(L13) 标记

    ⚠️ 硬约束（你 quiz Q4 自己指出的）：**每个 tool_call_id 必须有且仅有一条对应回复。**
       所以本函数**任何路径都必须返回一个字符串**，绝不能让异常逃出去。

    TODO-5: 实现它。这里有 **4 条路径**要覆盖：
            ① json.loads 失败 ② BusinessError ③ FatalError/TransientError ④ 正常执行。
            另外还有一条你可能想不到的：**工具名不存在**（模型幻觉出一个工具名）。
            —— 一共 5 条，写完数一遍。
    """
    def err(message: str, *, fatal: bool = False, **extra) -> tuple[str, bool]:
        return json.dumps({"error": message, **extra}, ensure_ascii=False), fatal

    if name not in tool_impls:
        return err(f"未知工具 '{name}'", available_tools=sorted(tool_impls))

    try: 
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError as e:
        return err(f"参数不是合法 JSON: {e}", received=raw_arguments[:200])

    if not isinstance(arguments, dict):
        return err(f"参数必须是 JSON 对象（dict），但收到 {type(arguments).__name__}")

    try:
        result = tool_impls[name](**arguments)
    except (BusinessError, TypeError) as e:
        return err(str(e))
    except FatalError as e:
        logger.error("tool_fatal name=%s error=%s", name, str(e))
        return err("服务暂时不可用", fatal=True)
    except TransientError as e:
        # TODO(L13): 重试
        logger.warning("tool_transient name=%s error=%s", name, e)
        return err("服务暂时不可用，请稍后再试", fatal=True)
    except Exception as e:
        logger.exception("tool_unexpected name=%s error=%s", name, e)
        return err("工具执行出现未预期错误", fatal=True)

    if not isinstance(result, str):
        result = json.dumps(result, ensure_ascii=False, default=str)
    return result, False



    #检查工具名是否存在
    # if name not in tool_impls:
    #     error_result = {"error": f"Tool '{name}' not found. Choose tools from {list(tool_impls.keys())}."}
    #     return (json.dumps(error_result, ensure_ascii=False), False)
    # #尝试解析 JSON 参数
    # try:
    #     arguments = json.loads(raw_arguments)
    # except json.JSONDecodeError as e:
    #     error_result = {"error": f"JSON decode error: {str(e)}"}
    #     return (json.dumps(error_result, ensure_ascii=False), False)
    # #尝试执行工具
    # try: 
    #     result = str(tool_impls[name](**arguments))
    #     return (json.dumps(result, ensure_ascii=False), False)
    # except BusinessError as e:
    #     error_result = {"error": str(e)}
    #     return (json.dumps(error_result, ensure_ascii=False), False)
    # except FatalError as e:
    #     error_result = {"error": str(e)}
    #     return (json.dumps(error_result, ensure_ascii=False), True)
    # except TransientError as e:
    #     error_result = {"error": str(e)}
    #     return (json.dumps(error_result, ensure_ascii=False), True)

def run_react(
    user_question: str,
    *,
    client,
    guard: LoopGuard,
    tools: list[dict],
    tool_impls: dict,
    system_prompt: str,
    model: str = "deepseek-v4-flash",
) -> RunResult:
    """生产级 ReAct executor。

    注意签名：client 和 guard 都是**注入进来的**，不是函数内部 new 的。
    这样测试时能塞假 client、塞小阈值的 guard（回扣 L6 的依赖注入）。

    TODO-6: 实现主循环。骨架逻辑如下，你把它写出来：
        1. 初始化 messages（system + user）、计时
        2. 循环：
           a. 调 API（带 tools）
           b. 取 msg 和 response.usage.prompt_tokens
           c. 把本轮指纹交给 guard.record_step(...)
           d. **没有 tool_calls** → 拿到最终答案，收工
              ⚠️ msg.content 可能是 None（你 L6 debug 路由时撞过）—— 兜底！
                 这是你出现 5 次的老毛病，这次别再犯。
           e. 有 tool_calls → _normalize(msg) 后 append，逐个执行工具
              任一工具 fatal → 立刻收工，stop_reason=TOOL_FATAL
              （但仍要把 error 结果 append 成 tool 消息，保持消息序列合法）
           f. 问 guard.should_stop()，非 None 就收工
        3. 每轮写一行结构化日志（见下面 _log_step）
        4. 组装 RunResult 返回 —— **每条退出路径都要 return**

    ⚠️ 门禁条件 3：全程用 logger，**一个 print 都不许有**。
    """
    raise NotImplementedError("TODO-6")


def _log_step(*, step: int, tool_calls: list[ToolCallRecord], prompt_tokens: int, elapsed: float) -> None:
    """每轮一行结构化日志（v3「可靠性最小集」要求）。

    TODO-7: 用 logger 输出一行 **JSON**，至少含：
            step / tool_names / prompt_tokens / elapsed_ms。
            为什么要 JSON 而不是人话？—— 因为日志是给机器采的，L13 要拿它算
            P95 延迟、token 成本、工具调用分布。人话日志采不了。
    """
    raise NotImplementedError("TODO-7")


# ===========================================================================
# 4) 手动跑一把（写完 TODO-1~7 后用这个验证）
# ===========================================================================
if __name__ == "__main__":
    import os

    from openai import OpenAI

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    SYSTEM_PROMPT = (
        "你是电商客服助手。需要订单信息时必须调用工具查询，绝不编造。"
        "判断是否延迟、赔付多少，必须以 check_delay 的返回为准，不要自己算。"
    )

    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )

    from tools import TOOL_IMPLS, TOOLS

    result = run_react(
        "我的订单 A123 到哪了？",
        client=client,
        guard=LoopGuard(max_steps=8, no_progress_threshold=3, max_prompt_tokens=60_000),
        tools=TOOLS,
        tool_impls=TOOL_IMPLS,
        system_prompt=SYSTEM_PROMPT,
    )
    logger.info("stop_reason=%s steps=%d tokens=%d", result.stop_reason, result.steps, result.total_prompt_tokens)
    logger.info("answer=%s", result.final_answer)
