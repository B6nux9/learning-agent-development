"""上下文管理模块 —— 【纯逻辑】,不碰 LLM、不碰网络、不碰文件。

═══════════════════════════════════════════════════════════════════════
这次作业真正要学的东西:不是"再写一遍压缩逻辑",而是【怎么把它写成能测的代码】。
═══════════════════════════════════════════════════════════════════════

三条生产规范,贯穿本文件:

1. 【纯逻辑与副作用分离】
   本模块【不发任何网络请求】。需要 LLM 的部分(生成摘要)通过【依赖注入】传进来。
   收益:压缩逻辑可以在【不调 LLM】的情况下完整测试 —— 快(毫秒级)、稳(不受模型
   随机性影响)、免费(不烧 token)。
   ⚠️ 这是最重要的一条。绝大多数人写 agent 代码测不了,就是因为把 LLM 调用和业务
   逻辑焊死在一起了。

2. 【不修改入参】
   compact() 返回【新列表】,绝不原地修改调用方传进来的 messages。
   原地修改是 Python 里最常见的隐蔽 bug 来源之一(调用方以为自己的数据没变)。

3. 【返回结果对象,而非裸值】
   compact() 返回 CompactResult(含"压没压、丢了几条、留了几条"),而不是只返回一个 list。
   调用方需要这些信息去打日志/上报指标 —— 这是 L13 可观测性的地基。

对照面试:蔚蓝 JD 明确要求"建立 Agent 任务的【评估与回归测试体系】"。
能讲清"我怎么让 agent 代码可测"是很强的加分项。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

# ── 类型别名:让签名自解释,也方便 IDE/类型检查 ──────────────────────────
Message = dict                              # {"role": str, "content": str|None, ...}
Summarizer = Callable[[list[Message]], str]  # 注入进来的"摘要器":一组消息 -> 一段摘要文本
Strategy = Literal["truncate", "summarize", "hybrid"]


@dataclass
class CompactResult:
    """压缩结果。带上足够的信息让调用方能记日志、报指标。"""
    messages: list[Message]      # 压缩后的新消息列表
    compacted: bool              # 这次到底压没压(没超阈值就没压)
    dropped_count: int = 0       # 被压掉(替换成摘要)的原始消息条数
    kept_count: int = 0          # 保留原文的消息条数
    summary: str | None = None   # 生成的摘要文本(便于调试/审计)


# ══════════════════════════════════════════════════════════════════════
#  TODO 1:找到"安全切点"—— 一个【纯函数】
# ══════════════════════════════════════════════════════════════════════
def find_safe_cut_index(messages: list[Message], keep_recent: int) -> int:
    """返回一个安全的切分下标 i,使得 messages[i:] 可以独立成为合法的消息序列。

    「安全」的含义:切完之后,不能出现【孤儿 tool 消息】——即一条 role="tool" 的消息,
    它对应的那条 assistant(带 tool_calls) 却被切走了。API 会因此报错。

    规则:
      - 下标 0 是 system 消息,永远保留,所以返回值最小是 1。
      - 先按 keep_recent 定一个初始切点,再往前退到安全位置。
      - 如果 messages 太短(不足以切),返回 len(messages) 表示"没什么可压的"。

    ⚠️ 这个函数是【纯函数】:同样输入必定同样输出,没有任何副作用,不碰网络。
       所以它能被单元测试彻底覆盖 —— 这正是把它单独拆出来的理由。

    要自己想清楚的边界情况(测试里都要覆盖):
      a. messages 只有 system 一条
      b. messages 比 keep_recent 还短
      c. 初始切点正好落在 tool 消息上(要往前退)
      d. 连续多条 tool 消息(一次 assistant 调了多个工具)
      e. 一路退到了 system 后面(退无可退)
    """
    # 你的代码:
    raise NotImplementedError("TODO 1: find_safe_cut_index")


# ══════════════════════════════════════════════════════════════════════
#  TODO 2:ContextManager —— 把策略、阈值、摘要器组装起来
# ══════════════════════════════════════════════════════════════════════
class ContextManager:
    """上下文管理器。

    用法:
        cm = ContextManager(summarizer=my_llm_summarizer, threshold=2000)
        result = cm.compact(messages, current_tokens=stats.last_prompt_tokens)
        messages = result.messages
    """

    def __init__(
        self,
        summarizer: Summarizer,
        threshold: int = 2000,
        keep_recent: int = 6,
        strategy: Strategy = "hybrid",
    ) -> None:
        """
        Args:
            summarizer: 【注入】的摘要器。测试时传一个假的,生产时传真调 LLM 的那个。
            threshold:  触发压缩的 token 阈值(用 API 实测的 prompt_tokens 判断)。
            keep_recent: 压缩时保留多少条最近的消息原文。
            strategy:   "truncate"=只截断不摘要 / "summarize"=全压成摘要 /
                        "hybrid"=最近N条原文+更早的摘要(默认,最常用)。
        """
        # TODO 2a:保存参数。顺便做参数校验——生产代码要对非法配置早失败(fail fast),
        #          而不是等运行时出诡异行为。比如 threshold <= 0、keep_recent < 0 应该直接报错。
        raise NotImplementedError("TODO 2a: __init__")

    def compact(self, messages: list[Message], current_tokens: int) -> CompactResult:
        """按阈值决定是否压缩,返回 CompactResult。

        要求:
          1. current_tokens <= threshold  → 不压,返回 compacted=False,
             messages 原样返回(但注意第 3 条)。
          2. 找不到可压的内容(见 TODO 1 的边界)→ 同样返回 compacted=False。
          3. 【绝不原地修改入参 messages】。需要新列表就构造新的。
          4. 按 self.strategy 分支:
             - "truncate":  不调 summarizer,直接丢掉旧消息(最省钱,但信息全丢)
             - "summarize": 全部旧消息压成摘要,不保留原文
             - "hybrid":    旧消息压成摘要 + 保留最近 keep_recent 条原文
          5. 摘要以 role="system" 的消息插在 system 之后
             (L5 Q4 学过:背景信息该用 system 角色)。

        Args:
            current_tokens: 当前上下文的【实测】token 数(来自 API 的 usage.prompt_tokens)。
                            注意这里是【传进来】的,不是自己算的 —— 又一次依赖注入:
                            本模块不关心 token 怎么数出来的,那是调用方的事。
        """
        # 你的代码:
        raise NotImplementedError("TODO 2b: compact")
