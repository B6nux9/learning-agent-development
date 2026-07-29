"""
阈值标定 (calibrate_threshold.py) —— 用评估集的距离分布，定 POLICY_DISTANCE_THRESHOLD。

sit 1 我们用 4 个探针拍了个 0.9；今天用 eval/rag_eval_set.json 里的 13 条
(9 normal + 4 unanswerable) 正经标定：看两组距离分布的「沟」在哪。

判据：normal 该被覆盖(距离小)、unanswerable 该转人工(距离大)。
理想=两组之间有一条清晰的沟，阈值放沟里；现实=可能重叠，那就做 precision/recall 权衡。

跑法（需 OPENAI_API_KEY 做 embedding）：
    uv run python capstones/stage2-customer-service-agent/calibrate_threshold.py
"""

from __future__ import annotations

import json
from pathlib import Path

# 复用 policy_rag 的索引与 embedding（同一套 POLICY_KB，别另建）
from policy_rag import _embed, _get_collection

EVAL_PATH = Path(__file__).resolve().parents[2] / "eval" / "rag_eval_set.json"


# ── 读评估集，取出要标定的两组问题 ──
def load_questions() -> dict[str, list[str]]:
    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))["cases"]
    groups: dict[str, list[str]] = {"normal": [], "unanswerable": []}
    for c in cases:
        if c["category"] in groups:
            groups[c["category"]].append(c["question"])
    return groups


# ══════════════════════════════════════════════════════════════════════
# distances_for —— 给一组问题，逐题算它对 POLICY_KB 的 top-1 距离
# ══════════════════════════════════════════════════════════════════════
def distances_for(questions: list[str]) -> list[float]:
    """对每个问题，embedding → chroma 查 top-1 → 取最近距离，收成一个 list。

    每个 q：
        qvec = _embed([q])[0]
        res  = _get_collection().query(query_embeddings=[qvec], n_results=1)
        dist = res["distances"][0][0]
      把所有 dist 收进一个 list 返回（顺序无所谓，等下会排序）。
    """
    distances = []
    for q in questions:
        qvec = _embed([q])[0]
        res = _get_collection().query(query_embeddings=[qvec], n_results=1)
        dist = res["distances"][0][0]
        distances.append(dist)
    return distances


# ── 把两组分布打印出来，标出「沟」 ──
def _report(groups: dict[str, list[float]]) -> None:
    for name, ds in groups.items():
        ds_sorted = sorted(ds)
        shown = ", ".join(f"{d:.3f}" for d in ds_sorted)
        lo = f"{min(ds):.3f}" if ds else "—"
        hi = f"{max(ds):.3f}" if ds else "—"
        print(f"[{name:12}] n={len(ds)}  min={lo}  max={hi}")
        print(f"               排序: {shown}")
    if groups["normal"] and groups["unanswerable"]:
        gap_lo = max(groups["normal"])          # normal 里最远的（最难覆盖的正例）
        gap_hi = min(groups["unanswerable"])    # unanswerable 里最近的（最像覆盖的负例）
        if gap_lo < gap_hi:
            print(f"\n✅ 有沟：normal 最大 {gap_lo:.3f} < unanswerable 最小 {gap_hi:.3f}，"
                  f"阈值可放 ({gap_lo:.3f}, {gap_hi:.3f}) 之间。")
        else:
            print(f"\n⚠️ 重叠：normal 最大 {gap_lo:.3f} ≥ unanswerable 最小 {gap_hi:.3f}，"
                  f"没有干净的沟 → 要做 precision/recall 权衡（往哪偏、牺牲谁）。")


if __name__ == "__main__":
    qs = load_questions()
    dist_groups = {name: distances_for(questions) for name, questions in qs.items()}
    _report(dist_groups)
