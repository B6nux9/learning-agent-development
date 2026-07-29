"""
政策答疑 RAG (policy_rag.py) —— capstone 的「答政策问题」能力。

L7 的 RAG 三件套(embed→chroma→grounding 生成)我给你复用，本文件你只写一个**新**东西：
  search_policy() —— 带**相似度阈值**的检索：政策没覆盖就转人工，而不是硬答（挡幻觉）。

为什么要阈值：向量检索**永远返回最近的 chunk**，哪怕问题跟政策八竿子打不着。
不设阈值 → 模型拿不相关资料硬凑 = 幻觉。设阈值 → 距离太远(不相似)就判「没覆盖」转人工。

跑法（需要 OPENAI_API_KEY 做 embedding）：
    uv run python capstones/stage2-customer-service-agent/policy_rag.py
"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from openai import OpenAI

# ── 两个 client（复用 L7）：embedding 走 OpenAI，生成走 DeepSeek ──
embed_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def _deepseek_key() -> str:
    return os.environ.get("DEEPSEEK_API_KEY") or (
        Path(__file__).resolve().parents[2] / "deepseek_api.txt"
    ).read_text().strip()


gen_client = OpenAI(api_key=_deepseek_key(), base_url="https://api.deepseek.com")
EMBED_MODEL = "text-embedding-3-small"
GEN_MODEL = "deepseek-v4-flash"


# ── 政策知识库（我给你；真实项目是 MD/PDF ~40页，这里给几条够演示阈值）──
POLICY_KB = [
    "退货政策：签收后 7 天内无理由退货，商品需保持完好、不影响二次销售。",
    "退款到账：退款审核通过后原路退回，支付宝/微信 1-3 个工作日，银行卡 3-7 个工作日。",
    "运费政策：7 天无理由退货运费由买家承担；商品质量问题退货运费由卖家承担。",
    "换货政策：签收 7 天内可申请换货，同款不同规格需补/退差价。",
    "发票政策：下单时可申请电子发票，开票后 3 个工作日内发送到预留邮箱。",
]


# ── 建索引（离线一次，复用 L7 的 embed + chroma；内存版够用）──
def _embed(texts: list[str]) -> list[list[float]]:
    resp = embed_client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [d.embedding for d in resp.data]


def _build_index() -> chromadb.Collection:
    col = chromadb.Client().create_collection("policy")
    col.add(
        ids=[f"p{i}" for i in range(len(POLICY_KB))],
        embeddings=_embed(POLICY_KB),
        documents=POLICY_KB,
    )
    return col


_COLLECTION: chromadb.Collection | None = None

def _get_collection() -> chromadb.Collection:
    global _COLLECTION
    if _COLLECTION is None:
        _COLLECTION = _build_index()
    return _COLLECTION


# ── grounding 生成（复用 L7 的强约束 prompt，我给你，直接调）──
def _grounded_answer(question: str, chunks: list[str]) -> str:
    system_prompt = (
        "你是电商客服助手。严格只依据下面提供的【资料】回答；"
        "资料中没有的不得编造。若资料与用户说法矛盾，要明确纠正并给出资料里的正确信息。"
    )
    user_prompt = f"用户问题: {question}\n\n提供的资料:\n" + "\n".join(chunks)
    resp = gen_client.chat.completions.create(
        model=GEN_MODEL,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_prompt}],
        temperature=0,
    )
    return resp.choices[0].message.content.strip()



# 阈值标定(eval 13 条分布, 见 calibrate_threshold.py): normal 0.78–1.09 / unanswerable 1.34–1.52，
# 沟(1.09,1.34)取 1.15 偏严侧防幻觉(旧值 0.9 会误踢 0.914/1.041/1.090 三条正例)；生产按误判率回调。
POLICY_DISTANCE_THRESHOLD = 1.15



# ══════════════════════════════════════════════════════════════════════
# block 6 —— 你来写：search_policy（带阈值的检索，今天唯一的新东西）
# ══════════════════════════════════════════════════════════════════════
def search_policy(question: str) -> dict:
    """答政策问题，用相似度阈值挡幻觉。

    接口契约：
      1. 检索：把 question embedding，chroma 查 top-1，同时拿 documents 和 **distances**。
         - qvec = _embed([question])[0]
         - res = _COLLECTION.query(query_embeddings=[qvec], n_results=1)
         - 最近的一条：文档 res["documents"][0][0]，距离 res["distances"][0][0]（**距离越小越相似**）
      2. 阈值闸：最近距离 > POLICY_DISTANCE_THRESHOLD → 判「没覆盖」，
         return {"ok": False, "reason": "not_covered"}（上层转人工）。
      3. 覆盖了（距离 ≤ 阈值）→ 用检索到的 chunk 调 _grounded_answer 生成，
         return {"ok": True, "answer": 生成文本}。
    """
    qvec = _embed([question])[0]
    res = _get_collection().query(query_embeddings=[qvec], n_results=1)
    
    distance = res["distances"][0][0]
    if distance > POLICY_DISTANCE_THRESHOLD:
        return {"ok": False, "reason": "not_covered"}

    return {"ok": True, "answer": _grounded_answer(question, [res["documents"][0][0]])}

# ── 跑起来看真实距离（今天的标定素材）──
if __name__ == "__main__":
    probes = [
        "怎么退货",          # 覆盖：退货政策
        "退款多久到账",       # 覆盖：退款到账
        "你们这周有什么活动",  # 不覆盖：政策里没有 → 应转人工
        "帮我推荐一款手机",    # 不覆盖：导购，超范围 → 应转人工
    ]
    for q in probes:
        qvec = _embed([q])[0]
        res = _get_collection().query(query_embeddings=[qvec], n_results=1)
        dist = res["distances"][0][0]
        doc = res["documents"][0][0]
        print(search_policy(q))
        print(f"[{dist:.3f}] 问「{q}」→ 最近政策：{doc[:20]}…")
