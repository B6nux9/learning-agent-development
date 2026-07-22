"""
L6 作业:上下文管理 + 结构化输出

两部分,A 是主菜(上下文压缩),B 是小练习(补结构化输出这一课的手感)。

═══════════════════════════════════════════════════════════════
Part A(主):给多轮对话加【阈值触发的上下文压缩】
═══════════════════════════════════════════════════════════════
实现上半场策略③"混合":平时不管,一旦上下文超过阈值,把最老的几轮压成摘要,
保留最近几轮原文。**惰性优化** —— 不要每轮都压。

  TODO A1  estimate_tokens():粗略估算 messages 的 token 数
  TODO A2  summarize_messages():把一段旧消息用【一次便宜的 LLM 调用】压成摘要文本
  TODO A3  compact_if_needed():阈值判断 + 执行压缩,拼出新的 messages

跑通标准:
  - 连续聊 10+ 轮(随便问订单),观察 [ctx] 日志:token 数涨到阈值时触发一次压缩,
    压缩后 token 数明显回落,且【压缩后 agent 仍记得早期信息】(比如你一开始说的名字)。

═══════════════════════════════════════════════════════════════
Part B(小):用【结构化输出】重写 L4 的 route_llm
═══════════════════════════════════════════════════════════════
你 L4 的路由用的是土办法:prompt 里求它 → .strip().lower() 洗它 → in VALID_GROUPS 验它。
现在用 response_format 的 json_schema 让 API 保证输出结构,对比一下两者的差别。

  TODO B1  route_structured():用结构化输出做意图分类,返回 {"group": "...", "reason": "..."}

注意:多要一个 reason 字段不是为了给用户看,而是【方便你调试和日志】——
      这正是"结构化输出用于代码消费"的典型场景(对比:给用户的回复应该是普通文本)。
"""

import os
import json
from dataclasses import dataclass
from openai import OpenAI

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

MODEL = "deepseek-v4-flash"          # 主对话
CHEAP_MODEL = "deepseek-chat"    # 摘要/路由这种小活(有更便宜的就换更便宜的)

# 压缩阈值:超过这个估算 token 数就触发压缩(故意设小,方便你几轮内就看到效果)
COMPACT_THRESHOLD = 800
KEEP_RECENT_TURNS = 4            # 压缩时保留最近几条消息的原文


# ---- 演示业务工具 ----
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

SYSTEM_PROMPT = "你是电商客服助手。涉及订单信息时必须调用 query_order 查询,禁止编造。回答简洁,不超过3句。"


# ============================================================
#  A1(已升级为生产做法):用 API 返回的 usage 统计真实 token
# ============================================================
# 【为什么废掉原来的"字符数/2"估算】
#   那个实现有两个问题,第二个是硬伤:
#     1. 不精确——中英文、标点的 token 密度差别很大。
#     2. 🔴 **系统性漏算**:它只数了 messages 里的 content,而一次请求真正发出去的还包括
#        【工具 schema(TOOLS)】——每轮都发,5 个工具就是几百 token;还有 tool_calls 的
#        arguments、每条消息的结构开销(role 标记/分隔符,每条约 3-4 token)。
#        所以估算值恒偏低,而且工具越多偏得越多 —— 阈值判断会直接失灵。
#
# 【生产做法】API 每次响应都回传真实用量,那是计费依据,把上述全部算进去了:
#     response.usage.prompt_tokens       本次请求的输入 token(权威)
#     response.usage.completion_tokens   输出 token
#   我们不"预估",而是【记住上一次请求的真实 prompt_tokens】,用它判断要不要压缩。
#   上下文是渐进增长的,用上一轮真实值判断这一轮,误差很小,且零依赖零成本。
#
# 【什么时候仍需要分词器】如果你必须在【发请求之前】精确知道大小(例如要截断到刚好塞满
#   窗口、或做请求前的成本拦截),才需要引入 tokenizer:
#     - OpenAI 系:  tiktoken.get_encoding("cl100k_base").encode(text)
#     - DeepSeek/Qwen 等:分词器不同,tiktoken 数出来对不上,要用 HuggingFace
#       transformers.AutoTokenizer 加载【对应模型自己的】tokenizer 才准。
#   代价:额外依赖 + 下载词表 + CPU 开销。本作业不需要。


@dataclass
class SessionStats:
    """会话级用量统计。

    生产里这类指标通常挂在 session / request context 对象上,用于:
      - 上下文压缩的阈值判断(本作业用途)
      - 成本核算与告警(token 消耗是直接的钱)
      - 可观测性上报  ← L13 会正式做,拼多多 JD 明确列了"Token 消耗"这个指标
    """
    last_prompt_tokens: int = 0      # 最近一次请求的输入 token —— 压缩阈值就看它
    total_prompt_tokens: int = 0     # 会话累计输入
    total_completion_tokens: int = 0  # 会话累计输出
    llm_calls: int = 0               # 会话内 LLM 调用次数

    def record(self, usage) -> None:
        """主对话链的调用:既计成本,也更新阈值依据。"""
        if usage is None:            # 防御:极少数实现可能不回 usage
            return
        self.last_prompt_tokens = usage.prompt_tokens
        self._accumulate(usage)

    def record_side_call(self, usage) -> None:
        """旁路调用(摘要、路由这类小活):【只计成本,不更新 last_prompt_tokens】。

        为什么要分开?因为 last_prompt_tokens 是用来判断【主对话上下文】有多大的。
        摘要调用发的是另一组 messages,把它的 prompt_tokens 混进来会污染压缩决策。
        —— 指标要分清"衡量什么",这在 L13 可观测性里是个反复出现的坑。
        """
        if usage is None:
            return
        self._accumulate(usage)

    def _accumulate(self, usage) -> None:
        self.total_prompt_tokens += usage.prompt_tokens
        self.total_completion_tokens += usage.completion_tokens
        self.llm_calls += 1

    def summary(self) -> str:
        return (f"调用 {self.llm_calls} 次 | 累计输入 {self.total_prompt_tokens} "
                f"| 累计输出 {self.total_completion_tokens} tokens")


stats = SessionStats()


# ============================================================
#  TODO A2:把一段旧消息压成摘要
# ============================================================
def summarize_messages(old_messages: list) -> str:
    """用一次【便宜模型】调用,把 old_messages 压成一段简短摘要文本。

    提示:
      - 先把 old_messages 转成可读文本(谁说了什么),再塞给模型。
      - prompt 要写清"保留什么":用户身份/偏好、提过的订单号、已确认的事实、未完成的诉求。
        (想想上半场:摘要是有损的,所以要明确指定【不能丢什么】)
      - temperature=0(要稳定),max_tokens 给足(别重蹈 L4 覆辙)。
      - 应用 Prompt 五块骨架和"别用模糊限定词"。
    """
    # 【改 1】把"指令"和"待摘要的内容"分开放:指令进 system,内容进 user。
    #        你原来是拼成一整个 user 消息。分开的好处:角色语义清晰,模型更容易分清
    #        "哪些是要我遵守的规则"和"哪些是要我处理的数据"——这正是 L5 学的角色区分。
    #
    # 【改 2】prompt 按本节五块骨架重写。对比你原来那句:
    #        原:"...不要丢失重要信息。"  ← "重要"是模糊词,模型自己判断什么算重要,
    #                                      结果很可能把姓名当闲聊丢掉 -> 验收句就答不出了
    #        新:把"必须保留"逐条列死 + 加一条禁止项,不给模型自由裁量空间。
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

    # 【改 3】.get("role", "") 现在安全了(归一化之后全是 dict)。
    #        用列表 + join 拼接,比字符串反复 += 更清晰(字符串是不可变对象,
    #        += 每次都在造新字符串;量大时 join 效率也更好)。
    lines = []
    for msg in old_messages:
        content = msg.get("content") or ""
        if content:
            lines.append(f"{msg.get('role', '')}: {content}")
    conversation = "\n".join(lines)

    response = client.chat.completions.create(
        model=CHEAP_MODEL,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM},
            {"role": "user", "content": conversation},
        ],
        temperature=0,      # 摘要要稳定可复现,不要它发挥
        max_tokens=1024,    # 给足(L4 教训:设小了推理型模型会返回空)
    )
    # 【改】摘要这次调用本身也花钱,同样计入统计。
    #      注意:它【不该】更新 last_prompt_tokens 用于阈值判断(那是另一条对话链的用量),
    #      所以这里只累加成本,不影响压缩决策 —— 见下方 record_side_call。
    stats.record_side_call(response.usage)
    return response.choices[0].message.content


# ============================================================
#  TODO A3:阈值触发的压缩
# ============================================================
def compact_if_needed(messages: list) -> list:
    """如果 messages 估算 token 超过 COMPACT_THRESHOLD,就压缩;否则原样返回。

    压缩后的结构应该是:
        [ system 消息(原样保留) ,
          一条承载摘要的消息 ,
          最近 KEEP_RECENT_TURNS 条原文 ]

    要想清楚的几件事:
      1. system 消息【绝对不能压掉】——它是人设+规则,压了 agent 就失忆变傻。
      2. 摘要放进 messages 时用什么 role?(提示:它是背景信息不是用户说的话——回想 L5 Q4)
      3. ⚠️ 陷阱:切分时不能把 assistant(带 tool_calls) 和它对应的 tool 消息拆散!
         API 要求每个 tool_call 都要有对应的 tool 结果消息,拆散了会报错。
         最简单的稳妥做法:保留区间往前找,找到一个"干净的切点"再切。
      4. 压缩后打印一行日志,方便你观察效果(临时调试,封版前删):
         print(f"[ctx] 压缩: {before} -> {after} tokens")
    """
    # 【改】判断依据从"自己估算"换成【上一次请求 API 实测的 prompt_tokens】。
    #      第一轮时它是 0(还没发过请求),自然不触发压缩 —— 符合预期。
    current_tokens = stats.last_prompt_tokens
    if current_tokens <= COMPACT_THRESHOLD:
        return messages          # 没超阈值就啥也不干 —— 惰性优化,别每轮都压

    # 【改·核心】切点逻辑。你原来的条件是:
    #     while 切点是 assistant 且有 tool_calls: cut_index -= 1
    #   这检查的是【安全情况】,而不是危险情况,方向反了。想清楚这件事:
    #
    #   messages 里工具调用长这样(必须成对出现):
    #       [... , assistant(带 tool_calls) , tool(结果) , tool(结果) , ...]
    #                      ↑ 父                    ↑ 子       ↑ 子
    #   新列表 = [system, 摘要] + messages[cut_index:] ,即 cut_index 之前的全被切走。
    #
    #   - 切点落在 assistant(带 tool_calls) 上 → 父和子都在保留区 → ✅ 安全
    #   - 切点落在 tool 上                    → 父被切走,只剩孤儿 tool → ❌ API 报错
    #
    #   所以要往前退的条件是【切点是 tool 消息】。一直退到不是 tool 为止,
    #   自然就退到了那条 assistant 父消息上,父子就一起被保留了。
    cut_index = max(1, len(messages) - KEEP_RECENT_TURNS)   # max(1,...) 保证不会切掉 system
    while cut_index > 1 and messages[cut_index].get("role") == "tool":
        cut_index -= 1

    old_messages = messages[1:cut_index]      # [1:] 跳过 system —— system 绝不能压掉

    # 【改·补兜底】如果没东西可压(比如退到头了),直接返回,别去调一次没意义的 LLM。
    # (这也是你的老毛病:每条路径都要有明确返回 —— L3、L5 都栽过)
    if not old_messages:
        return messages

    summary = summarize_messages(old_messages)

    # 摘要用 system 角色:它是【背景信息】,不是用户说的话,也不是助手的回复。
    # (L5 Q4 学的:长期记忆注入 system,同一个道理 —— 位置要对,角色更要对)
    new_messages = (
        [messages[0], {"role": "system", "content": f"[早前对话摘要] {summary}"}]
        + messages[cut_index:]
    )

    # 【改】压缩后的真实大小要等下一次请求的 usage 才知道(我们不再自己估),
    #      所以这里只报"压缩前实测值 + 做了什么",下一轮的 [ctx] 行会显示回落效果。
    print(f"[ctx] 触发压缩:上轮实测 {current_tokens} tokens > 阈值 {COMPACT_THRESHOLD};"
          f" 已把 {len(old_messages)} 条旧消息压成摘要,保留最近 {len(messages) - cut_index} 条原文")
    return new_messages

def run_agent(messages: list) -> str:
    turn = 0
    while turn < 8:
        turn += 1
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        stats.record(response.usage)      # 【改】记录真实用量 —— 压缩阈值和成本统计都靠它
        msg = response.choices[0].message

        # 【改·根治】原来是 messages.append(msg) —— 直接把 SDK 对象塞进列表,
        # 造成 messages 变成"混血列表"(dict + ChatCompletionMessage),
        # 导致下游每个函数都要 isinstance 判一次(L4/L5/L6 已经因此炸了三次)。
        # 现在在【入口】统一转成 dict,下游全部代码就都只需面对 dict 一种类型。
        #   model_dump()      —— SDK 对象是 pydantic 模型,这个方法转成 dict
        #   exclude_none=True —— 排掉值为 None 的字段(function_call/refusal 等),
        #                        否则会把一堆 null 垃圾塞进下一次请求
        if not msg.tool_calls:
            messages.append(msg.model_dump(exclude_none=True))
            return msg.content
        messages.append(msg.model_dump(exclude_none=True))
        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            try:
                result = AVAILABLE_TOOLS[name](**args)
            except Exception as e:
                result = json.dumps({"error": str(e)}, ensure_ascii=False)
            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
    return "抱歉,这个问题我暂时处理不了,已为您转接人工客服"


# ============================================================
#  TODO B1:用结构化输出做意图路由(对比 L4 的土办法)
# ============================================================
def route_structured(user_text: str) -> dict:
    """用【结构化输出】把 user_text 分类,返回 {"group": ..., "reason": ...}。

    做法:在 client.chat.completions.create 里加 response_format 参数,
    形如:
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "route",
                "schema": {
                    "type": "object",
                    "properties": {
                        "group":  {"type": "string", "enum": ["order", "refund", "account"]},
                        "reason": {"type": "string"}
                    },
                    "required": ["group", "reason"],
                    "additionalProperties": False
                }
            }
        }

    要做的:
      1. 写好 system prompt(分类任务说明)
      2. 带上 response_format 调用
      3. json.loads 解析返回的 content,拿到 dict

    ⚠️ 现实注意:不是所有厂商/模型都支持 json_schema 强制。
       如果 DeepSeek 报错不支持,退一档试 response_format={"type": "json_object"}(JSON mode),
       并在 prompt 里说清字段——然后【体会一下这两档保证强度的差别】,这本身就是本题的收获。
       无论哪档,都仍要保留一层校验兜底(group 不在枚举里就回默认值)——
       回想 L4:永远不要完全信任外部返回。
    """
    # 你的代码:
    system_prompt = "你是一个意图分类器,请根据用户输入将其分类为 'order', 'refund', 或 'account'。请提供分类的理由。"
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "route",
            "schema": {
                "type": "object",
                "properties": {
                    "group": {"type": "string", "enum": ["order", "refund", "account"]},
                    "reason": {"type": "string"}
                },
                "required": ["group", "reason"],
                "additionalProperties": False
            }
        }
    }
    response = client.chat.completions.create(
        model=CHEAP_MODEL,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_text}],
        response_format=response_format
    )
    content = response.choices[0].message.content
    try:
        result = json.loads(content)
        if result.get("group") not in ["order", "refund", "account"]:
            result["group"] = "order"  # 默认值
            result["reason"] = "分类不在预期范围,默认归为 'order'"
    except json.JSONDecodeError:
        result = {"group": "order", "reason": "JSON 解析失败,默认归为 'order'"}
    return result   


def main():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("(多聊几轮,观察 [ctx] 日志;输入 退出 结束)")
    while True:
        user_input = input("你> ")
        if user_input.lower() in ["quit", "exit", "退出"]:
            break
        messages.append({"role": "user", "content": user_input})
        messages = compact_if_needed(messages)          # ← 每轮检查,但只在超阈值时才真压
        print(f"客服助手: {run_agent(messages)}")
        # 【改】显示 API 实测用量,而非自己估算。stats.summary() 顺便让你看到累计成本
        #      ——盯着"累计输入"这个数字涨,你会对上半场讲的【平方级增长】有切身体感。
        print(f"[ctx] 本轮实测输入 {stats.last_prompt_tokens} tokens | {stats.summary()}")


if __name__ == "__main__":
    main()
