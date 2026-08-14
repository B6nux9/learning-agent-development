"""可执行的东西:搜索工具、think_tool、辅助函数(见 DESIGN.md 一)。

- R1: fake_search(教练给现成,拔网线能跑)+ think_tool(你写)+ get_all_tools(给现成)
- R2: 接真 Tavily、token 韧性工具(remove_up_to_last_ai_message 等)
"""

from datetime import datetime

from langchain_core.messages import AIMessage, MessageLikeRepresentation
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from deep_research.configuration import Configuration
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
    """R2 版:协议 + 反思 + 按配置选搜索。

    源码在这里还会按配置接入 Tavily/OpenAI/Anthropic 原生搜索和 MCP 工具(R2/扩展⑤)。
    注意 ResearchComplete 的接入方式:tool(BaseModel) 把协议类转成"可绑定的工具",
    但它没有可执行体——谁负责在它被调用时做出反应?(R1-9 里你会回答这个问题)
    """
    configurable = Configuration.from_runnable_config(config)
    tools = [tool(ResearchComplete), think_tool]
    # TODO(R2-7): 按 configurable.search_api 追加搜索工具后返回 tools:
    #   "tavily" → TavilySearch(max_results=3)(langchain-tavily 现成工具,key 走环境变量 TAVILY_API_KEY)
    #   其余取值 → fake_search(默认必须离线——9 条既有测试一个 configurable 都没配)
    if configurable.search_api == "tavily":
        tools.append(TavilySearch(max_results=3))
    else:
        tools.append(fake_search)
    return tools


########## Token 韧性 ##########

# 教练给现成:跨 provider 的超限报错嗅探(各家连报错格式都不统一,只能模式匹配)
def is_token_limit_exceeded(exception: Exception, model_name: str = None) -> bool:
    """Determine if an exception indicates a token/context limit was exceeded.

    Args:
        exception: The exception to analyze
        model_name: Optional model name to optimize provider detection

    Returns:
        True if the exception indicates a token limit was exceeded, False otherwise
    """
    error_str = str(exception).lower()

    # Step 1: Determine provider from model name if available
    provider = None
    if model_name:
        model_str = str(model_name).lower()
        if model_str.startswith('openai:'):
            provider = 'openai'
        elif model_str.startswith('anthropic:'):
            provider = 'anthropic'
        elif model_str.startswith('gemini:') or model_str.startswith('google:'):
            provider = 'gemini'

    # Step 2: Check provider-specific token limit patterns
    if provider == 'openai':
        return _check_openai_token_limit(exception, error_str)
    elif provider == 'anthropic':
        return _check_anthropic_token_limit(exception, error_str)
    elif provider == 'gemini':
        return _check_gemini_token_limit(exception, error_str)

    # Step 3: If provider unknown, check all providers
    return (
        _check_openai_token_limit(exception, error_str) or
        _check_anthropic_token_limit(exception, error_str) or
        _check_gemini_token_limit(exception, error_str)
    )

def _check_openai_token_limit(exception: Exception, error_str: str) -> bool:
    """Check if exception indicates OpenAI token limit exceeded."""
    # Analyze exception metadata
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, '__module__', '')

    # Check if this is an OpenAI exception
    is_openai_exception = (
        'openai' in exception_type.lower() or
        'openai' in module_name.lower()
    )

    # Check for typical OpenAI token limit error types
    is_request_error = class_name in ['BadRequestError', 'InvalidRequestError']

    if is_openai_exception and is_request_error:
        # Look for token-related keywords in error message
        token_keywords = ['token', 'context', 'length', 'maximum context', 'reduce']
        if any(keyword in error_str for keyword in token_keywords):
            return True

    # Check for specific OpenAI error codes
    if hasattr(exception, 'code') and hasattr(exception, 'type'):
        error_code = getattr(exception, 'code', '')
        error_type = getattr(exception, 'type', '')

        if (error_code == 'context_length_exceeded' or
            error_type == 'invalid_request_error'):
            return True

    return False

def _check_anthropic_token_limit(exception: Exception, error_str: str) -> bool:
    """Check if exception indicates Anthropic token limit exceeded."""
    # Analyze exception metadata
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, '__module__', '')

    # Check if this is an Anthropic exception
    is_anthropic_exception = (
        'anthropic' in exception_type.lower() or
        'anthropic' in module_name.lower()
    )

    # Check for Anthropic-specific error patterns
    is_bad_request = class_name == 'BadRequestError'

    if is_anthropic_exception and is_bad_request:
        # Anthropic uses specific error messages for token limits
        if 'prompt is too long' in error_str:
            return True

    return False

def _check_gemini_token_limit(exception: Exception, error_str: str) -> bool:
    """Check if exception indicates Google/Gemini token limit exceeded."""
    # Analyze exception metadata
    exception_type = str(type(exception))
    class_name = exception.__class__.__name__
    module_name = getattr(exception.__class__, '__module__', '')

    # Check if this is a Google/Gemini exception
    is_google_exception = (
        'google' in exception_type.lower() or
        'google' in module_name.lower()
    )

    # Check for Google-specific resource exhaustion errors
    is_resource_exhausted = class_name in [
        'ResourceExhausted',
        'GoogleGenerativeAIFetchError'
    ]

    if is_google_exception and is_resource_exhausted:
        return True

    # Check for specific Google API resource exhaustion patterns
    if 'google.api_core.exceptions.resourceexhausted' in exception_type.lower():
        return True

    return False


def remove_up_to_last_ai_message(messages: list[MessageLikeRepresentation]) -> list[MessageLikeRepresentation]:
    """token 超限自救:丢新保旧的截断。

    行为契约:从后往前找到最后一条 AIMessage,返回它之前的所有消息
    (最后一条 AIMessage 本人及其之后的消息全部丢弃);
    整个列表里没有 AIMessage 时,原样返回。
    不许修改传入的列表(纯函数——想想 iconcat 那课)。
    """
    # TODO(R2-6): 倒序扫描实现。边界自查:返回值"含不含"那条 AIMessage?
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            return messages[:i]  # 截断到最后一条 AIMessage 之前的所有消息
    return messages  # 没有 AIMessage,原样返回
