"""
L8 作业 · Part B：Plan-and-Execute + 偏差触发 Replan

===========================================================================
这一部分同时补上 **L6 欠的 Part B（结构化输出）** —— 让模型用 json_schema
吐出一个"计划"对象，而不是一段要你正则解析的自然语言。

三个核心件：
    PLAN_SCHEMA       结构化输出的契约（L6 缺口 2 的动手部分）
    parallel_groups   纯逻辑：从 depends_on 算出"哪几步能并行" —— pytest 靶子
    run_plan_execute  接线：执行计划，偏差触发 replan（有上限）

⚠️ 本文件共有 **5 个 TODO**（TODO-1 ~ TODO-5）。做完 `grep -n "TODO-" planner.py` 数一遍。
===========================================================================
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from executor import RunResult, StopReason, ToolCallRecord, _execute_tool

logger = logging.getLogger(__name__)


# ===========================================================================
# 1) 结构化输出契约
# ===========================================================================
PLAN_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "execution_plan",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "steps": {
                    "type": "array",
                    "description": "按依赖关系排好的执行步骤",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string", "description": "步骤编号，如 s1"},
                            "tool": {"type": "string", "description": "要调用的工具名"},
                            # TODO-1: 补三个字段。
                            #   ① arguments —— 想清楚它该是什么类型。
                            #      难点：不同工具参数结构不同，JSON Schema 怎么表达"任意对象"？
                            #      strict 模式下很多端点不接受自由 object —— 这里有个真实取舍，
                            #      你可以选"存成 JSON 字符串"绕开。选哪个都行，**在注释里写清代价**。
                            #   ② depends_on —— 依赖哪些步骤 id（数组）。parallel_groups 全靠它。
                            #   ③ purpose —— 这步干什么（一句话）。给人看的，审批时要读。
                            # ——三个，写完数一遍。
                        },
                        "required": ["id", "tool"],  # TODO-1 续：把你新加的字段补进 required
                        "additionalProperties": False,
                    },
                },
                "requires_human_approval": {
                    "type": "boolean",
                    "description": "本计划是否含不可逆的写操作，需要人工批准后才能执行",
                },
                # TODO-1 续：再想想还缺什么。提示：如果模型判断"这个任务根本不该提前规划"，
                #            它怎么告诉你？（回扣讲义 §4：不是所有任务都值得规划）
            },
            "required": ["steps", "requires_human_approval"],
            "additionalProperties": False,
        },
    },
}


@dataclass
class PlanStep:
    id: str
    tool: str
    arguments: dict
    depends_on: list[str] = field(default_factory=list)
    purpose: str = ""


@dataclass
class Plan:
    steps: list[PlanStep]
    requires_human_approval: bool = False


# ===========================================================================
# 2) 纯逻辑：并行分组（pytest 靶子）
# ===========================================================================
def parallel_groups(plan: Plan) -> list[list[str]]:
    """把计划按依赖关系分层：同一层内的步骤**互不依赖，可以并发执行**。

    例：s1 无依赖；s2、s3 都依赖 s1；s4 依赖 s2 和 s3
        → [["s1"], ["s2", "s3"], ["s4"]]

    这个函数就是讲义 §Q2 补充点的代码化：
    **"Plan-and-Execute 可并行"是可能性不是必然 —— 取决于 depends_on 的形状。**
    如果返回的每层都只有 1 个元素，说明这个计划**完全串行**，
    那你花掉的那轮规划延迟就白付了。

    ⚠️ 别忘了处理**环**（模型是可能吐出 s1→s2→s1 这种的）。
       撞到环怎么办？抛异常还是返回空？想清楚，接线层要据此决定 stop_reason。

    TODO-2: 实现拓扑分层。这里有 **3 件事**要做：
            ① 分层算法本身
            ② 环检测
            ③ 依赖了一个不存在的 step id 怎么办（模型幻觉）
            ——三件，写完数一遍。
    """
    raise NotImplementedError("TODO-2")


def is_plan_stale(step: PlanStep, observation: str) -> bool:
    """判断"计划过时了"—— 触发 replan 的条件。

    讲义 §3 说 Plan-and-Execute 最惨的失败模式是**机械执行一个已知错误的计划**。
    这个函数就是防它的闸门。

    TODO-3: 想清楚什么信号算"计划过时"，至少覆盖 **2 类**：
            ① 这步的工具返回了 error（业务错误 → 后续步骤的前提可能塌了）
            ② 观察结果与计划假设矛盾。
               具体到本作业：计划里写了"给 A123 申请赔付"，但 check_delay
               返回 delayed=false —— 计划是在不知道这个事实时定的。
            怎么在不写死业务规则的前提下判断②？这是个开放题，
            **写下你的方案和它的局限**（面试会追问"你怎么知道计划过时了"）。
    """
    raise NotImplementedError("TODO-3")


# ===========================================================================
# 3) 接线层
# ===========================================================================
def make_plan(user_question: str, *, client, tools: list[dict], model: str = "deepseek-v4-pro",
              prior_observations: list[str] | None = None) -> Plan:
    """让模型产出一个结构化计划。

    ⚠️ 两个真实工程坑，你会撞上：
    1. **端点未必支持 json_schema**。DeepSeek 端点对 `response_format` 的支持程度要自己试。
       如果 400 了，降级方案是 `{"type": "json_object"}` + 把 schema 写进 prompt + **自己校验**。
       —— 这个降级过程本身就是生产常态，撞上了别慌，把过程记进 interview-notes。
    2. **规划用哪个模型？** 这里默认给了 `deepseek-v4-pro`（贵、慢、准），
       执行用 `deepseek-v4-flash`。为什么这么分？—— 回扣 L6 你学的"摘要器用 pro、
       主对话用 flash"。**规划错一次全盘皆输，执行错一步还能 replan。**

    TODO-4: 实现它。要点：
            ① prompt 里要把可用工具列出来（模型得知道能用什么才能规划）
            ② prior_observations 非空时，说明这是 **replan** —— 要把已知事实带进去，
               否则新计划会犯和旧计划一样的错
            ③ 解析返回的 JSON，组装成 Plan 对象；解析失败要有兜底
            ——三个要点，写完数一遍。
    """
    raise NotImplementedError("TODO-4")


def run_plan_execute(
    user_question: str,
    *,
    client,
    tools: list[dict],
    tool_impls: dict,
    max_replans: int = 2,
    auto_approve: bool = True,
    planner_model: str = "deepseek-v4-pro",
) -> RunResult:
    """Plan → Execute → 偏差触发 Replan。

    注意 `auto_approve`：真实客服系统里 requires_human_approval=True 的计划**必须**
    停下来等人批。这里默认 True 是为了能跑通对比实验，但你要在代码里
    留出那个分支 —— capstone 的客服域检查表第一条就是它。

    TODO-5: 实现它。骨架：
        1. make_plan → 拿到 plan
        2. requires_human_approval and not auto_approve → 返回 RunResult(stop_reason=HANDOFF)
        3. parallel_groups(plan) 分层（本作业**顺序执行每层即可，不必真并发**，
           但要把分层结果记进 trace —— Part C 的对比要用它说明"能并行几组"）
        4. 逐步执行，每步后 is_plan_stale(...) 检查
           → 过时且还有 replan 额度 → 带着已有观察重新 make_plan，回到 3
           → 过时但额度用完 → stop_reason=MAX_STEPS（或你自己定义的语义，说明理由）
        5. 全部执行完 → 把所有观察交给模型生成最终答复 → stop_reason=FINAL_ANSWER
        6. 组装 RunResult（steps / total_prompt_tokens 都要**真实累计**，
           Part C 靠它和 ReAct 比）

    ⚠️ 注意：规划那次 LLM 调用的 token **也要算进 total_prompt_tokens**。
       不算的话对比数据就是假的 —— 这是最容易自欺欺人的地方。
    """
    raise NotImplementedError("TODO-5")
