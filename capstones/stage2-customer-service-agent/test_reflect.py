"""
门禁第二条 · reflect() 单测 (test_reflect.py)

复用 L10 的可测性核心功：reflect 的 client 是**依赖注入**的 → 测试传一个假 client，
零网络（「拔网线还能过」）。这里不 monkeypatch，直接把假 client 当参数喂进去——
比 test_policy 换接缝还干净，正是「依赖注入 > 内部构造」的回报。

覆盖三条：
  ① accept（正）：judge 判合格 → reflect 原样返回 accept。
  ② revise（反）：judge 判不合格 → reflect 透传 verdict + critique。
  ③ fail-open（兜底）：judge 调用炸了 → reflect 不抛异常，默认 accept（质量层不拖垮 agent）。
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from reflect import reflect


# --------------------------------------------------------------------------
# 假 client —— 模仿 openai client 的调用链：
#   client.chat.completions.create(...).choices[0].message.content
# 你要让 FakeClient 的 create() 返回一个「长得像真 response」的对象，
# 其 .choices[0].message.content == 你预设的那段 JSON 字符串。
# 提示：SimpleNamespace 可以快速拼出 .choices[0].message.content 这种嵌套属性。
# --------------------------------------------------------------------------
class FakeClient:
    """构造时传入 judge「要吐出的 content 字符串」；create() 就固定返回它。
    若构造时 raise_on_call=True，则 create() 抛异常（模拟模型宕机）。"""

    def __init__(self, content: str = "", raise_on_call: bool = False):
        # 搭出 client.chat.completions.create(...) 这条嵌套调用链，reflect 才调得到。
        self.content = content
        self.raise_on_call = raise_on_call
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, *args, **kwargs):
        # raise_on_call=True 模拟模型宕机；否则返回 response.choices[0].message.content == self.content
        if self.raise_on_call:
            raise RuntimeError("模型宕机")
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


# --------------------------------------------------------------------------
# ① 正：judge accept → reflect 返回 accept
# --------------------------------------------------------------------------
def test_reflect_accept():
    client = FakeClient(json.dumps({"verdict": "accept", "critique": ""}))
    result = reflect("user message", "draft reply", [], client)
    assert result["verdict"] == "accept"


# --------------------------------------------------------------------------
# ② 反：judge revise → reflect 透传 verdict + critique
# --------------------------------------------------------------------------
def test_reflect_revise_passes_critique():
    client = FakeClient(json.dumps({"verdict": "revise", "critique": "命中红线1：泄露了归属"}))
    result = reflect("user message", "draft reply", [], client)
    assert result["verdict"] == "revise"
    assert "红线1" in result["critique"]    


# --------------------------------------------------------------------------
# ③ 兜底：judge 调用炸了 → fail-open 返回 accept（不抛异常）
#    这条把我们讨论的「模型宕机该 fail-open」用测试锁死，防以后有人改回 fail-closed。
# --------------------------------------------------------------------------
def test_reflect_fail_open_on_error():
    client = FakeClient(raise_on_call=True)
    result = reflect("user message", "draft reply", [], client)
    assert result["verdict"] == "accept"
