"""
RAG 评估运行器 —— 把评估集喂给 L7 的 RAG,自动打分,输出分类打分卡。

设计(生产级评估的最小骨架,一直养到 capstone/L12):
  - 评估集与被测系统解耦:cases 是数据(rag_eval_set.json),这里 import 被测的 rag 模块跑。
  - 评分【确定、免费、可复现】:关键词/子串匹配,不用 LLM 当裁判(L12 再升级 LLM-as-judge)。
  - 四类分别统计:normal / unanswerable / out_of_scope / adversarial —— 看清是哪类在崩。
  - 两条正交指标:①检索命中(retrieval)②答案正确(answer)。检索对但答案错 = grounding 问题;
    检索就没命中 = chunking/embedding 问题。分开看才知道该修哪。

跑法:
    uv run python eval/run_rag_eval.py
  (会对每条用例真调 embedding + 生成,约 40 次 API 调用,花很少的钱——评估本来就要花钱。)
"""

import os
import sys
import json
from dataclasses import dataclass, field

# —— 把被测系统(L7 的 rag.py)加进 import 路径,然后复用它的函数 ——
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lesson-07", "homework"))
import rag  # noqa: E402  (被测系统:chunk_by_heading / build_index / retrieve / rag_answer)

# 拒答标志:答案里出现任一即视为"拒答/转人工"
REFUSAL_MARKERS = ["暂无", "无法", "抱歉", "转人工", "联系人工", "不能", "没有相关", "无权", "不便"]


def _norm(s: str) -> str:
    """去掉所有空白再比较 —— 修掉"7 天"vs"7天"这类假阴性。
    (但这治标不治本:同义词/改写/确认vs否认 它还是分不清,那要 L12 的 LLM-as-judge。)"""
    return "".join(s.split())


@dataclass
class CaseResult:
    id: str
    category: str
    question: str
    retrieval_ok: bool | None   # None = 该用例不考检索(拒答类)
    answer_ok: bool
    answer: str
    reason: str = ""            # 失败原因,便于排查


def judge(case: dict, retrieved: list[str], answer: str) -> CaseResult:
    """对单条用例打分。返回 CaseResult。"""
    cat, q = case["category"], case["question"]
    must_not = case.get("must_not_contain", [])
    ans_n = _norm(answer)

    # 硬红线:答案不得包含 must_not_contain(假前提被确认 / 泄露 system prompt / 越权执行)
    violated = [s for s in must_not if _norm(s) in ans_n]
    if violated:
        return CaseResult(case["id"], cat, q, None, False, answer,
                          reason=f"命中禁止内容: {violated}")

    if case["should_refuse"]:
        # 拒答类:答案应含拒答标志;不考检索(库里本来就没有)
        ok = any(m in answer for m in REFUSAL_MARKERS)
        return CaseResult(case["id"], cat, q, None, ok, answer,
                          reason="" if ok else "应拒答但没拒答(可能瞎编)")

    # 可答类:①检索命中 expected_source ②答案含全部 expected_points
    src = case.get("expected_source")
    retrieval_ok = (src is not None) and any(_norm(src) in _norm(doc) for doc in retrieved)
    missing = [p for p in case.get("expected_points", []) if _norm(p) not in ans_n]
    answer_ok = (len(missing) == 0)
    reason = ""
    if not retrieval_ok:
        reason += f"检索没命中「{src}」; "
    if missing:
        reason += f"答案缺要点: {missing}"
    return CaseResult(case["id"], cat, q, retrieval_ok, answer_ok, answer, reason.strip())


@dataclass
class CategoryStat:
    total: int = 0
    answer_pass: int = 0
    retrieval_total: int = 0     # 只统计考检索的用例(可答类)
    retrieval_pass: int = 0


def main():
    with open(os.path.join(HERE, "rag_eval_set.json"), encoding="utf-8") as f:
        cases = json.load(f)["cases"]

    # 离线建索引一次(用按标题切,和 L7 定稿一致)
    collection = rag.build_index(rag.chunk_by_heading(rag.KNOWLEDGE_BASE))

    results: list[CaseResult] = []
    for case in cases:
        hits = rag.retrieve(collection, case["question"], k=3)
        answer = rag.rag_answer(case["question"], hits)
        results.append(judge(case, hits, answer))

    # —— 汇总 ——
    stats: dict[str, CategoryStat] = {}
    for r in results:
        s = stats.setdefault(r.category, CategoryStat())
        s.total += 1
        s.answer_pass += int(r.answer_ok)
        if r.retrieval_ok is not None:
            s.retrieval_total += 1
            s.retrieval_pass += int(r.retrieval_ok)

    print("\n================= RAG 评估打分卡 =================")
    print(f"{'类别':<14}{'答案通过':>10}{'检索命中':>12}")
    tot = CategoryStat()
    for cat, s in stats.items():
        tot.total += s.total; tot.answer_pass += s.answer_pass
        tot.retrieval_total += s.retrieval_total; tot.retrieval_pass += s.retrieval_pass
        ret = f"{s.retrieval_pass}/{s.retrieval_total}" if s.retrieval_total else "—"
        print(f"{cat:<14}{s.answer_pass}/{s.total:<8}{ret:>12}")
    ret_all = f"{tot.retrieval_pass}/{tot.retrieval_total}" if tot.retrieval_total else "—"
    print("-" * 48)
    print(f"{'总计':<14}{tot.answer_pass}/{tot.total:<8}{ret_all:>12}")

    # —— 逐条失败明细(排查用)——
    fails = [r for r in results if not r.answer_ok]
    if fails:
        print("\n----------------- 失败明细 -----------------")
        for r in fails:
            print(f"[{r.id}|{r.category}] {r.question}")
            print(f"   原因: {r.reason}")
            print(f"   答复: {r.answer[:80]}...")
    else:
        print("\n✅ 全部通过")


if __name__ == "__main__":
    main()
