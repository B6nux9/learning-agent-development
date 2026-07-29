"""
阶段二 Capstone · 政策 RAG 单元测试 (test_policy.py)

本文件第一次用「测试替身 / mock」——因为 search_policy 碰网络（embedding + 生成）。
核心思想：**只测你的逻辑（阈值闸的分支），不测 OpenAI/DeepSeek 的质量。**
所以把三个「别人的活」换成你手捏的假货，喂一个你指定的距离，只看 if 分支走对没走对。

三个要换掉的接缝（seam）：
  - _embed(...)          → 返回一个假向量（不打 OpenAI）
  - _get_collection()    → 返回一个假 collection，它的 .query() 距离由你说了算（控制点！）
  - _grounded_answer(...) → 返回一句固定假答案（不打 DeepSeek）

换的手法 = pytest 的 monkeypatch fixture：测试期间临时替换，测完自动还原。

跑法：
    uv run pytest capstones/stage2-customer-service-agent/test_policy.py -v
"""

from __future__ import annotations

import pytest

import policy_rag


# ===========================================================================
# 假 collection（我给你）——一个只会按你给的距离/文档回答 .query() 的替身。
# 结构照真实 res：距离/文档都是双层 list（还记得 res["distances"][0][0] 吗）。
# ===========================================================================
class _FakeCollection:
    def __init__(self, distance: float, doc: str):
        self._distance = distance
        self._doc = doc

    def query(self, query_embeddings, n_results):
        # 忽略入参，永远返回你构造好的 res
        return {"distances": [[self._distance]], "documents": [[self._doc]]}


def _patch_seams(monkeypatch, *, distance: float, doc: str = "退货政策：签收后 7 天内无理由退货。"):
    """把三个接缝一次性换成假货。distance 是你要测的那个「检索距离」。"""
    monkeypatch.setattr(policy_rag, "_embed", lambda texts: [[0.0]])            # 假向量
    monkeypatch.setattr(policy_rag, "_get_collection", lambda: _FakeCollection(distance, doc))  # 假库
    monkeypatch.setattr(policy_rag, "_grounded_answer", lambda q, chunks: "FAKE_ANSWER")        # 假生成


# ===========================================================================
# 正例 —— 我给你写全当模板：距离 < 阈值 → 放行生成
# ===========================================================================
def test_search_policy_covered_returns_answer(monkeypatch):
    # Arrange：距离 0.5 < 阈值 0.9 → 应判「覆盖」，走生成分支
    _patch_seams(monkeypatch, distance=0.5)
    # Act
    result = policy_rag.search_policy("怎么退货")
    # Assert：ok=True，且 answer 是被 _grounded_answer（假货）生成的那句
    assert result["ok"] is True
    assert result["answer"] == "FAKE_ANSWER"


# ===========================================================================
# 反例① —— 你来写：距离 > 阈值 → not_covered，不生成
# ===========================================================================
def test_search_policy_not_covered_escalates(monkeypatch):
    """契约：距离 1.5 > 阈值 0.9 → 返回 {"ok": False, "reason": "not_covered"}。
    照上面模板：先 _patch_seams(distance=1.5)，再调 search_policy，再断言 ok / reason。
    """
    # TODO(你来写): Arrange 用 distance=1.5；Act 调 search_policy；Assert ok=False + reason
    _patch_seams(monkeypatch, distance=1.5)
    result = policy_rag.search_policy("你们这周有什么活动")
    assert result["ok"] is False
    assert result["reason"] == "not_covered"


# ===========================================================================
# 反例② —— 你来写（进阶：行为验证，不只看返回值）
# 目标：没覆盖时**根本不该调用 _grounded_answer**（省一次 LLM 调用/省钱）。
# 手法：把 _grounded_answer 换成「一被调用就炸」的假货；如果分支写错真去调它，测试就红。
# ===========================================================================
def test_search_policy_not_covered_skips_generation(monkeypatch):
    """契约：not_covered 分支绝不能调 _grounded_answer。
    提示：
      - _embed / _get_collection 照常 patch（distance 用 > 阈值，如 1.5）。
      - 但 _grounded_answer 换成一个会 raise 的函数：
            def _boom(q, chunks):
                raise AssertionError("not_covered 时不该调用 _grounded_answer")
        用 monkeypatch.setattr 把它装上。
      - 然后调 search_policy；只要没炸、且 reason == not_covered，就说明分支没误入生成。
    """
    # TODO(你来写): 装 _boom，patch 另外两个接缝，调 search_policy，断言 not_covered
    def _boom(q, chunks):
        raise AssertionError("not_covered 时不该调用 _grounded_answer")
    _patch_seams(monkeypatch, distance=1.5)
    monkeypatch.setattr(policy_rag, "_grounded_answer", _boom)
    monkeypatch.setattr(policy_rag, "_get_collection", lambda: _FakeCollection(1.5, "假文档"))
    monkeypatch.setattr(policy_rag, "_embed", lambda texts: [[0.0]])
    result = policy_rag.search_policy("你们这周有什么活动")
    assert result["ok"] is False
    assert result["reason"] == "not_covered"
