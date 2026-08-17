"""三层图本体(DESIGN.md 二)。本文件按课程进度生长:

- R1: researcher 子图 —— researcher ⇄ researcher_tools 的 ReAct 循环 + 子图编译
- R2: compress_research 真实现 + output schema 防火墙
- R3: supervisor 子图(supervisor ⇄ supervisor_tools,gather fan-out)
- R4: 主图(clarify / brief / final_report)+ 端到端
"""

import asyncio
from typing import Literal

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages import filter_messages
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command

from deep_research.configuration import Configuration
from deep_research.prompts import (
    research_system_prompt,
    compress_research_system_prompt,
    compress_research_simple_human_message,
)
from deep_research.state import (
    ConductResearch,
    ResearchComplete,
    ResearcherState,
    ResearcherOutputState,
    SupervisorState,
)
from deep_research.utils import (
    get_all_tools,
    get_notes_from_tool_calls,
    get_today_str,
    is_token_limit_exceeded,
    remove_up_to_last_ai_message,
    think_tool,
)

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
    """把整个 ReAct 对话压缩成过墙提炼稿(防火墙内侧最后一道工序)。

    行为契约(Group B 先写直线逻辑,失败重试是 Group C 的事):
    - 压缩模型 = configurable_model.with_config({...}) —— 注意用 compression_model /
      compression_model_max_tokens 两个字段,不是 research 那对(四模型分工)
    - 模式切换:researcher_messages 尾部追加 HumanMessage(compress_research_simple_human_message),
      system prompt 换成 compress_research_system_prompt(填 date)
    - 调用后返回 dict,恰好是防火墙放行的两个字段:
      compressed_research = str(response.content)
      raw_notes = ["\\n".join(所有 tool 和 ai 消息的 content)]
      (提取用 filter_messages(messages, include_types=["tool", "ai"]))
    """
    configurable = Configuration.from_runnable_config(config)
    researcher_messages = state.get("researcher_messages", [])

    # TODO(R2-3): 配置压缩模型 synthesizer_model —— configurable_model.with_config({...}),
    #   model / max_tokens 取 compression 那对字段。
    compression_model = (
        configurable_model
        .with_config({
            "model": configurable.compression_model,
            "max_tokens": configurable.compression_model_max_tokens
        })
    )


    # TODO(R2-5): 教练代写(2026-08-13,学生要求)——封版前需能逐行讲回来,quiz 出变式验证。
    # 模式切换:拼新列表而不是 append 原列表——state.get 拿到的就是状态里那个 list 对象,
    # 原地 append 会把这条 HumanMessage 污染进图状态(⚠️ 源码 538 行原地 append,就是那个坑)
    researcher_messages = researcher_messages + [HumanMessage(compress_research_simple_human_message)]

    synthesis_attempts = 0
    max_attempts = 3

    while synthesis_attempts < max_attempts:
        try:
            # messages 在循环内重组:截断重试后 researcher_messages 已变短,不能用旧的
            messages = [SystemMessage(compress_research_system_prompt.format(date=get_today_str()))] + researcher_messages
            response = await compression_model.ainvoke(messages)
            raw_notes = ["\n".join(
                [str(m.content) for m in filter_messages(researcher_messages, include_types=["tool", "ai"])]
            )]
            return {
                "compressed_research": str(response.content),
                "raw_notes": raw_notes
            }
        except Exception as e:
            synthesis_attempts += 1
            # 传实际在干活的模型:compression_model(⚠️ 源码这里传了 research_model——嗅探对象错位)
            if is_token_limit_exceeded(e, configurable.compression_model):
                # 丢新保旧剪一轮再试;其他错误不剪,盲重试赌运气
                researcher_messages = remove_up_to_last_ai_message(researcher_messages)
            continue

    # 兜底:压缩失败,原料照样过墙(防火墙第二字段 = 降级通道)
    raw_notes = ["\n".join(
        [str(m.content) for m in filter_messages(researcher_messages, include_types=["tool", "ai"])]
    )]
    return {
        "compressed_research": "Error synthesizing research report: Maximum retries exceeded",
        "raw_notes": raw_notes
    }

# TODO(R1-10): 组装并编译 researcher 子图,赋值给 researcher_subgraph:
#   StateGraph(ResearcherState) → 加三个节点 → START 连到 researcher
#   → compress_research 连到 END → .compile()
#   思考:researcher ⇄ researcher_tools 之间为什么一条 add_edge 都不用写?(quiz 会考)
# TODO(R2-2): 给 StateGraph 加上防火墙和配置声明两个参数:
#   output=ResearcherOutputState(过墙滤网:ainvoke 返回值只保留该 schema 里的字段)
#   config_schema=Configuration(向外声明"本图认哪些 configurable 字段")
#   记得补 import。改完先自己预测:test_r2 的防火墙测试断言返回值里有哪几个 key?
researcher_subgraph = StateGraph(ResearcherState, output_schema=ResearcherOutputState, context_schema=Configuration) \
    .add_node("researcher", researcher) \
    .add_node("researcher_tools", researcher_tools) \
    .add_node("compress_research", compress_research) \
    .add_edge(START, "researcher") \
    .add_edge("compress_research", END) \
    .compile()


###################
# Supervisor 子图(R3 主战场)
###################

async def supervisor(state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor_tools"]]:
    """supervisor ReAct 循环的"思考"半步:读派活对话,决定下一步派谁研究什么。

    researcher 节点的镜像,但注意三个差别(Group A 讲义):
    - 工具是写死的三件套协议 [ConductResearch, ResearchComplete, think_tool],
      不走 get_all_tools(supervisor 不亲自搜索,只派活/思考/收工)
    - 不在节点内拼 SystemMessage —— supervisor_messages 进节点时已经带着
      system prompt(R4 由 write_research_brief 用 override 信封整体写入;
      R3 测试手动 seed)。所以 ainvoke 的输入就是 supervisor_messages 本身。
    - 计数器叫 research_iterations,+1 的语义是"supervisor 又思考了一轮"
      (预算含义和 researcher 的 tool_call_iterations 的关键差别,Group C 见)

    行为契约:
    - 模型 = configurable_model 依次:绑定三件套、加重试
      (configurable.max_structured_output_retries)、注入模型配置
      (model / max_tokens,从 configurable 的 research_model 系列字段取)
    - 返回 Command:固定去 supervisor_tools;update 里追加模型回复,
      research_iterations 计数 +1
    """
    configurable = Configuration.from_runnable_config(config)
    supervisor_messages = state.get("supervisor_messages", [])

    # TODO(R3-4): 组装 supervisor 模型 —— 三件套协议工具 + 重试 + 模型配置。
    #   (R1-4 的镜像,但 tools 列表是写死的;源码把它命名为 lead_researcher_tools)
    supervisor_model_config = {
            "model": configurable.research_model,
            "max_tokens": configurable.research_model_max_tokens,
        }
    supervisor_model = (
        configurable_model
        .bind_tools([ConductResearch, ResearchComplete, think_tool])
        .with_retry(stop_after_attempt=configurable.max_structured_output_retries)
        .with_config(supervisor_model_config)
    )

    # TODO(R3-5): ainvoke 并按 docstring 契约返回 Command。
    #   回读契约:输入消息是什么?update 里有几个 key?计数器从哪读、怎么加?
    input_messages = supervisor_messages
    response = await supervisor_model.ainvoke(input_messages)
    return Command(goto="supervisor_tools", update={
        "supervisor_messages": [response],
        "research_iterations": state.get("research_iterations", 0) + 1
    })


async def supervisor_tools(state: SupervisorState, config: RunnableConfig) -> Command[Literal["supervisor", "__end__"]]:
    """supervisor ReAct 循环的"行动"半步 —— 但三类工具零真实执行,全按名字拦截转手。

    结构与 researcher_tools 镜像,两处关键反转(Group A 讲义):
    - **前置检查**:进门先查退出,查完才"执行"。researcher_tools 是后置
      (先执行后查预算)——因为这层一次"工具执行"= 整个 researcher 子图跑一遍,
      先查再跑省的是真金白银。
    - 退出时要**收割成果**:notes 从对话里的 ToolMessage 打包(researcher_tools
      退出只是路由,不带货)。

    行为契约:
    1. 前置退出(三个条件任一满足 → goto END,
       update = {"notes": get_notes_from_tool_calls(supervisor_messages),
                 "research_brief": state.get("research_brief", "")}):
       a. research_iterations > configurable.max_researcher_iterations(注意是 >,不是 ≥)
       b. 最新一条消息没有 tool_calls
       c. tool_calls 里出现 ResearchComplete
    2. think_tool 拦截:不执行任何函数,对每个 think_tool 调用直接内联造
       ToolMessage(content=f"Reflection recorded: {reflection}", name / tool_call_id 对齐)
    3. ConductResearch 转手 fan-out:每个调用变成一次
       researcher_subgraph.ainvoke({"researcher_messages": [HumanMessage(topic)],
       "research_topic": topic}, config),asyncio.gather 并发收齐;
       每个结果的 compressed_research 装进 ToolMessage 回给 supervisor
       (拿不到时用兜底文案 "Error synthesizing research report: Maximum retries exceeded");
       所有结果的 raw_notes 用 "\\n" 拼成一整条,塞进 update 的 raw_notes(装在单元素 list 里)
    4. 都处理完 → goto "supervisor",update 带上全部 ToolMessage(think 的和 research 的)

    (预算切片与超发教育、except 兜底 —— Group D 再加;本组先写直线逻辑,和 R2 一个节奏)
    """
    configurable = Configuration.from_runnable_config(config)
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = supervisor_messages[-1]

    # TODO(R3-6): 前置退出检查(契约 1)。三个条件各自算一个 bool,再一起判——
    #   源码就是这么写的,可读性 > 短路技巧。
    #   (想清楚 a 为什么用 > 而不是 ≥:supervisor 节点先 +1 后才到这里,
    #    iterations 此刻数的是"已经思考过几轮"——含本轮)
    condition_a = research_iterations > configurable.max_researcher_iterations
    condition_b = not most_recent_message.tool_calls
    condition_c = any(call["name"] == "ResearchComplete" for call in most_recent_message.tool_calls)
    if condition_a or condition_b or condition_c:
        notes = get_notes_from_tool_calls(supervisor_messages)
        research_brief = state.get("research_brief", "")
        return Command(goto="__end__", update={"notes": notes, "research_brief": research_brief})

    # TODO(R3-7): think_tool 拦截(契约 2)。
    #   从 most_recent_message.tool_calls 里按名字过滤,内联造 ToolMessage。
    #   reflection 文本在 tool_call["args"]["reflection"] 里。
    think_tool_messages = [
        ToolMessage(
            content=f"Reflection recorded: {tool_call['args']['reflection']}",
            name=tool_call["name"],
            tool_call_id=tool_call["id"]
        )
        for tool_call in most_recent_message.tool_calls
        if tool_call["name"] == "think_tool"
    ]

    # TODO(R3-8): ConductResearch 转手 fan-out(契约 3)+ 收尾路由(契约 4)。
    #   R1-8 你写过一遍 gather + zip 对齐,这里的新东西只有两个:
    #   ainvoke 的对象从"工具"换成了"整个子图";返回值是过墙后的 dict
    #   (只剩 compressed_research / raw_notes 两个 key——R2 防火墙在这一刻兑现)。
    conduct_research_calls = [
        tool_call for tool_call in most_recent_message.tool_calls
        if tool_call["name"] == "ConductResearch"
    ]
    # ↓ 教练二次代写(2026-08-17,学生确认)——债未清:封版前逐行讲回来 + quiz 变式必考。
    # TODO(R3-10): 预算切片 + 超发教育(改造下面的 fan-out,三步):
    #   a. conduct_research_calls 按 configurable.max_concurrent_research_units
    #      切成 allowed(前 N 张)和 overflow(第 N+1 张起)两摞
    #   b. fan-out 只跑 allowed 那摞
    #   c. overflow 每张单也必须造 ToolMessage 回礼(为什么一张都不能少?
    #      想想 provider 对 tool_calls 的应答规矩),content 用源码原文:
    #      f"Error: Did not run this research as you have already exceeded the "
    #      f"maximum number of concurrent research units. Please try again with "
    #      f"{configurable.max_concurrent_research_units} or fewer research units."
    #      ——注意这是"教育性"报错:把预算数字告诉模型,下一轮它自己会改。
    #      (回接你 R2 quiz Q3 的方案 B:裁剪+教育性回执,官方就是这么做的)
    #
    # TODO(R3-11): except 兜底(把 fan-out 到回礼的整段包进 try):
    #   任何异常 → 不炸图,goto END 优雅收工,update 带
    #   {"notes": get_notes_from_tool_calls(supervisor_messages),
    #    "research_brief": state.get("research_brief", "")}——烂尾也要把已有成果带出墙。
    #   ⚠️ 源码此处是 findings ①:`is_token_limit_exceeded(e, ...) or True`——
    #   嗅探结果被 or True 吞掉,是死代码。你自己决定:忠实复现(加注释标记)
    #   还是诚实写法(直接无条件收工)。行为等价,R5 findings.md 都要写这条。
    # R3-10a. 预算切片:list 切片天然处理"不够 N 张"的情况,不用 if。
    #    allowed 是掏钱执行的,overflow 是"单收了、活不干、回执教育"的。
    allowed_conduct_research_calls = conduct_research_calls[:configurable.max_concurrent_research_units]
    overflow_conduct_research_calls = conduct_research_calls[configurable.max_concurrent_research_units:]

    # R3-11. try 包住"花钱段"——fan-out 到回礼组装全在里面。
    try:
        # ① gather fan-out:一张派活单 = 整个 researcher 子图跑一遍(只跑 allowed)。
        #    同一个话题写两处:researcher_messages 是给模型看的对话开场白,
        #    research_topic 是给 compress_research 用的元数据(R2 里它进压缩 prompt)。
        research_tasks = [
            researcher_subgraph.ainvoke({
                "researcher_messages": [HumanMessage(content=tool_call["args"]["research_topic"])],
                "research_topic": tool_call["args"]["research_topic"]
            }, config)
            for tool_call in allowed_conduct_research_calls
        ]
        research_results = await asyncio.gather(*research_tasks)

        # ② zip 回礼:gather 保证结果顺序 == 任务提交顺序,所以 zip 对齐是安全的;
        #    tool_call_id 错位 = 模型看到张冠李戴的研究结果。
        #    结果是过墙 dict(R2 防火墙),只剩 compressed_research / raw_notes 两个 key;
        #    .get 的第二参数做降级:压缩三连败时防火墙送出来的 dict 里没有正文。
        conduct_tool_messages = [
            ToolMessage(
                content=result.get("compressed_research", "Error synthesizing research report: Maximum retries exceeded"),
                name=tool_call["name"],
                tool_call_id=tool_call["id"]
            )
            for result, tool_call in zip(research_results, allowed_conduct_research_calls)
        ]

        # R3-10c. 超发教育:活没干,但每个 tool_call_id 仍必须应答(provider 规矩);
        #    回执把预算数字明说给模型——你 R2 quiz Q3 的方案 B,官方同款。
        for overflow_call in overflow_conduct_research_calls:
            conduct_tool_messages.append(ToolMessage(
                content=(
                    f"Error: Did not run this research as you have already exceeded the "
                    f"maximum number of concurrent research units. Please try again with "
                    f"{configurable.max_concurrent_research_units} or fewer research units."
                ),
                name="ConductResearch",
                tool_call_id=overflow_call["id"]
            ))

        # ③ raw_notes 聚合:审计通道,模型永远看不到——只进 state,不进 ToolMessage。
        raw_notes_concat = "\n".join([
            "\n".join(result.get("raw_notes", []))
            for result in research_results
        ])
    except Exception:
        # 兜底收工:researcher 烂尾不许炸穿图,已收割的成果照样带出墙。
        # ⚠️ findings ①:源码这里是 `if is_token_limit_exceeded(e, configurable.research_model) or True:`
        #   ——嗅探结果被 or True 吞掉,永真死代码。复现版取诚实写法:无条件收工,行为等价。
        #   (R5 findings.md 收账;修法若要"区别对待 token 超限",得先想清楚其他异常该怎么办)
        return Command(
            goto=END,
            update={
                "notes": get_notes_from_tool_calls(supervisor_messages),
                "research_brief": state.get("research_brief", "")
            }
        )

    # ④ 收尾路由:think 的和 research 的回礼一起带走;raw_notes 非空才写(不做无意义脏写)。
    update_payload = {"supervisor_messages": think_tool_messages + conduct_tool_messages}
    if raw_notes_concat:
        update_payload["raw_notes"] = [raw_notes_concat]
    return Command(goto="supervisor", update=update_payload)


# TODO(R3-9): 组装并编译 supervisor 子图,赋值给 supervisor_subgraph:
#   StateGraph(SupervisorState, context_schema=Configuration)
#   → 两个节点 → START 连 supervisor → .compile()
#   对照 R1-10 想两个问题:这里为什么不需要 output_schema 防火墙?
#   (提示:supervisor 的调用方是谁?它的 state 里有没有 32k 垃圾山?)
#   为什么照样一条节点间 edge 都不用写?
supervisor_subgraph = StateGraph(SupervisorState, context_schema=Configuration) \
    .add_node("supervisor", supervisor) \
    .add_node("supervisor_tools", supervisor_tools) \
    .add_edge(START, "supervisor") \
    .compile()
