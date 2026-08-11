"""三层图本体(DESIGN.md 二)。本文件按课程进度生长:

- R1: researcher 子图 —— researcher ⇄ researcher_tools 的 ReAct 循环 + 子图编译
- R2: compress_research 真实现 + output schema 防火墙
- R3: supervisor 子图(supervisor ⇄ supervisor_tools,gather fan-out)
- R4: 主图(clarify / brief / final_report)+ 端到端
"""

import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from deep_research.configuration import Configuration
from deep_research.prompts import research_system_prompt
from deep_research.state import ResearcherState
from deep_research.utils import get_all_tools, get_today_str

# 可配置模型:此处不指定具体模型,真正的 model/max_tokens 在每次调用时
# 经 .with_config({...}) 注入(源码同款写法;测试则直接替换整个对象)。
configurable_model = init_chat_model(configurable_fields=("model", "max_tokens", "api_key"))


###################
# Researcher 子图(R1 主战场)
###################

async def researcher(state: ResearcherState, config: RunnableConfig) -> Command[Literal["researcher_tools"]]:
    """ReAct 循环的"思考"半步:模型看到当前对话,决定调什么工具(或开始写总结)。

    行为契约:
    - 模型 = configurable_model 依次绑定工具、加重试、注入模型配置
    - 输入 = [SystemMessage(research_system_prompt,填好 date 和 mcp_prompt="")] + 历史消息
    - 返回 Command:固定去 researcher_tools;update 里追加模型回复,
      并把 tool_call_iterations 计数 +1
    """
    configurable = Configuration.from_runnable_config(config)
    researcher_messages = state.get("researcher_messages", [])

    tools = await get_all_tools(config)
    if len(tools) == 0:
        raise ValueError("No tools found to conduct research: 请检查 utils.get_all_tools。")

    # TODO(R1-4): 组装研究模型 —— 把 configurable_model 依次:绑定 tools、
    #   加重试(次数用 configurable.max_structured_output_retries)、
    #   注入模型配置(至少含 model / max_tokens,值从 configurable 取)。
    research_model_config = {
        "model": configurable.research_model,
        "max_tokens": configurable.research_model_max_tokens,
    }
    research_model = (
        configurable_model
        .bind_tools(tools)
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(research_model_config)
    )


    # TODO(R1-5): 组装输入消息并 ainvoke,然后按 docstring 契约返回 Command。
    #   (回读契约:update 里应该有几个 key?各是什么?)
    input_messages = [SystemMessage(research_system_prompt.format(date=get_today_str(), mcp_prompt=""))] + researcher_messages
    response = await research_model.ainvoke(input_messages)
    return Command(goto="researcher_tools", update={
        "researcher_messages": [response],
        "tool_call_iterations": state.get("tool_call_iterations", 0) + 1
    })


async def execute_tool_safely(tool, args, config):
    """安全执行单个工具:任何异常都不许炸掉整个图。

    行为契约:成功 → 返回工具结果;失败 → 返回字符串
    "Error executing tool: <异常信息>"。错误也作为 observation 喂回模型,
    让模型自己决定重试还是换招(而不是让一次工具故障终结整个研究)。
    """
    # TODO(R1-6): try/except 包住 tool.ainvoke(args, config)
    try:
        result = await tool.ainvoke(args, config)
        return result
    except Exception as e:
        return f"Error executing tool: {str(e)}"


async def researcher_tools(state: ResearcherState, config: RunnableConfig) -> Command[Literal["researcher", "compress_research"]]:
    """ReAct 循环的"行动"半步 + 循环路由器。

    路由规则(就是你 R0 推导的三个退出条件,在这里逐条落地):
    1. 早退:上一条 AI 消息一个工具都没调(模型开始写总结文字)
       → 什么都不执行,直接去 compress_research
    2. 并发执行本轮所有 tool_calls,结果包装成 ToolMessage 列表
    3. 晚退:预算耗尽(tool_call_iterations ≥ max_react_tool_calls)
       或本轮调用了 ResearchComplete → 带着 ToolMessage 去 compress_research
    4. 都不满足 → 带着 ToolMessage 回 researcher 继续循环
    """
    configurable = Configuration.from_runnable_config(config)
    researcher_messages = state.get("researcher_messages", [])
    most_recent_message = researcher_messages[-1]

    # TODO(R1-7): 早退检查(规则 1)。
    if not most_recent_message.tool_calls:
        return Command(goto="compress_research", update={})

    # TODO(R1-8): 并发执行(规则 2):
    #   建 {工具名: 工具} 映射 → 对每个 tool_call 发一个 execute_tool_safely
    #   → asyncio.gather 一次收齐 → zip 对齐组装 ToolMessage
    #   (ToolMessage 三件套:content / name / tool_call_id ——
    #    tool_call_id 为什么必须原样带回?想不通就故意填错跑一次测试看看)
    tools = await get_all_tools(config)
    tools_by_name = {
        tool.name if hasattr(tool, "name") else tool.get("name", "web_search"): tool
        for tool in tools
    }

    tool_calls = most_recent_message.tool_calls
    tool_execution_tasks = [
        execute_tool_safely(tools_by_name[tool_call["name"]], tool_call["args"], config)
        for tool_call in tool_calls
    ]
    observations = await asyncio.gather(*tool_execution_tasks)

    tool_outputs = [
        ToolMessage(
            content=observation,
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        )
        for observation, tool_call in zip(observations, tool_calls)
    ]

    # TODO(R1-9): 晚退检查 + 路由(规则 3、4)。
    #   注意 ResearchComplete 在这里"被响应"的方式:没有任何代码执行,
    #   只是按名字识别 → 改变路由。这就是"协议工具"的另一半。
    if state.get("tool_call_iterations", 0) >= configurable.max_react_tool_calls or any(call["name"] == "ResearchComplete" for call in tool_calls):
        return Command(goto="compress_research", update={"researcher_messages": tool_outputs})
    else:
        return Command(goto="researcher", update={"researcher_messages": tool_outputs})


async def compress_research(state: ResearcherState, config: RunnableConfig):
    """R2 的主角:把整个 ReAct 对话压缩成过墙提炼稿。R1 先用占位实现保住图形状。"""
    return {
        "compressed_research": "[R2 填充] compression not implemented yet",
        "raw_notes": [],
    }


# TODO(R1-10): 组装并编译 researcher 子图,赋值给 researcher_subgraph:
#   StateGraph(ResearcherState) → 加三个节点 → START 连到 researcher
#   → compress_research 连到 END → .compile()
#   思考:researcher ⇄ researcher_tools 之间为什么一条 add_edge 都不用写?(quiz 会考)
researcher_subgraph = StateGraph(ResearcherState) \
    .add_node("researcher", researcher) \
    .add_node("researcher_tools", researcher_tools) \
    .add_node("compress_research", compress_research) \
    .add_edge(START, "researcher") \
    .add_edge("compress_research", END) \
    .compile()
