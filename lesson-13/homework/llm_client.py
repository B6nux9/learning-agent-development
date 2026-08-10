import logging
import random
import time
from dataclasses import dataclass
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

    取不到（无 response/无 header）或取不出合法数字（HTTP-date 格式、乱写的值、负数）
    一律返回 None，让调用方退回自己的退避——别信外部输入，哪怕它来自服务端。
    """
    try:
        raw = exc.response.headers.get("retry-after")
        if raw is None:
            return None
        wait = float(raw)
        return wait if wait >= 0 else None
    except (AttributeError, ValueError, TypeError):
        return None


@dataclass
class CallMetrics:
    """一次逻辑调用的账本，喂给可观测层（§2）。"""
    attempts: int                  # 实际发生的尝试数（含首次）
    latency_s: float               # 全程墙钟耗时，含重试等待
    prompt_tokens: int | None      # 成功时从 response.usage 取；拿不到为 None
    completion_tokens: int | None
    outcome: str                   # "ok" | "gave_up"


class LLMUnavailable(Exception):
    """重试/预算耗尽后的统一信号。上层(agent)捕它走降级：硬编码话术 + 转人工。

    这层的意义是翻译：上层从此不需要认识 openai 的异常家族。
    但 FATAL(4xx) 不翻译、原样透传——400 是我们自己的 bug，把它包装成
    "服务不可用"会把"该修代码的问题"伪装成"该等待的问题"：上层会安抚用户、
    稍后重试，而工程师永远收不到那声该炸的响。bug 要炸给人看，不是兜给用户。
    携带 metrics：失败也要记账，否则可观测层看不见最贵的那些调用。
    """

    def __init__(self, message: str, metrics: CallMetrics | None = None):
        super().__init__(message)
        self.metrics = metrics


def chat_with_retry(client, *, max_retries: int = 3,
                    deadline_s: float | None = None, **create_kwargs):
    """带重试的 chat.completions.create（v3：+CallMetrics +LLMUnavailable）。

    行为契约:
      - 成功 → 返回 (response, CallMetrics(outcome="ok"))
      - FATAL → 原样 re-raise（不翻译，理由见 LLMUnavailable docstring）
      - RETRYABLE → full-jitter 退避后重试
      - RATE_LIMITED → 等待时长优先尊重服务端 Retry-After 指令，取不到才退回退避
      - deadline_s: 总时间预算（秒）。None=不限（离线跑批）；对话路径传小值（如 8.0）。
        铁律: 睡之前先算账，已耗时 + 要睡的 > 预算 → 不睡，立刻放弃。
        （重试预算服从延迟预算。deadline 只裁决"等待"；请求本身的卡死
         归 client 的 timeout 管——构造时 OpenAI(max_retries=0, timeout=8.0)，
         内层重试必须缴械，重试策略只在本层这一个属主。）
      - 耗尽/预算不够 → raise LLMUnavailable(metrics 随身) from 原异常
    """
    start = time.monotonic()  # monotonic: 墙钟会被 NTP 回拨，单调钟只增不减

    def _metrics(attempts: int, outcome: str, response=None) -> CallMetrics:
        usage = getattr(response, "usage", None)  # 防御: 200 也可能长得不标准（D 箱教训）
        return CallMetrics(
            attempts=attempts,
            latency_s=time.monotonic() - start,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            outcome=outcome,
        )

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(**create_kwargs)
        except Exception as exc:
            category = classify(exc)
            if category is Category.FATAL:
                raise
            if attempt == max_retries:  # 耗尽判断在 sleep 之前：不白睡最后一觉
                raise LLMUnavailable(
                    f"重试耗尽: {attempt + 1} 次尝试全部失败",
                    _metrics(attempt + 1, "gave_up"),
                ) from exc

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
                raise LLMUnavailable(
                    f"预算不够: 还需等 {wait:.2f}s 但预算只剩 {deadline_s - elapsed:.2f}s",
                    _metrics(attempt + 1, "gave_up"),
                ) from exc

            logger.warning(
                "chat_with_retry: attempt=%d/%d, category=%s, wait=%.2fs",
                attempt + 1, max_retries + 1, category.value, wait,
            )
            time.sleep(wait)
        else:
            return response, _metrics(attempt + 1, "ok", response)
