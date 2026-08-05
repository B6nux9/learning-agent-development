"""
L11 Capstone · 多 Agent 代码审查系统 (multi_agent_review.py)

架构 = 管理者模式(Orchestration) + 不共享上下文(每个 reviewer 独立进程/上下文)：

    用户给一段代码
         │
     Manager.review()  ──并行分派(各自隔离上下文)──┐
         │                                          │
    ┌────┴─────┬───────────────┬───────────────┐   │
    ▼          ▼               ▼               ▼   │
 static_review llm_review(安全) llm_review(正确性) ...  ← reviewers
 (工具:pyflakes  (LLM lens,     (LLM lens,
  执行/静态反馈✅) 弱:无新信息)   弱:无新信息)
    └────┴─────┴───────────────┴───────────────┘
         │
     synthesize()  去重/排序/防级联错误(§4)→ 一份报告

【判据落地(Ch10 §3)】多个同模型 reviewer 读同一段代码=不引入新信息=通常无效。
  本系统价值来自 **static_review**——它带真实工具反馈(pyflakes 抓未定义名/未用 import)，
  这是 LLM 读代码时拿不到的 ground-truth。LLM lens 保留作对比，让你亲眼看差距。

【隔离落地】每个 reviewer 各起独立 messages/上下文，互不看对方输出（进程，非线程）。
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


# 统一的 finding 形状（各 reviewer 都返回 list[Finding]）：
#   {"source": str, "line": int | None, "message": str}
#   source 标明是谁报的(pyflakes / llm:安全 / llm:正确性)——汇总时要用它区分工具证据 vs LLM 意见。


# --------------------------------------------------------------------------
# block 1  static_review —— 工具型 reviewer（跑 pyflakes，带真实静态反馈）
# 这是整个系统里唯一"引入新信息"的 reviewer，也是最该先盖、且能不联网独立测的一块。
# --------------------------------------------------------------------------
def static_review(code: str) -> list[dict]:
    """对一段 Python 源码跑 pyflakes，返回结构化 findings。

    接口契约（coach 给；函数体你写）：
      输入：code: str —— 待审的 Python 源码
      输出：list[dict]，每个 = {"source": "pyflakes", "line": int|None, "message": str}
            没问题就返回 []
      要做：
        1. 把 code 写进一个临时 .py 文件（tempfile.NamedTemporaryFile，encoding='utf-8'）。
        2. 跑 subprocess.run([sys.executable, "-m", "pyflakes", 临时路径], capture_output=True, text=True)。
           ⚠️ **必须用 sys.executable，不是裸 "python"** —— 否则可能跑到没装 pyflakes 的别的解释器
              （你刚踩过这个"哪个 python"的坑）。
        3. pyflakes 每行输出形如  <path>:<line>:<col>: <message>。逐行解析成 finding：
           - 把 <path> 那段去掉，取出 line 号(int) 和 message。
           - 解析不出行号的行，line 设 None、整行当 message（别让格式意外把函数搞崩）。
        4. **临时文件用完要删**（os.unlink），别泄露临时文件——想想放哪能保证删（面试追问）。
      约束：stdout 和 stderr 都要看（pyflakes 语法错误走 stderr）。
    """
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pyflakes", tmp_path],
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
    finally:
        os.unlink(tmp_path)

    findings = []
    for raw in output.splitlines():
        if not raw.strip():
            continue
        # 已知的 tmp_path 别参与解析：先把它(和分隔冒号)从行首剥掉，
        # 剩下的才是真正未知的 <line>:<col>: <message>——绕开盘符 C: 的冒号。
        if raw.startswith(tmp_path):
            rest = raw[len(tmp_path):].lstrip(":")
            parts = rest.split(":", 2)  # [line, col, message]
            try:
                line_number = int(parts[0])
                message = parts[2].strip() if len(parts) > 2 else rest.strip()
                findings.append({"source": "pyflakes", "line": line_number, "message": message})
                continue
            except (ValueError, IndexError):
                pass
        # 不以已知路径开头、或行号解析不出(如语法错的源码回显/^ 标记行)：整行兜底
        findings.append({"source": "pyflakes", "line": None, "message": raw.strip()})

    return findings

# --------------------------------------------------------------------------
# block 2  llm_review —— LLM lens reviewer（下一步写，先留契约）
# --------------------------------------------------------------------------
# 每个 lens = 一个独立"身份"的 reviewer（不同 system prompt = 不同 Agent）
LENS_PROMPTS = {
    "安全": "你是代码安全审查员。只找安全问题（注入/越权/密钥硬编码/危险调用等）。",
    "正确性": "你是代码正确性审查员。只找逻辑错误、边界遗漏、异常处理缺失。",
}

# 输出契约 —— 必须和下面 parser 的 data.get("findings", []) 严格对齐（同一契约的两处）。
# 关键：① 是数组(一个 reviewer 可报多条) ② 每条只要 line+message，**不要 source**
#       (source 由代码按 lens 标注，不信模型——它上次把 source 填成了函数名)。
FORMAT_INSTRUCTION = (
    '只输出 JSON，形如：{"findings": [{"line": 行号整数或null, "message": "问题描述"}]}。'
    '发现多个问题就在数组里放多条；没发现就输出 {"findings": []}。不要输出 source 字段。'
)


def llm_review(code: str, lens: str, client) -> list[dict]:
    """用某个"视角(lens)"让 LLM 审代码。

    接口契约（函数体你写）：
      输入：code、lens（"安全"/"正确性"，用 LENS_PROMPTS 取对应身份）、client（依赖注入，可 mock）
      输出：list[dict]，每个 = {"source": f"llm:{lens}", "line": int|None, "message": str}
      要做：
        1. **隔离**（本 block 的考点）：messages 只起**全新的一段** ——
           [{"role":"system", ...lens 身份 + 输出格式要求...}, {"role":"user", "content": code}]。
           **绝不接收/拼接别的 reviewer 或 Manager 的历史**。这就是"进程"式隔离。
        2. 让模型输出 JSON（response_format={"type":"json_object"}，temperature=0）。
           约定一个形状，比如 {"findings":[{"line":int|null,"message":str}, ...]}。
        3. 解析：给每条补上 source=f"llm:{lens}"，返回 list。
        4. **兜底**：解析失败 / 模型抽风 → 返回 []（一个 reviewer 挂了不该拖垮整个审查，
           回扣 reflect 的 fail-open；但这里返回空列表而非 accept）。
      想清楚（写完答我）：为什么每个 lens 必须"全新起一段"，而不是所有 lens 共用一段对话历史？
                          （用 Ch10 §1 的"隔离/进程"和"防 anchoring"回答）
    """
    messages = [
        {"role": "system", "content": LENS_PROMPTS[lens] + FORMAT_INSTRUCTION},
        {"role": "user", "content": code},
    ]
    try:
        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
        findings = data.get("findings", [])
        for f in findings:
            f["source"] = f"llm:{lens}"
        return findings
    except Exception:
        logger.warning("llm_review(%s) failed", lens, exc_info=True)
        return []  # fail-open: 一个 lens 挂了不拖垮整个审查
# --------------------------------------------------------------------------
# block 3-A  synthesize —— 汇总(纯逻辑，先写、能不联网测)
# --------------------------------------------------------------------------
def synthesize(findings: list[dict]) -> dict:
    """把所有 reviewer 的 findings 去重 + 排序，组装成报告。

    接口契约（函数体你写）：
      输入：findings: list[dict]，各 reviewer 混在一起的原始结果（每个 = {source, line, message}）
      输出：dict 报告，形如
            {"count": 去重后条数, "findings": [排序后的 findings]}
      要做：
        1. **去重**：同一个问题可能被多个 reviewer 报（或同一 reviewer 报重）。
           用什么当"同一条"的 key？—— 想一个（提示：(line, message) 或含 source？先想清楚再定）。
        2. **排序（§4 防级联的落地）**：**工具证据(source == "pyflakes")排在 LLM 意见前面**。
           为什么？pyflakes 是确定性 ground-truth，LLM 是概率意见——别让一堆 LLM 意见淹没确定的事实。
           （同类内部可再按 line 排，None 行号放最后。）
        3. 返回 {"count": ..., "findings": ...}。
      纯函数：不碰网络、不调 LLM —— 所以它能被单测直接喂假 findings 验证。
    """
    unique_findings = {}
    for f in findings:
        key = (f["line"], f["message"])
        if key not in unique_findings:
            unique_findings[key] = f

    sorted_findings = sorted(
        unique_findings.values(),
        key=lambda f: (f["source"] != "pyflakes", f["line"] if f["line"] is not None else float("inf")),
    )

    return {"count": len(sorted_findings), "findings": sorted_findings}


# --------------------------------------------------------------------------
# block 3-B  review —— Manager：并行分派(隔离) + 汇总
# --------------------------------------------------------------------------
def review(code: str, client, lenses: list[str] | None = None) -> dict:
    """Manager：并行跑所有 reviewer（各自隔离上下文），汇总成一份报告。

    接口契约（函数体你写）：
      输入：code、client（传给 llm_review）、lenses（默认 ["安全","正确性"]）
      输出：synthesize(...) 的报告 dict
      要做：
        1. 组装任务列表（每个任务是"调用某个 reviewer"）：
           - 1 个 static_review(code)   —— 注意它**不要 client**
           - 每个 lens 一个 llm_review(code, lens, client)
        2. 用 ThreadPoolExecutor 并行跑（骨架见上面讲解）：
             with ThreadPoolExecutor() as ex:
                 futures = [ex.submit(...), ...]
                 每个 future.result() 拿回一个 list[dict]
        3. 把所有 reviewer 的 list **拍平成一个大 list**（每个 reviewer 返回的是 list，你要 flatten）。
        4. 交给 synthesize，return 它的报告。
      自查（老短板）：static_review 和 llm_review 的**参数不一样**（一个没 client）——
        别用同一种方式 submit，想清楚每个任务怎么 submit。
    """
    if lenses is None:
        lenses = ["安全", "正确性"]

    tasks = [("static_review", static_review, (code,))] + [
        (f"llm_review:{lens}", llm_review, (code, lens, client)) for lens in lenses
    ]

    all_findings = []
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(func, *args): name for name, func, args in tasks}
        for future in futures:
            try:
                findings = future.result()
                all_findings.extend(findings)
            except Exception:
                logger.warning("%s failed", futures[future], exc_info=True)

    return synthesize(all_findings)