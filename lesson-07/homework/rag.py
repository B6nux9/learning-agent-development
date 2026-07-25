"""
L7 作业:用【真向量库 ChromaDB】搭一个最小可用的 RAG(生产形态,可写进简历)

为什么不手写 cosine 检索:那是个点积,面试证明不了什么,还像"没用过专业工具"。
概念(cosine/top-k/HNSW)你懂即可(quiz Q3 已答);项目用真向量库,面试才好讲选型与权衡。

═══════════════════════════════════════════════════════════════════════
技术栈(都是能写进简历、面试能讲的):
  - 切块 chunking       :按语义边界切
  - embedding           :OpenAI text-embedding-3-small(DeepSeek 端点无 embedding 接口)
  - 向量库              :ChromaDB(嵌入式、零配置、HNSW 近似最近邻、sqlite 持久化)
  - generation          :DeepSeek v4-flash(便宜)
  embedding 与生成解耦 → 两个 client。想全用 OpenAI 见下方 GEN_MODEL 标注。

面试选型话术(记住):选 Chroma 因嵌入式/零配置/适合中小规模+快速迭代;
  上千万级或高并发 → Milvus/Qdrant;数据在 Postgres → pgvector;只要极致速度 → FAISS。

依赖:pip install chromadb   (装不上就退 faiss-cpu,告诉我)

你要补 4 个 TODO:
  TODO 1  chunk_text       切块(固定窗口 + overlap)
  TODO 2  embed_texts      批量 embedding(OpenAI)
  TODO 3a build_index      把 chunks 存进 Chroma(离线建索引)
  TODO 3b retrieve         用 Chroma 查 top-k(在线检索)
  TODO 4  rag_answer       grounding 生成(强 prompt 约束)

跑通标准:
  "怎么退货"/"咋退款啊"    → 字面不同也命中退货政策(embedding 的价值)
  "退货运费谁出"           → 命中运费条款
  "你们卖不卖苹果手机"     → 知识库没有 → grounding 生效,答"暂无相关信息",不瞎编
"""

import os
import chromadb
from openai import OpenAI

# ── 两个 client:embedding 走 OpenAI,生成走 DeepSeek ────────────────────
embed_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
gen_client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],
                    base_url="https://api.deepseek.com")

EMBED_MODEL = "text-embedding-3-small"
GEN_MODEL = "deepseek-v4-flash"     # ← 想全用 OpenAI:改 "gpt-4o-mini",并把 gen_client 换成 embed_client

# ── 向量库:Chroma 持久化到本地磁盘(体现"离线建索引一次"的思想)──────────
#    PersistentClient 会把索引存到 ./chroma_db,下次可直接用,不必重新 embedding。
chroma_client = chromadb.PersistentClient(path="./chroma_db")
COLLECTION_NAME = "ecommerce_faq"

# ── 知识库 ──────────────────────────────────────────────────────────────
KNOWLEDGE_BASE = """\
# 退货与退款政策
本店支持 7 天无理由退货。商品需保持未拆封、未使用、不影响二次销售的状态,并保留完整包装与配件。
生鲜、定制类、贴身衣物等特殊商品不支持无理由退货。

# 退款到账时间
退款申请审核通过后,款项将原路退回。信用卡预计 3-7 个工作日到账,余额/零钱通常 1-2 个工作日。

# 运费承担规则
若因商品质量问题或发错货导致退货,退货运费由本店承担。
若为 7 天无理由退货(非质量问题),退货运费由买家承担。

# 换货流程
换货需商品未使用且不影响二次销售。请先联系客服登记,寄回后我们在收到并检验合格后发出新品。
同款换货不收取差价;跨款换货按新旧商品差价多退少补。

# 发票说明
下单时可备注开具电子发票,发票将在订单完成后 3 个工作日内发送至预留邮箱。纸质发票需额外申请。
"""


# ══════════════════════════════════════════════════════════════════════
#  TODO 1:切块 —— 固定窗口 + 重叠(chunk_size + chunk_overlap)
# ══════════════════════════════════════════════════════════════════════
def chunk_text(text: str, chunk_size: int = 150, chunk_overlap: int = 30) -> list[str]:
    """把 text 按【固定字符窗口】切块,相邻块之间保留 chunk_overlap 个字符的重叠。

    为什么要 overlap:防止一个完整意思正好被切在两块的交界处而丢失
    (比如"已签收商品 | 需在7日内退回",没重叠的话检索到后半块就没了前提)。
    窗口每次前进的步长 = chunk_size - chunk_overlap(所以相邻块尾首重叠 chunk_overlap 个字符)。

    实现要点:
      - 从 0 开始,每次取 text[start : start+chunk_size] 作为一块;
      - 下一块 start += (chunk_size - chunk_overlap);
      - 直到覆盖完整个 text。去掉首尾空白、跳过空块。
      - ⚠️ 边界守卫(fail fast):若 chunk_overlap >= chunk_size,步长 <= 0 会【死循环】,
        应在函数开头直接 raise ValueError(你的老短板:边界情况)。

    生产对照:真实项目用 LangChain 的 RecursiveCharacterTextSplitter —— 它做的就是
      size+overlap,但更聪明:优先在【段落/句子/词】边界断开,而不是像这里硬切字符。
      我们手写一遍是为了吃透 size/overlap 这两个旋钮,不是要取代它。
      (对这份带 # 标题的结构化文档,按标题切其实更好;这里用通用的窗口切法是为了练 overlap。)
    """
    # 你的代码:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size to avoid infinite loop.")
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += (chunk_size - chunk_overlap)
    return chunks


# ── 更好的切法:按 # 标题切(结构化文档的语义边界)──────────────────────────
def chunk_by_heading(text: str) -> list[str]:
    """按 '# 小标题' 切块:每块 = 一个标题 + 它下面的正文,直到下一个标题。

    对 markdown 这种结构化文档,标题就是天然的语义边界,每块是一个自洽的知识单元,
    比固定窗口"硬切字符"干净得多(不会把一句话/一节切两半)。
    生产等价物 = LangChain 的 MarkdownHeaderTextSplitter(L9 会用)。
    """
    chunks, current = [], []
    for line in text.splitlines():
        if line.startswith("# ") and current:   # 遇到新标题 → 先把上一块收尾
            chunks.append("\n".join(current).strip())
            current = []
        current.append(line)
    if current:                                  # 别漏最后一块(边界!)
        chunks.append("\n".join(current).strip())
    return [c for c in chunks if c]              # 去空块


# ══════════════════════════════════════════════════════════════════════
#  TODO 2:批量 embedding(OpenAI)
# ══════════════════════════════════════════════════════════════════════
def embed_texts(texts: list[str]) -> list[list[float]]:
    """把一批文本转成向量列表,返回 [[float,...], ...](顺序与 texts 对应)。

    用法:
        resp = embed_client.embeddings.create(model=EMBED_MODEL, input=texts)
        # resp.data[i].embedding 是第 i 条文本的向量(float 列表)
    要点:一次传【一批】(input=列表)省钱省时;返回纯 list 即可(Chroma 接受 list)。
    """
    # 你的代码:
    resp = embed_client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in resp.data]


# ══════════════════════════════════════════════════════════════════════
#  TODO 3a:离线建索引 —— 把 chunks 存进 Chromacd 
# ══════════════════════════════════════════════════════════════════════
def build_index(chunks: list[str]) -> chromadb.Collection:
    """建立/重建 Chroma collection,把 chunks 及其向量存进去,返回 collection。

    步骤:
      1. 干净重建(避免重复运行时累积重复):
             chroma_client.delete_collection(COLLECTION_NAME)  # 可能不存在,try/except 包一下
             collection = chroma_client.create_collection(COLLECTION_NAME)
      2. 对 chunks 批量 embedding(调 embed_texts)。
      3. collection.add(
             ids=[f"chunk_{i}" for i in range(len(chunks))],   # 每条要有唯一 id
             embeddings=<上一步的向量列表>,
             documents=chunks,                                  # 原文,查询时会原样返回
         )
    说明:我们【自带 embedding】传进去,不用 Chroma 内置的 embedder ——
         这是生产常见做法(embedding 模型自己选,向量库只管存和查)。
    """
    # 你的代码:
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = chroma_client.create_collection(COLLECTION_NAME)
    embeddings = embed_texts(chunks)
    collection.add(
        ids=[f"chunk_{i}" for i in range(len(chunks))],
        embeddings=embeddings,
        documents=chunks
    )
    return collection

# ══════════════════════════════════════════════════════════════════════
#  TODO 3b:在线检索 —— 用 Chroma 查 top-k
# ══════════════════════════════════════════════════════════════════════
def retrieve(collection: chromadb.Collection, question: str, k: int = 3) -> list[str]:
    """把问题 embedding 后,在 Chroma 里查最相似的 k 个 chunk,返回它们的原文列表。

    步骤:
      1. q_vec = embed_texts([question])[0]     # 问题也要用【同一个 embedding 模型】
      2. res = collection.query(query_embeddings=[q_vec], n_results=k)
      3. 返回 res["documents"][0]                # 注意是嵌套列表:外层对应多个 query,取 [0]
    (Chroma 底层用 HNSW 做近似最近邻,这步就是"向量库"的核心价值:海量向量里毫秒找 top-k。)
    """
    # 你的代码:
    q_vec = embed_texts([question])[0]
    res = collection.query(query_embeddings=[q_vec], n_results=k)
    return res["documents"][0]


# ══════════════════════════════════════════════════════════════════════
#  TODO 4:grounding 生成 —— 关键在 prompt 强约束
# ══════════════════════════════════════════════════════════════════════
def rag_answer(question: str, retrieved_chunks: list[str]) -> str:
    """把检索到的 chunks 作为"资料"塞进 prompt,让模型【只依据资料】回答。

    system prompt 必须强约束(回扣 L6 + 你 quiz Q2):
      - 只依据提供的资料回答;资料中没有的不得编造;
      - 答不出就说"暂无相关信息,建议联系人工客服"。
    步骤:拼资料 → gen_client.chat.completions.create(model=GEN_MODEL, ..., temperature=0) → 返回文本。
    """
    # 你的代码:
    system_prompt = (
        "你是一个客服助手。请根据提供的资料回答用户的问题。"
        "如果资料中没有相关信息，请回答'暂无相关信息,建议联系人工客服'。"
        "请不要编造信息。"
    )
    user_prompt = f"用户问题: {question}\n\n提供的资料:\n" + "\n".join(retrieved_chunks)
    response = gen_client.chat.completions.create(
        model=GEN_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    return response.choices[0].message.content.strip()

# ══════════════════════════════════════════════════════════════════════
#  主流程:离线建索引一次 → 在线按问题检索+回答
# ══════════════════════════════════════════════════════════════════════
def main():
    # —— 离线:切块 + 建索引 ——
    # 对比实验:换成按标题切,看答案质量变化(想切回固定窗口就用注释那行)
    chunks = chunk_by_heading(KNOWLEDGE_BASE)
    # chunks = chunk_text(KNOWLEDGE_BASE, chunk_size=150, chunk_overlap=30)
    print(f"[index] 切出 {len(chunks)} 个 chunk")
    for i, c in enumerate(chunks):          # 打出来,亲眼看相邻块的尾首重叠
        print(f"  [chunk {i}] {c[:40]}...")
    collection = build_index(chunks)
    print(f"[index] 已写入 Chroma,collection 现有 {collection.count()} 条")

    # —— 在线:每个问题检索 + 回答 ——
    for q in ["怎么退货", "咋退款啊要几天", "退货运费谁出", "你们卖不卖苹果手机"]:
        hits = retrieve(collection, q, k=3)
        answer = rag_answer(q, hits)
        print(f"\n>>> 问:{q}")
        print(f"[检索命中] {[h[:20] + '...' for h in hits]}")   # 看真实召回,确认没跑偏
        print(f"客服:{answer}")


if __name__ == "__main__":
    main()
