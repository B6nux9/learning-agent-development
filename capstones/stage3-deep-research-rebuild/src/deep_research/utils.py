"""可执行的东西:搜索工具、think_tool、辅助函数(见 DESIGN.md 一)。

- R1: fake_search(教练给现成,拔网线能跑)+ think_tool(你写)+ get_all_tools(给现成)
- R2: 接真 Tavily、token 韧性工具(remove_up_to_last_ai_message 等)
"""

from datetime import datetime

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from deep_research.state import ResearchComplete


def get_today_str() -> str:
    """今天的日期,填进 system prompt 让模型知道'现在'是什么时候。"""
    return datetime.now().strftime("%a %b %d, %Y")


##########################
# 搜索工具(R1 用假的,R2 换真的)
##########################

_FAKE_CORPUS = {
    "default": (
        "1. LangGraph subgraphs let you compose graphs as nodes of a parent graph. "
        "A subgraph can declare its own state schema and an output schema that "
        "filters what flows back to the parent.\n"
        "2. The Command primitive lets a node return both a routing decision (goto) "
        "and a state update in one object, replacing conditional edges.\n"
        "3. ReAct agents alternate between reasoning steps and tool calls until a "
        "stop condition is met (budget, explicit completion signal, or no tool call)."
    ),
}


@tool(description="Search the web for information on the given queries. Returns search results as text.")
def fake_search(queries: list[str]) -> str:
    """离线假搜索:不管查什么都返回固定语料(按查询词回显,便于断言)。

    R1 的意义:让 ReAct 循环先跑起来,把"图的机制"和"搜索的质量"解耦——
    拔网线也能跑绿。R2 用相同签名换成真 Tavily,图代码一行不用改。
    """
    blocks = []
    for q in queries:
        blocks.append(f"=== Results for: {q} ===\n{_FAKE_CORPUS['default']}")
    return "\n\n".join(blocks)


##########################
# 反思工具
##########################

@tool(description="Strategic reflection tool for research planning")
def think_tool(reflection: str) -> str:
    """把 ReAct 的 Reasoning 变成一次可见的 tool call(DESIGN.md 决策 4)。

    模型在两次搜索之间调用它,把"我找到了什么/还缺什么/要不要继续"写进
    reflection 参数——反思因此进入消息历史,可审计、可回放。

    Args:
        reflection: 模型对研究进展、缺口、下一步的详细反思

    Returns:
        一句确认文本(把 reflection 原样带上),作为 ToolMessage 回到对话里
    """
    # TODO(R1-3): 一行实现。想清楚再写:这个工具"执行"了什么?
    #   如果答案是"什么都没执行",那它的价值在哪?(quiz 会考)
    return f"Reflection received: {reflection}"


##########################
# 工具箱组装
##########################

async def get_all_tools(config: RunnableConfig) -> list:
    """R1 版工具箱:协议工具 + think_tool + fake_search。

    源码在这里还会按配置接入 Tavily/OpenAI/Anthropic 原生搜索和 MCP 工具(R2/扩展⑤)。
    注意 ResearchComplete 的接入方式:tool(BaseModel) 把协议类转成"可绑定的工具",
    但它没有可执行体——谁负责在它被调用时做出反应?(R1-9 里你会回答这个问题)
    """
    return [tool(ResearchComplete), think_tool, fake_search]
