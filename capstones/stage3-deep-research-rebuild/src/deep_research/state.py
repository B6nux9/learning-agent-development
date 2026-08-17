"""状态与协议定义 —— 只放"数据的形状",不放任何可执行逻辑(见 DESIGN.md 一)。

本文件按课程进度分区生长:
- R1: ResearchComplete(协议工具)+ ResearcherState
- R2: ResearcherOutputState(子图出口防火墙)
- R3: ConductResearch + override_reducer + SupervisorState
- R4: AgentState / AgentInputState + ClarifyWithUser / ResearchQuestion
"""

import operator
from typing import Annotated

from langchain_core.messages import MessageLikeRepresentation
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

###################
# 协议类("工具可以只是协议,不必可执行" —— DESIGN.md 决策 2)
###################

# TODO(R1-1): 定义 ResearchComplete —— 一个纯协议工具:
#   继承 BaseModel,不需要任何字段;docstring 写清用途
#   (researcher 用它宣告"这个子课题我研究完了";它永远不会被执行,
#    researcher_tools 只认它的名字就路由去压缩)。
#   注意:这个 docstring 会被 bind_tools 转成模型看到的工具描述——
#   它是写给模型读的说明书,不是写给人的注释。
class ResearchComplete(BaseModel):
    """Call this tool to indicate that the research is complete."""


# TODO(R3-2): 定义 ConductResearch —— supervisor 的"派活协议工具":
#   继承 BaseModel,含一个字段 research_topic: str,用 pydantic Field 加 description。
#   和 ResearchComplete 一样永远不会被执行——supervisor_tools 按名字拦截它,
#   把 research_topic 转手塞给 researcher_subgraph.ainvoke。
#   注意:Field 的 description 是写给模型看的"任务书填写要求"——源码要求
#   "单一课题 + 至少一段话的高细节描述"。想想为什么要在这里管模型:
#   派活单写得太粗,researcher 拿到的 research_topic 就没法干活。
#   (源码 state.py:15-19,description 原文照抄即可)
class ConductResearch(BaseModel):
    """Call this tool to conduct research on a specific topic."""
    research_topic: Annotated[str, Field(description="A single research topic, described in at least one paragraph of high detail.")]


###################
# Reducer 定义(R3:同一个字段既要能追加、也要能整体重置)
###################

# TODO(R3-1): 定义 override_reducer(current_value, new_value) —— 双语义 reducer:
#   - new_value 是 dict 且 .get("type") == "override" → 返回 new_value.get("value", new_value)
#     (整体替换,丢弃旧值)
#   - 否则 → operator.add(current_value, new_value)(普通追加,和 R1 的 operator.add 同款)
#   回忆 R1 quiz:add reducer 下"写 0 等于没写"——没有任何 update 值能把字段清空。
#   override_reducer 就是官方解法:在数据通道里内嵌一条控制协议。
#   (R4 的 write_research_brief 会用 {"type": "override", "value": [...]} 重置 supervisor_messages)
def override_reducer(current_value, new_value):
    if isinstance(new_value, dict) and new_value.get("type") == "override":
        return new_value.get("value", new_value)
    else:
        return operator.add(current_value, new_value)


###################
# State 定义
###################

# TODO(R1-2): 定义 ResearcherState(TypedDict)—— researcher 子图的运行时状态,5 个字段:
#   - researcher_messages: 消息列表。researcher 和 researcher_tools 轮流往里写,
#     必须"追加合并"而不是整体覆盖(想想:用哪种 Annotated 写法能让 LangGraph 帮你合并?)
#   - tool_call_iterations: int —— ReAct 循环预算计数器
#   - research_topic: str —— supervisor 派下来的任务书(R1 里由测试直接注入)
#   - compressed_research: str —— R2 压缩产物,先占位
#   - raw_notes: list[str] —— R2 用,先普通声明即可(R3 会讨论要不要换 override_reducer)
class ResearcherState(TypedDict):
    researcher_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    tool_call_iterations: int
    research_topic: str
    compressed_research: str
    raw_notes: Annotated[list[str], override_reducer]  # R3 升级:普通 list → override_reducer(源码同款)


# TODO(R2-1): 定义 ResearcherOutputState —— researcher 子图的"出墙滤网":
#   只放允许过墙的两个字段:compressed_research(str)和 raw_notes(list[str],默认空列表)。
#   源码用 BaseModel 定义它(和 ResearcherState 的 TypedDict 不同)——照做。
#   想清楚再写:为什么 researcher_messages 不在里面?这个类删掉一个字段意味着什么?
class ResearcherOutputState(BaseModel):
    compressed_research: str
    raw_notes: Annotated[list[str], override_reducer] = []  # R3 升级,同上


# TODO(R3-3): 定义 SupervisorState(TypedDict)—— supervisor 子图的运行时状态,5 个字段:
#   - supervisor_messages: 消息列表,挂 override_reducer(不是 operator.add——
#     想想谁需要"重置"这个字段?提示:R4 主图,每次新研究要清场)
#   - research_brief: str —— 研究任务书(R4 由主图写入;R3 测试直接注入)
#   - notes: list[str],挂 override_reducer —— 研究成果汇总,supervisor 退出时
#     从 ToolMessage 里收割,过墙给 R4 的 final_report 用
#   - research_iterations: int —— supervisor 的循环预算计数器(对应 researcher 的
#     tool_call_iterations,但预算语义有个关键差别,Group C 见)
#   - raw_notes: list[str],挂 override_reducer —— 所有 researcher 的原始笔记聚合
class SupervisorState(TypedDict):
    supervisor_messages: Annotated[list[MessageLikeRepresentation], override_reducer]
    research_brief: str
    notes: Annotated[list[str], override_reducer]
    research_iterations: int
    raw_notes: Annotated[list[str], override_reducer]