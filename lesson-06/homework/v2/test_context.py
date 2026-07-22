"""context.py 的单元测试。

═══════════════════════════════════════════════════════════════════════
本次作业的【新肌肉】就在这个文件里。
═══════════════════════════════════════════════════════════════════════

注意这些测试的一个共同特点:**没有任何一个会调用 LLM**。
- 测 find_safe_cut_index:它本来就是纯函数,天然可测。
- 测 ContextManager:通过【注入一个假的 summarizer】把 LLM 换掉。

这就是"依赖注入"的实际价值:
  ✅ 快   —— 整个测试套件毫秒级跑完(真调 LLM 要几十秒)
  ✅ 稳   —— 不受模型随机性影响,结果可复现(真 LLM 每次摘要都不一样,没法断言)
  ✅ 免费 —— 不烧一个 token
  ✅ 能测异常路径 —— 想测"摘要器报错怎么办",注入一个专门抛异常的假摘要器即可

运行方式:
    pip install pytest
    cd lesson-06/homework/v2
    pytest test_context.py -v

如果不想装 pytest,文件底部有个极简的自跑入口:  python test_context.py
"""

import pytest

from context import ContextManager, CompactResult, find_safe_cut_index


# ══════════════════════════════════════════════════════════════════════
#  测试替身(test double):假的摘要器
# ══════════════════════════════════════════════════════════════════════
def fake_summarizer(messages: list[dict]) -> str:
    """假摘要器:不调 LLM,返回可预测的固定内容。

    返回值里带上条数,方便断言"到底压了几条进去"。
    """
    return f"[FAKE SUMMARY of {len(messages)} messages]"


def exploding_summarizer(messages: list[dict]) -> str:
    """专门用来测异常路径的假摘要器 —— 真 LLM 你没法让它按需报错,假的可以。"""
    raise RuntimeError("summarizer down")


# ══════════════════════════════════════════════════════════════════════
#  测试数据构造小工具
# ══════════════════════════════════════════════════════════════════════
def sys_msg(text="你是助手"):
    return {"role": "system", "content": text}


def user_msg(text="hi"):
    return {"role": "user", "content": text}


def assistant_msg(text="hello"):
    return {"role": "assistant", "content": text}


def assistant_with_tools(n=1):
    """带 n 个 tool_calls 的 assistant 消息(content 为 None,这是真实形态)。"""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": f"call_{i}", "type": "function",
             "function": {"name": "query_order", "arguments": "{}"}}
            for i in range(n)
        ],
    }


def tool_msg(call_id="call_0"):
    return {"role": "tool", "tool_call_id": call_id, "content": '{"status":"运输中"}'}


# ══════════════════════════════════════════════════════════════════════
#  Part 1:find_safe_cut_index —— 我给 3 个样板,你补 4 个
# ══════════════════════════════════════════════════════════════════════

def test_cut_index_normal_case():
    """普通情况:全是 user/assistant,没有工具消息,切点就是 len - keep_recent。"""
    messages = [sys_msg(), user_msg(), assistant_msg(), user_msg(), assistant_msg()]
    # 5 条消息,保留最近 2 条 -> 切点应为 3
    assert find_safe_cut_index(messages, keep_recent=2) == 3


def test_cut_index_backs_off_tool_message():
    """⚠️ 核心用例:初始切点落在 tool 消息上时,必须往前退到它的 assistant 父消息。"""
    messages = [
        sys_msg(),                 # 0
        user_msg(),                # 1
        assistant_with_tools(),    # 2  ← 父
        tool_msg(),                # 3  ← 子(初始切点会落在这)
        assistant_msg(),           # 4
    ]
    # 5 条,keep_recent=2 -> 初始切点 3,那是 tool 消息 -> 必须退到 2(父 assistant)
    idx = find_safe_cut_index(messages, keep_recent=2)
    assert idx == 2, "切点不能落在 tool 上,否则父 assistant 被切走会产生孤儿 tool"
    # 再验一次结果确实合法:切出来的第一条不是 tool
    assert messages[idx]["role"] != "tool"


def test_cut_index_only_system():
    """边界 a:只有 system 一条,没什么可压 -> 返回 len(messages)。"""
    messages = [sys_msg()]
    assert find_safe_cut_index(messages, keep_recent=4) == len(messages)


# ────────────────────────────────────────────────────────────────────
#  TODO 3:补齐下面 4 个测试(把 pass 换成真正的断言)
# ────────────────────────────────────────────────────────────────────

def test_cut_index_shorter_than_keep_recent():
    """边界 b:消息总数比 keep_recent 还少 -> 应该没什么可压。

    提示:想清楚这时候期望返回什么?(和 test_cut_index_only_system 一致吗?)
    """
    # TODO: 你的测试
    pass


def test_cut_index_consecutive_tool_messages():
    """边界 d:一条 assistant 调了 3 个工具 -> 后面跟着 3 条连续的 tool 消息。
    初始切点若落在中间某条 tool 上,要一路退到那条 assistant。

    提示:用 assistant_with_tools(3) + 三条 tool_msg 构造。
    """
    # TODO: 你的测试
    pass


def test_cut_index_never_cuts_system():
    """边界 e:无论怎么退,返回值都不应该 <= 0(system 必须留住)。

    提示:构造一个开头就是 assistant+tool、且 keep_recent 很大的场景。
    """
    # TODO: 你的测试
    pass


def test_cut_index_is_pure():
    """纯函数验证:调用它【不应该修改入参】。

    提示:调用前先深拷贝一份(copy.deepcopy),调用后断言原列表没变。
    这类测试在生产代码里很有价值——它能防住"某天有人手滑加了个原地修改"。
    """
    # TODO: 你的测试
    pass


# ══════════════════════════════════════════════════════════════════════
#  Part 2:ContextManager —— 我给 2 个样板,你补 4 个
# ══════════════════════════════════════════════════════════════════════

def test_below_threshold_does_not_compact():
    """没超阈值 -> 不压缩,compacted 为 False。"""
    cm = ContextManager(summarizer=fake_summarizer, threshold=1000, keep_recent=2)
    messages = [sys_msg(), user_msg(), assistant_msg()]
    result = cm.compact(messages, current_tokens=500)
    assert result.compacted is False
    assert len(result.messages) == 3


def test_hybrid_keeps_system_and_inserts_summary():
    """hybrid 策略:system 保留 + 摘要插在它后面 + 最近 N 条原文保留。"""
    cm = ContextManager(summarizer=fake_summarizer, threshold=100,
                        keep_recent=2, strategy="hybrid")
    messages = [sys_msg(), user_msg("第1句"), assistant_msg("答1"),
                user_msg("第2句"), assistant_msg("答2")]
    result = cm.compact(messages, current_tokens=999)   # 远超阈值,必压

    assert result.compacted is True
    assert result.messages[0]["role"] == "system"           # system 还在第一位
    assert "FAKE SUMMARY" in result.messages[1]["content"]  # 摘要紧随其后
    assert result.messages[1]["role"] == "system"           # 摘要用 system 角色
    # 最近 2 条原文还在最后
    assert result.messages[-1]["content"] == "答2"


# ────────────────────────────────────────────────────────────────────
#  TODO 4:补齐下面 4 个测试
# ────────────────────────────────────────────────────────────────────

def test_compact_does_not_mutate_input():
    """⚠️ 重要:compact 绝不能原地修改传进去的 messages。

    提示:deepcopy 一份原始数据,compact 之后断言原 list 长度和内容都没变。
    """
    # TODO: 你的测试
    pass


def test_truncate_strategy_does_not_call_summarizer():
    """truncate 策略应该【完全不调用 summarizer】(省钱)。

    提示:注入 exploding_summarizer —— 如果被调用就会抛异常,
    测试能跑通就证明没调过。这是个很聪明的测法,记住这个套路。
    """
    # TODO: 你的测试
    pass


def test_invalid_config_fails_fast():
    """非法配置应当在构造时就报错,而不是等到运行时出怪事。

    提示:用 pytest.raises 断言 threshold=0 或 keep_recent=-1 会抛异常。
        with pytest.raises(ValueError):
            ContextManager(summarizer=fake_summarizer, threshold=0)
    """
    # TODO: 你的测试
    pass


def test_tool_pairing_preserved_after_compact():
    """⚠️ 端到端的安全性验证:压缩后的消息序列里,不能出现【孤儿 tool】。

    提示:构造一个含 assistant_with_tools + tool_msg 的较长列表,压缩后遍历结果,
    断言"每条 role='tool' 的消息之前,都能找到一条带 tool_calls 的 assistant"。
    这个测试直接对应你上一版踩的那个 API 报错。
    """
    # TODO: 你的测试
    pass


# ══════════════════════════════════════════════════════════════════════
#  不想装 pytest 时的极简自跑入口
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ✅ {name}")
                passed += 1
            except Exception as e:
                print(f"  ❌ {name}: {type(e).__name__}: {e}")
                failed += 1
    print(f"\n通过 {passed} / 失败 {failed}")
