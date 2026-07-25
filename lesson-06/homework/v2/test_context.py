"""context.py 的单元测试。

═══════════════════════════════════════════════════════════════════════
本次由教练代写(用户选择先专注实现代码,测试留待后续专门学习)。
所以现在请【反过来用】这个文件:把它当作 compact() 的【验收标准 / spec】——
    你的目标 = 让这些测试全部变绿。
测试里每条 assert 就是对 compact 行为的一条硬性要求,比读文档更精确。
═══════════════════════════════════════════════════════════════════════

契约约定(compact 要实现成这样,测试据此断言):
  - dropped_count = 被折叠进摘要 / 被丢弃的【原始非 system 消息】条数 = cut - 1
  - kept_count    = 保留原文的原始消息条数                        = len(messages) - cut
  其中 cut = find_safe_cut_index(messages, keep_recent)

这些测试的共同特点:**没有一个会真的调用 LLM**(靠注入 fake/exploding summarizer),
所以毫秒级、可复现、不烧 token —— 这就是依赖注入的价值,以后专门学测试时再回味。

运行:
    pytest test_context.py -v          # 装了 pytest
    python test_context.py             # 没装 pytest 的极简自跑入口(见文件底部)
"""

import copy

import pytest

from context import ContextManager, CompactResult, find_safe_cut_index


# ══════════════════════════════════════════════════════════════════════
#  测试替身(test double)
# ══════════════════════════════════════════════════════════════════════
def fake_summarizer(messages: list[dict]) -> str:
    """假摘要器:不调 LLM,返回可预测的固定内容(带条数便于断言)。"""
    return f"[FAKE SUMMARY of {len(messages)} messages]"


def exploding_summarizer(messages: list[dict]) -> str:
    """一被调用就爆炸 —— 用来证明"某策略没有调用摘要器"。"""
    raise RuntimeError("summarizer 不该被调用")


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
    """带 n 个 tool_calls 的 assistant(content=None,真实形态)。"""
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


def assert_no_orphan_tool(messages):
    """断言:每条 tool 消息之前,要么是另一条 tool,要么是带 tool_calls 的 assistant。
    这正是"孤儿 tool 会让 API 报错"的那条约束。"""
    for i, m in enumerate(messages):
        if m.get("role") == "tool":
            assert i > 0, f"tool 出现在下标 0,没有父 assistant"
            prev = messages[i - 1]
            ok = prev.get("role") == "tool" or (
                prev.get("role") == "assistant" and prev.get("tool_calls"))
            assert ok, f"下标 {i} 的 tool 是孤儿(前一条是 {prev.get('role')})"


# ══════════════════════════════════════════════════════════════════════
#  Part 1:find_safe_cut_index
# ══════════════════════════════════════════════════════════════════════

def test_cut_index_normal_case():
    """普通情况:全是 user/assistant,切点 = len - keep_recent。"""
    messages = [sys_msg(), user_msg(), assistant_msg(), user_msg(), assistant_msg()]
    assert find_safe_cut_index(messages, keep_recent=2) == 3


def test_cut_index_backs_off_tool_message():
    """核心:初始切点落在 tool 上时,退回它的 assistant 父消息。"""
    messages = [sys_msg(), user_msg(), assistant_with_tools(), tool_msg(), assistant_msg()]
    idx = find_safe_cut_index(messages, keep_recent=2)   # 初始切点 3(tool) → 退到 2
    assert idx == 2
    assert messages[idx]["role"] != "tool"


def test_cut_index_only_system():
    """边界 a:只有 system 一条 → 无可压 → 返回 1。"""
    messages = [sys_msg()]
    assert find_safe_cut_index(messages, keep_recent=4) == 1


def test_cut_index_shorter_than_keep_recent():
    """边界 b:消息比 keep_recent 还少 → 无可压 → 返回 1。

    ⚠️ 这个用例专门锁住"太短时返回 1(而不是 len)"这个设计决策。
    对比 test_cut_index_only_system(n=1,两种设计都返回 1,区分不出),
    这里 n=3,只有 return 1 的实现才能通过。
    """
    messages = [sys_msg(), user_msg(), assistant_msg()]   # n=3
    assert find_safe_cut_index(messages, keep_recent=4) == 1


def test_cut_index_consecutive_tool_messages():
    """边界 d:一条 assistant 调 3 个工具 → 3 条连续 tool。
    初始切点落在中间某条 tool 上,要一路退到那条 assistant。"""
    messages = [
        sys_msg(),                    # 0
        user_msg(),                   # 1
        assistant_with_tools(3),      # 2  ← 父
        tool_msg("call_0"),           # 3
        tool_msg("call_1"),           # 4
        tool_msg("call_2"),           # 5
        assistant_msg(),              # 6
    ]
    # n=7, keep_recent=3 → 初始切点 4(tool) → 退 4→3→2,停在 assistant_with_tools
    idx = find_safe_cut_index(messages, keep_recent=3)
    assert idx == 2
    assert_no_orphan_tool(messages[idx:])   # 切出来的尾段自身合法


def test_cut_index_never_cuts_system():
    """边界 e:一路回退也不能越过 system(返回值 >= 1)。"""
    # messages[1] 是带 tool_calls 的 assistant,后面跟着 tool。
    # keep_recent=2 → 初始切点 2(tool)→ 退到 1,while 的 i>1 守住不再退。
    messages = [sys_msg(), assistant_with_tools(), tool_msg(), tool_msg()]
    idx = find_safe_cut_index(messages, keep_recent=2)
    assert idx == 1
    assert idx >= 1                      # system 永远保住


def test_cut_index_is_pure():
    """纯函数:调用不得修改入参。"""
    messages = [sys_msg(), user_msg(), assistant_with_tools(), tool_msg(), assistant_msg()]
    snapshot = copy.deepcopy(messages)
    find_safe_cut_index(messages, keep_recent=2)
    assert messages == snapshot, "find_safe_cut_index 不应修改入参"


# ══════════════════════════════════════════════════════════════════════
#  Part 2:ContextManager
# ══════════════════════════════════════════════════════════════════════

def test_below_threshold_does_not_compact():
    """没超阈值 → 不压缩。"""
    cm = ContextManager(summarizer=fake_summarizer, threshold=1000, keep_recent=2)
    messages = [sys_msg(), user_msg(), assistant_msg()]
    result = cm.compact(messages, current_tokens=500)
    assert result.compacted is False
    assert len(result.messages) == 3


def test_hybrid_keeps_system_and_inserts_summary():
    """hybrid:system 保留 + 摘要(system 角色)插在其后 + 最近 N 条原文保留。"""
    cm = ContextManager(summarizer=fake_summarizer, threshold=100,
                        keep_recent=2, strategy="hybrid")
    messages = [sys_msg(), user_msg("第1句"), assistant_msg("答1"),
                user_msg("第2句"), assistant_msg("答2")]
    result = cm.compact(messages, current_tokens=999)

    assert result.compacted is True
    assert result.messages[0]["role"] == "system"
    assert result.messages[1]["role"] == "system"
    assert "FAKE SUMMARY" in result.messages[1]["content"]
    assert result.messages[-1]["content"] == "答2"
    # 契约:cut=3 → dropped = [第1句,答1] = 2 条;kept = [第2句,答2] = 2 条
    assert result.dropped_count == 2
    assert result.kept_count == 2


def test_compact_does_not_mutate_input():
    """compact 绝不原地修改入参 messages。"""
    cm = ContextManager(summarizer=fake_summarizer, threshold=100, keep_recent=2)
    messages = [sys_msg(), user_msg("a"), assistant_msg("b"),
                user_msg("c"), assistant_msg("d")]
    snapshot = copy.deepcopy(messages)
    cm.compact(messages, current_tokens=999)   # 触发压缩
    assert messages == snapshot, "compact 修改了调用方传进来的 messages"


def test_truncate_strategy_does_not_call_summarizer():
    """truncate 策略:完全不调用 summarizer(注入会爆炸的那个来证明)。"""
    cm = ContextManager(summarizer=exploding_summarizer, threshold=100,
                        keep_recent=2, strategy="truncate")
    messages = [sys_msg(), user_msg("a"), assistant_msg("b"),
                user_msg("c"), assistant_msg("d")]
    # 若 compact 调用了 summarizer,exploding_summarizer 会抛异常,测试即失败
    result = cm.compact(messages, current_tokens=999)
    assert result.compacted is True
    assert result.summary is None                 # truncate 不产生摘要
    assert result.messages[0]["role"] == "system"  # system 仍保留
    # truncate 直接丢旧消息,不插摘要:结果里不应出现 FAKE/摘要标记
    assert all("SUMMARY" not in (m.get("content") or "") for m in result.messages)


def test_invalid_config_fails_fast():
    """非法配置在【构造时】就报错(fail fast),而不是运行时出怪事。"""
    with pytest.raises(ValueError):
        ContextManager(summarizer=fake_summarizer, threshold=0)
    with pytest.raises(ValueError):
        ContextManager(summarizer=fake_summarizer, keep_recent=-1)
    with pytest.raises(ValueError):
        ContextManager(summarizer=fake_summarizer, strategy="nonsense")


def test_tool_pairing_preserved_after_compact():
    """端到端安全性:压缩后不出现孤儿 tool(直接对应你上一版踩的 API 报错)。"""
    cm = ContextManager(summarizer=fake_summarizer, threshold=100,
                        keep_recent=6, strategy="hybrid")
    messages = [
        sys_msg(),                    # 0
        user_msg("查A123和B456"),      # 1
        assistant_with_tools(2),      # 2  ← 父(点了两个工具)
        tool_msg("call_0"),           # 3
        tool_msg("call_1"),           # 4
        user_msg("谢谢"),              # 5
        assistant_msg("不客气"),       # 6
        user_msg("再查A123"),          # 7
        assistant_msg("好的"),         # 8
    ]
    result = cm.compact(messages, current_tokens=999)
    assert result.compacted is True
    assert_no_orphan_tool(result.messages)   # 保留区若含 tool,其父 assistant 必须也在


# ══════════════════════════════════════════════════════════════════════
#  免 pytest 的极简自跑入口
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
