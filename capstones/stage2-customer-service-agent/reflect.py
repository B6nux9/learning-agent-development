"""
阶段二 Capstone · Reflection 节点 (reflect.py)

定位：给 run() 的「正常出口」加一道质检——答复交给用户之前，按红线自审一遍，
不合格就让模型重写一次。补齐 Planning-Acting-**Reflection** 闭环的最后一环。

  - Evaluator（挑错的）：本文件的 reflect()。用 LLM-as-judge，但 client 依赖注入 → 可 mock。
  - Actor（干活的）：agent.py 的 run()（不改核心，只在出口前插一次调用）。
  - Self-reflection（改进指令）：reflect 返回的 critique，被 run() 当反馈喂回模型重写。

【纪律回扣】
  - 反思只审「代码判不了、但有对错」的话术层：是否泄露/越权/答非所问/替人工瞎承诺。
    能 hard-code 的（越权/超额）继续由 tools.py 的 if 守，别让 reflect 去判红线（Q1）。
  - client 当参数传（依赖注入，L6）→ test 传假 client，不碰网络（L10 mock）。
"""

from __future__ import annotations

import json


# --------------------------------------------------------------------------
# 质检 rubric —— 反思的「依据」（空泛的「再检查一遍」没用，要具体，L6 回扣）
# --------------------------------------------------------------------------
# 这段是给 evaluator 模型看的「审查标准」。来源 = 现成的，抄你 SYSTEM_PROMPT 的话术约束
# + 三道安全线，翻译成「审查视角」的话。至少覆盖这几条红线（你来把它写全）：
#   - forbidden / order_not_found：只能统一说「没查到这笔订单哦～」，不许解释原因（防泄露）。
#   - needs_human / not_covered：不许自己承诺退款结果或转人工话术（该由 escalate 工具统一处理）。
#   - 忠实性：答复必须忠于工具返回，不许编造工具没给的信息（金额/状态/时间不许瞎报）。
#   - 答非所问：答复要对上用户的问题。
# 提示：结尾明确要求模型「只输出 JSON：{"verdict":"accept"|"revise","critique":"..."}」，
#       并说清 critique 要「具体、可操作」（指出哪条红线、怎么改），不是「感觉不太好」。
REFLECT_RUBRIC = """你是电商售后客服系统的**合规质检员**。你自己不回复用户、不调用任何工具，
你的唯一职责是：审查一条**即将发给用户的草稿答复**，对照下面的红线判断它是否合格。

判定原则：草稿**只要命中任意一条红线就 revise**；全部通过才 accept。存疑从严（偏向 revise）。

红线清单（对照「工具返回 trace」逐条查草稿）：
1. 泄露归属：工具返回 forbidden 或 order_not_found 时，草稿只能统一说「没查到这笔订单哦～」这类话，
   **不得解释订单为何查不到**（如「这单不是您的」「该订单属于他人」都算泄露）→ revise。
2. 越权承诺：工具返回 needs_human / not_covered 时，草稿**不得自己承诺退款结果、也不得自己编转人工话术**
   （转人工由系统统一开工单处理）；草稿若替人工下了结论或做了承诺 → revise。
3. 忠实性：草稿陈述的金额 / 订单状态 / 发货时间等，**必须与工具 trace 一致**；
   工具没返回的信息**不得编造**（凭空报一个金额、状态即为编造）→ revise。
4. 答非所问：草稿要正面回应「用户消息」里的问题；答非所问 → revise。

输出要求：**只输出 JSON**，形如 {"verdict":"accept","critique":""} 或
{"verdict":"revise","critique":"<具体可操作的修改指令>"}。
critique 必须**指出命中的是哪条红线、草稿哪句话有问题、应改成什么**，禁止「感觉不太好」这类空话。
"""


# --------------------------------------------------------------------------
# reflect —— evaluator 本体（LLM-as-judge）
# --------------------------------------------------------------------------
def reflect(user_message: str, draft_reply: str, tool_trace: list[dict], client) -> dict:
    """对一条**即将发给用户**的草稿答复做质检。

    接口契约（coach 给签名+输入输出+约束，函数体你写）：
      输入
        user_message : str        —— 用户这句话（判「答非所问」要用）
        draft_reply  : str        —— 模型写好、准备发给用户的草稿
        tool_trace   : list[dict] —— 本轮所有工具返回的 dict（判「话术是否忠于工具返回」要用）
        client       : OpenAI     —— **依赖注入**，不在函数里 get_client()（否则没法 mock）
      输出（结构化，别返回自然语言）
        {"verdict": "accept", "critique": ""}        —— 合格，照发
        {"verdict": "revise", "critique": "<可操作的修改指令>"}  —— 不合格，要重写
      约束
        1. 用 REFLECT_RUBRIC 当 system，把 user_message / draft_reply / tool_trace 拼进 user。
        2. temperature=0；response_format={"type":"json_object"}（结构化输出，L6/L8 回扣）。
        3. **解析兜底**：模型输出不是合法 JSON、或缺字段时——不要抛异常。
           想清楚这里该 accept 还是 revise？（这就是我埋的 fail-open/fail-closed 问题，写完答我）
        4. verdict 只允许 "accept" / "revise" 两个值；其它值按兜底处理。
    """
    # 拼 user prompt：把待审材料（用户问题 / 草稿 / 工具轨迹）交给 judge
    user_prompt = f"""
    你是 evaluator，负责对一条即将发给用户的草稿答复做质检。
    现有：
      用户消息：{user_message}
      草稿答复：{draft_reply}
      工具调用返回 trace：{json.dumps(tool_trace, ensure_ascii=False)}
    请按系统消息里的审查标准，判断草稿答复是否合格，并输出 JSON。
    """

    # 调用 LLM 并解析。
    # 整段 try：API 调用（模型宕机/超时）和解析（非法 JSON/缺字段）都可能失败，
    # 任一失败都走 fail-open —— reflect 是叠在三道 hard-code 安全线之上的**质量层**，
    # 质量层故障绝不能把已经安全的 agent 拖垮，故默认放草稿过（accept）。
    try:
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": REFLECT_RUBRIC},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        verdict = result.get("verdict")
        critique = result.get("critique", "")
        if verdict not in ("accept", "revise"):
            raise ValueError(f"invalid verdict: {verdict!r}")
        return {"verdict": verdict, "critique": critique}
    except Exception:
        # fail-open：reflect 自身故障时不阻断用户，放草稿过。
        # 生产环境这里要 logger.warning(exc_info=True) 上报，让「质检静默失灵」可观测。
        return {"verdict": "accept", "critique": ""}

