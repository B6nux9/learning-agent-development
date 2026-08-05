"""
门禁 · 多 Agent 代码审查系统测试 (test_multi_agent_review.py)

三块可测性递进：
  ① synthesize   —— 纯逻辑，直接喂假 findings（零依赖）。
  ② static_review —— 确定性(跑真 pyflakes，本地无网络)。
  ③ 隔离性 + review —— 用 SpyClient(记录每个 reviewer 收到的 messages)，
     **验证每个 llm reviewer 都拿到全新隔离上下文**——这是本课的招牌性质。
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from multi_agent_review import review, static_review, synthesize


# --------------------------------------------------------------------------
# SpyClient：假 client——① 记录每次 create 收到的 messages（验隔离用）
#                        ② 返回一条固定 finding（不碰网络）
# --------------------------------------------------------------------------
class SpyClient:
    def __init__(self):
        self.calls: list[list[dict]] = []  # 每个元素 = 一次 create 收到的 messages
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, *, messages, **kwargs):
        self.calls.append(messages)
        content = json.dumps({"findings": [{"line": 1, "message": "spy 报的问题"}]})
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


# --------------------------------------------------------------------------
# ① synthesize：去重 + 工具优先排序（纯逻辑）
# --------------------------------------------------------------------------
def test_synthesize_dedup_and_tool_first():
    findings = [
        {"source": "llm:正确性", "line": 5, "message": "除零"},
        {"source": "pyflakes", "line": 1, "message": "os 未用"},
        {"source": "pyflakes", "line": 1, "message": "os 未用"},  # 重复
    ]
    report = synthesize(findings)
    # 去重(3→2) + 工具证据排最前
    assert report["count"] == 2
    assert report["findings"][0]["source"] == "pyflakes"


# --------------------------------------------------------------------------
# ② static_review：确定性抓到 planted bug（跑真 pyflakes，无网络）
# --------------------------------------------------------------------------
def test_static_review_catches_undefined_and_unused():
    findings = static_review("import os\ndef f():\n    return y\n")
    # 断言对着 pyflakes 的真实英文输出（不是我以为它该说的中文）
    finding_messages = ", ".join(f["message"] for f in findings)
    assert "unused" in finding_messages
    assert "undefined" in finding_messages


# --------------------------------------------------------------------------
# ③ 隔离性（招牌测试）：每个 llm reviewer 都拿到全新的 [system, user] 上下文
# --------------------------------------------------------------------------
def test_reviewers_get_isolated_context():
    spy = SpyClient()
    review("def f(): pass\n", spy, lenses=["安全", "正确性"])
    # 隔离验证：2 次 llm 调用，每次都是干净的 [system, user]，且不含别的 reviewer 的输出
    assert len(spy.calls) == 2
    for messages in spy.calls:
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        message_text = json.dumps(messages)
        assert "spy 报的问题" not in message_text


# --------------------------------------------------------------------------
# ④ review：一个 reviewer 挂了不拖垮整体（fail-open），仍出报告
# --------------------------------------------------------------------------
def test_review_survives_one_reviewer_failing():
    class BoomClient:
        def __init__(self):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._boom))

        def _boom(self, **kwargs):
            raise RuntimeError("模型宕机")

    report = review("import os\n", BoomClient(), lenses=["安全"])
    # LLM 全挂，但 pyflakes 照常 → 报告仍有工具发现（fail-open）
    assert report["count"] >= 1
    assert any(f["source"] == "pyflakes" for f in report["findings"])
