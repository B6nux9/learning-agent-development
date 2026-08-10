import logging
import random
import time
from enum import Enum

from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)


class Category(Enum):
    RETRYABLE = "retryable"        # 瞬时: 抖动/超时/5xx
    RATE_LIMITED = "rate_limited"  # 429: 可重试但必须等
    FATAL = "fatal"                # 4xx/未知: fail fast


def classify(exc: Exception) -> Category:
    """把 create() 抛出的异常分进三箱。
    规则：APIConnectionError(含 APITimeoutError) → RETRYABLE
          RateLimitError → RATE_LIMITED
          APIStatusError: status_code >= 500 → RETRYABLE，其余 → FATAL
          未知异常 → FATAL（宁可快挂，别对不认识的错瞎重试）
    """
    if isinstance(exc, (APIConnectionError, APITimeoutError)):
        return Category.RETRYABLE
    elif isinstance(exc, RateLimitError):
        return Category.RATE_LIMITED
    elif isinstance(exc, APIStatusError):
        if exc.status_code >= 500:
            return Category.RETRYABLE
        else:
            return Category.FATAL
    else:
        return Category.FATAL


def compute_backoff(attempt: int, *, base: float = 1.0, cap: float = 8.0) -> float:
    """第 attempt 次失败后，重试前该睡多少秒。full jitter 版（AWS 方案）。
    attempt: 第几次失败，从 0 开始（第一次失败后调用时 attempt=0）
    base:    退避基数（秒）
    cap:     单次等待上限（秒）——指数不能无限涨
    返回:    在 [0, min(cap, base * 2**attempt)] 区间内均匀随机取的一个数
    """
    return random.uniform(0, min(cap, base * 2**attempt))


def _retry_after_seconds(exc) -> float | None:
    """从 429 异常上提取服务端指令的等待秒数。

    取不到（无 response/无 header）或取不出合法数字（如 HTTP-date 格式、负数、乱写的值）
    一律返回 None，让调用方退回自己的退避——**别信外部输入**，哪怕它来自服务端。
    """
    try:
        raw = exc.response.headers.get("retry-after")
        if raw is None:
            return None
        wait = float(raw)
        return wait if wait >= 0 else None
    except (AttributeError, ValueError, TypeError):
        return None


def chat_with_retry(client, *, max_retries: int = 3,
                    deadline_s: float | None = None, **create_kwargs):
    """带重试的 chat.completions.create（v2：+deadline 预算 +Retry-After）。

    行为契约:
      - 成功 → 返回 response 原物
      - FATAL → 原样 re-raise（一层不吞、不包装，让上层看到真相）
      - RETRYABLE → full-jitter 退避后重试
      - RATE_LIMITED → 等待时长优先尊重服务端的 Retry-After 指令，取不到才退回退避
      - deadline_s: 总时间预算（秒）。None=不限（离线跑批）；对话路径传小值（如 8.0）。
        铁律: 睡之前先算账，已耗时 + 要睡的时长 > 预算 → 不睡，立刻 re-raise。
        （重试预算服从延迟预算：上界不是次数，是用户还愿意等的时间。）
      - max_retries 是"重试"次数，不含首次 → 总尝试 = 1 + max_retries
      - 耗尽/预算不够 → re-raise 最后一个异常（块 5 换成 LLMUnavailable）
    """
    start = time.monotonic()  # monotonic: 墙钟会被 NTP 回拨，单调钟只增不减
    for attempt in range(max_retries + 1):
        try:
            return client.chat.completions.create(**create_kwargs)
        except Exception as exc:
            category = classify(exc)
            if category is Category.FATAL:
                raise
            if attempt == max_retries:
                raise  # 耗尽判断在 sleep 之前：不白睡最后一觉

            if category is Category.RATE_LIMITED:
                wait = _retry_after_seconds(exc)
                if wait is None:
                    wait = compute_backoff(attempt)
            else:
                wait = compute_backoff(attempt)

            # 预算检查只写这一次，backoff 和 Retry-After 两种等待都从这里过
            elapsed = time.monotonic() - start
            if deadline_s is not None and elapsed + wait > deadline_s:
                logger.warning(
                    "chat_with_retry: 睡不起就别开始睡 wait=%.2fs elapsed=%.2fs deadline=%.2fs",
                    wait, elapsed, deadline_s,
                )
                raise

            logger.warning(
                "chat_with_retry: attempt=%d/%d, category=%s, wait=%.2fs",
                attempt + 1, max_retries + 1, category.value, wait,
            )
            time.sleep(wait)


if __name__ == "__main__":
    from types import SimpleNamespace

    import httpx
    import openai

    req = httpx.Request("POST", "https://x")

    def _status_exc(cls, code, headers=None):
        return cls("boom", response=httpx.Response(code, request=req, headers=headers), body=None)

    assert classify(openai.APIConnectionError(request=req)) is Category.RETRYABLE
    assert classify(_status_exc(openai.RateLimitError, 429)) is Category.RATE_LIMITED
    assert classify(_status_exc(openai.InternalServerError, 500)) is Category.RETRYABLE
    assert classify(_status_exc(openai.BadRequestError, 400)) is Category.FATAL
    assert classify(ValueError("??")) is Category.FATAL
    print("classify: 5/5 冒烟通过")

    # ---- chat_with_retry 冒烟：计数 fake，零网络零真睡 ----
    SENTINEL = object()  # 哨兵：object() 身份唯一，is 可证"拿回的就是 create 的原物"

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

    # 免真睡 + 记账：sleep 换成记录器，既不等待又能断言"睡了几次、每次多久"
    sleeps: list[float] = []
    _real_sleep = time.sleep
    time.sleep = sleeps.append
    try:
        # ① 两次抖动后成功 → 总调用 3，拿回原响应
        fake = FakeClient(2, lambda: openai.APIConnectionError(request=req))
        assert chat_with_retry(fake, model="m", messages=[]) is SENTINEL
        assert fake.calls == 3, f"期望 3 次调用，实际 {fake.calls}"

        # ② FATAL 一击即抛 → 总调用 1，异常原样透传
        fake = FakeClient(99, lambda: _status_exc(openai.BadRequestError, 400))
        try:
            chat_with_retry(fake, model="m", messages=[])
            raise AssertionError("BadRequest 应该抛出来")
        except openai.BadRequestError:
            pass
        assert fake.calls == 1, f"期望 1 次调用，实际 {fake.calls}"

        # ③ 全程失败 → 总调用 1 + max_retries，最后原样抛出
        fake = FakeClient(99, lambda: openai.APIConnectionError(request=req))
        try:
            chat_with_retry(fake, model="m", messages=[], max_retries=3)
            raise AssertionError("耗尽后应该抛出来")
        except openai.APIConnectionError:
            pass
        assert fake.calls == 4, f"期望 4 次调用，实际 {fake.calls}"

        # ④ 429 尊重 Retry-After → 两次等待都精确等于服务端指令的 20 秒
        sleeps.clear()
        fake = FakeClient(2, lambda: _status_exc(openai.RateLimitError, 429,
                                                 headers={"retry-after": "20"}))
        assert chat_with_retry(fake, model="m", messages=[]) is SENTINEL
        assert fake.calls == 3
        assert sleeps == [20.0, 20.0], f"应精确尊重服务端指令，实际 {sleeps}"

        # ⑤ 非法 Retry-After（"soon"）→ 退回 full-jitter 退避，落在各自区间内
        sleeps.clear()
        fake = FakeClient(2, lambda: _status_exc(openai.RateLimitError, 429,
                                                 headers={"retry-after": "soon"}))
        assert chat_with_retry(fake, model="m", messages=[]) is SENTINEL
        assert len(sleeps) == 2
        assert 0 <= sleeps[0] <= 1.0 and 0 <= sleeps[1] <= 2.0, f"应退回退避区间，实际 {sleeps}"

        # ⑥ 预算不够睡 → 不睡，立刻抛，总调用 1
        sleeps.clear()
        fake = FakeClient(99, lambda: _status_exc(openai.RateLimitError, 429,
                                                  headers={"retry-after": "20"}))
        try:
            chat_with_retry(fake, model="m", messages=[], deadline_s=5.0)
            raise AssertionError("预算不够应该立刻抛")
        except openai.RateLimitError:
            pass
        assert fake.calls == 1, f"期望 1 次调用，实际 {fake.calls}"
        assert sleeps == [], f"睡不起就别开始睡，实际睡了 {sleeps}"
    finally:
        time.sleep = _real_sleep  # 冒烟归冒烟，全局的东西借了要还

    print("chat_with_retry: 6/6 冒烟通过")
