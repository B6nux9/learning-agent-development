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
from pydantic import BaseModel
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
    raw_notes: list[str]


# TODO(R2-1): 定义 ResearcherOutputState —— researcher 子图的"出墙滤网":
#   只放允许过墙的两个字段:compressed_research(str)和 raw_notes(list[str],默认空列表)。
#   源码用 BaseModel 定义它(和 ResearcherState 的 TypedDict 不同)——照做。
#   想清楚再写:为什么 researcher_messages 不在里面?这个类删掉一个字段意味着什么?
class ResearcherOutputState(BaseModel):
    compressed_research: str
    raw_notes: list[str] = []