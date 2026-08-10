from types import SimpleNamespace

import httpx
import openai
import pytest

from llm_client import (Category, LLMUnavailable, chat_with_retry, classify,
                        compute_backoff)

REQ = httpx.Request("POST", "https://x")
# 哨兵自带 usage：is 验身份 + 顺手验 token 提取（SimpleNamespace 实例身份唯一）
SENTINEL = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5))


def _status_exc(cls, code, headers=None):
    return cls("boom", response=httpx.Response(code, request=REQ, headers=headers), body=None)


class FakeClient:
    """前 fail_times 次 create 抛 exc_factory()，之后返回 SENTINEL；全程计数。"""

    def __init__(self, fail_times, exc_factory):
        self.calls = 0
        self._fail_times = fail_times
        self._exc_factory = exc_factory
        # 拼出 client.chat.completions.create 这条属性链（capstone reflect 测试同款手法）
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls += 1
        if self.calls <= self._fail_times:
            raise self._exc_factory()
        return SENTINEL


@pytest.fixture
def sleeps(monkeypatch):
    """把 time.sleep 换成记录器；monkeypatch 在测试结束后自动还原。"""
    recorded = []
    monkeypatch.setattr("time.sleep", recorded.append)
    return recorded


# ---------- classify ----------

@pytest.mark.parametrize("exc_factory, expected", [
    (lambda: openai.APIConnectionError(request=REQ), Category.RETRYABLE),
    (lambda: _status_exc(openai.RateLimitError, 429), Category.RATE_LIMITED),
    (lambda: _status_exc(openai.InternalServerError, 500), Category.RETRYABLE),
    (lambda: _status_exc(openai.BadRequestError, 400), Category.FATAL),
    (lambda: ValueError("??"), Category.FATAL),
])
def test_classify(exc_factory, expected):
    assert classify(exc_factory()) is expected


def test_compute_backoff_bounds():
    # 下界是 0（full jitter 特意允许超早重试），上界先指数涨、后被 cap 兜住。
    # 随机函数的边界断言必须精确，宁可多抽样——错的下界(如 0.1)= ~10% 概率的 flaky test。
    for attempt, ceiling in [(0, 1.0), (1, 2.0), (3, 8.0), (10, 8.0)]:
        for _ in range(20):
            assert 0 <= compute_backoff(attempt) <= ceiling


# ---------- chat_with_retry ----------

def test_retry_then_success(sleeps):
    fake = FakeClient(2, lambda: openai.APIConnectionError(request=REQ))
    resp, m = chat_with_retry(fake, model="m", messages=[])
    assert resp is SENTINEL
    assert fake.calls == 3                       # 2 败 1 胜
    assert len(sleeps) == 2                      # 每败睡一次
    assert (m.attempts, m.outcome) == (3, "ok")
    assert (m.prompt_tokens, m.completion_tokens) == (10, 5)


def test_fatal_passes_through(sleeps):
    fake = FakeClient(99, lambda: _status_exc(openai.BadRequestError, 400))
    with pytest.raises(openai.BadRequestError):   # 原样透传，不翻译成 LLMUnavailable
        chat_with_retry(fake, model="m", messages=[])
    assert fake.calls == 1                        # 一击即抛
    assert sleeps == []                           # 更不会睡


def test_exhausted_raises_translated(sleeps):
    fake = FakeClient(99, lambda: openai.APIConnectionError(request=REQ))
    with pytest.raises(LLMUnavailable) as excinfo:
        chat_with_retry(fake, model="m", messages=[], max_retries=3)
    assert fake.calls == 4                        # 1 + max_retries
    # 翻译异常但不销毁证据：from exc 把元凶挂在 __cause__
    assert isinstance(excinfo.value.__cause__, openai.APIConnectionError)
    m = excinfo.value.metrics                     # 失败也要记账
    assert (m.attempts, m.outcome) == (4, "gave_up")


def test_429_respects_retry_after(sleeps):
    fake = FakeClient(2, lambda: _status_exc(openai.RateLimitError, 429,
                                             headers={"retry-after": "20"}))
    resp, _ = chat_with_retry(fake, model="m", messages=[])
    assert resp is SENTINEL
    assert sleeps == [20.0, 20.0]                 # 精确尊重服务端指令


def test_bad_retry_after_falls_back(sleeps):
    fake = FakeClient(2, lambda: _status_exc(openai.RateLimitError, 429,
                                             headers={"retry-after": "soon"}))
    resp, _ = chat_with_retry(fake, model="m", messages=[])
    assert resp is SENTINEL
    assert len(sleeps) == 2
    assert 0 <= sleeps[0] <= 1.0 and 0 <= sleeps[1] <= 2.0   # 退回 full-jitter 区间


def test_deadline_refuses_to_sleep(sleeps):
    fake = FakeClient(99, lambda: _status_exc(openai.RateLimitError, 429,
                                              headers={"retry-after": "20"}))
    with pytest.raises(LLMUnavailable) as excinfo:
        chat_with_retry(fake, model="m", messages=[], deadline_s=5.0)
    assert fake.calls == 1                        # 首枪永远值得打
    assert sleeps == []                           # 睡不起就别开始睡
    assert (excinfo.value.metrics.attempts, excinfo.value.metrics.outcome) == (1, "gave_up")


def test_kwarg_typo_is_swallowed_by_create_kwargs(sleeps):
    """记录一个真坑（今天现场撞的）：参数名拼错(deadline≠deadline_s)不会报错——
    被 **create_kwargs 静默吞掉透传给 create()，预算等于没设。
    这条测试是"行为文档"：**kwargs 透传的包装函数天生吞 typo，改约定前它就该这么表现。"""
    fake = FakeClient(1, lambda: _status_exc(openai.RateLimitError, 429,
                                             headers={"retry-after": "20"}))
    resp, _ = chat_with_retry(fake, model="m", messages=[], deadline=0.01)  # 拼错的参数名
    assert resp is SENTINEL
    assert sleeps == [20.0]                       # "预算"没拦住它：真睡了 20 秒
