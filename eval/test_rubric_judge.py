"""
门禁 · Rubric-based LLM-judge 测试 (eval/test_rubric_judge.py)

全 mock,不联网(judge 的 client 依赖注入 → 传假 client)。覆盖：
  ① veto 归一化：模型自相矛盾(veto=True 但 verdict=pass)→ 代码强制 fail
  ② 兜底 fail-closed：坏 JSON / 形状不对 → fail
  ③ 正常：干净 pass → pass
  ④ calibrate：在金标集上统计一致率(用固定假 judge,结果确定)
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from rubric_judge import GOLDEN_SET, calibrate, judge_reply


class FakeClient:
    """create() 固定返回构造时给的 content 字符串（模拟 judge 模型的输出）。"""

    def __init__(self, content: str):
        self.content = content
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))])


# --------------------------------------------------------------------------
# ① veto 归一化：模型说 veto=True 却给 verdict=pass → 必须被强制成 fail
# --------------------------------------------------------------------------
def test_veto_forces_fail_even_if_model_says_pass():
    client = FakeClient(json.dumps({
        "scores": {"忠实性": 4, "完整性": 4},
        "veto_triggered": True,      # veto 触发
        "veto_reason": "确认假前提",
        "verdict": "pass",           # 但模型自相矛盾地给了 pass
    }))
    result = judge_reply("q", "a", [], client)
    # veto 触发 → 代码强制 fail，不信模型自相矛盾的 pass
    assert result["verdict"] == "fail", f"Expected verdict to be 'fail' due to veto, but got {result['verdict']}"


# --------------------------------------------------------------------------
# ② 兜底 fail-closed：模型输出根本不是合法 JSON → 返回 fail，不抛异常
# --------------------------------------------------------------------------
def test_fallback_fail_closed_on_bad_json():
    client = FakeClient("这不是JSON{{{")
    result = judge_reply("q", "a", [], client)
    # 坏 JSON → 不抛异常，fail-closed 返回 fail
    assert result["verdict"] == "fail", f"Expected verdict to be 'fail' due to bad JSON, but got {result['verdict']}"


# --------------------------------------------------------------------------
# ③ 正常：干净的 pass → pass 原样返回
# --------------------------------------------------------------------------
def test_clean_pass():
    client = FakeClient(json.dumps({
        "scores": {"忠实性": 4, "完整性": 3},
        "veto_triggered": False,
        "veto_reason": "",
        "verdict": "pass",
    }))
    result = judge_reply("q", "a", [], client)
    # 干净 pass → 原样返回 pass
    assert result["verdict"] == "pass", f"Expected verdict to be 'pass', but got {result['verdict']}"


# --------------------------------------------------------------------------
# ④ calibrate：用「永远判 pass」的假 judge，一致率应 = 金标集里 human_verdict=pass 的比例
# --------------------------------------------------------------------------
def test_calibrate_counts_agreement():
    always_pass = FakeClient(json.dumps({
        "scores": {}, "veto_triggered": False, "veto_reason": "", "verdict": "pass",
    }))
    report = calibrate(always_pass)
    # 永远判 pass 的 judge，只会和"人类也判 pass"的案例一致 → agree = 金标集里 pass 的条数
    expected_total = len(GOLDEN_SET)
    expected_agree = sum(1 for item in GOLDEN_SET if item["human_verdict"] == "pass")
    assert report["total"] == expected_total, f"Expected total {expected_total}, but got {report['total']}"
    assert report["agree"] == expected_agree, f"Expected agree {expected_agree}, but got {report['agree']}"
