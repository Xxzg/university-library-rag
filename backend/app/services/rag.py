"""RAG 问答核心链路：

用户问题
  → ① 多轮历史改写（condense question，把"那第三章呢"补全为独立问题）
  → ② 向量检索召回 top-k（Chroma + bge-m3）
  → ③ 重排（硅基流动 bge-reranker-v2-m3，失败自动降级为向量序）
  → ④ Prompt 组装（文献片段带 [n] 编号，要求答案标注引用）
  → ⑤ LLM 流式生成（SSE 推送）
  → ⑥ 溯源结构化（引用块绑定书名/页码/原文）
"""
import json
from typing import AsyncGenerator

import httpx
from langchain_openai import ChatOpenAI

from app.config import settings
from app.services.vectorstore import get_vectorstore

# ---------- 常量 ----------

REWRITE_SYSTEM = (
    "你是问题改写助手。根据对话历史，把用户的最新问题改写为一个独立、完整、"
    "不依赖上下文即可理解的中文问题。只输出改写后的问题本身，不要任何解释。"
    "如果最新问题本身已经完整独立，原样输出它。"
)

ANSWER_SYSTEM = (
    "你是高校图书馆的智能文献问答助手。请严格遵守：\n"
    "1. 仅根据下面提供的馆藏文献片段回答用户问题，禁止使用片段之外的知识编造内容；\n"
    "2. 答案中引用了哪条片段，就在对应句子末尾标注 [n]（如 [1] [2]），可多选；\n"
    "3. 回答用简体中文，条理清晰，先给结论再展开；\n"
    "4. 如果文献片段不足以回答问题，直接说明“馆藏文献中暂无足够的相关内容”，并简述片段里最接近的信息。"
)

HISTORY_ROUNDS = 5  # 参与上下文的历史轮数


# ---------- ① 历史改写 ----------

def _build_history_text(history: list[dict]) -> str:
    lines = []
    for m in history[-HISTORY_ROUNDS * 2 :]:
        speaker = "用户" if m["role"] == "user" else "助手"
        lines.append(f"{speaker}: {m['content']}")
    return "\n".join(lines)


async def rewrite_question(question: str, history: list[dict]) -> str:
    """把多轮对话中的指代问题改写为独立问题。无历史时直接返回原问题。"""
    if not history:
        return question
    llm = _get_llm(temperature=0.0)
    prompt = (
        f"对话历史：\n{_build_history_text(history)}\n\n"
        f"最新问题：{question}\n\n改写后的独立问题："
    )
    try:
        resp = await llm.ainvoke([("system", REWRITE_SYSTEM), ("human", prompt)])
        rewritten = resp.content.strip().strip('"“”')
        return rewritten or question
    except Exception:
        # 改写失败不阻塞问答，退回原问题
        return question


# ---------- ②③ 检索 + 重排 ----------

def recall_chunks(query: str) -> list[dict]:
    """向量检索召回，返回带元数据的 chunk 列表（含距离分）。"""
    store = get_vectorstore()
    docs_and_scores = store.similarity_search_with_score(query, k=settings.recall_top_k)
    results = []
    for doc, score in docs_and_scores:
        meta = doc.metadata
        results.append(
            {
                "document_id": meta.get("doc_id", 0),
                "title": meta.get("title", "未知文献"),
                "page": meta.get("page"),
                "chunk_index": meta.get("chunk_index", 0),
                "snippet": doc.page_content,
                # Chroma 返回的是 L2 距离，转成 0~1 的相似度展示用
                "score": max(0.0, 1.0 - float(score)),
            }
        )
    return results


async def rerank_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """调用 rerank 模型对召回结果精排；失败时降级为原始向量序。"""
    if not chunks or not settings.rerank_model:
        return chunks[: settings.rerank_top_n]
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{settings.llm_api_base.rstrip('/')}/rerank",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.rerank_model,
                    "query": query,
                    "documents": [c["snippet"] for c in chunks],
                    "top_n": settings.rerank_top_n,
                    "return_documents": False,
                },
            )
            resp.raise_for_status()
            ranked = resp.json()["results"]  # [{index, relevance_score}]
        reranked = []
        for r in ranked:
            c = dict(chunks[r["index"]])
            c["score"] = float(r["relevance_score"])
            reranked.append(c)
        return reranked
    except Exception:
        # 重排服务不可用时降级，保证可用性
        return chunks[: settings.rerank_top_n]


# ---------- ④⑤⑥ 组装 + 流式生成 ----------

def _get_llm(temperature: float = 0.3, streaming: bool = True) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
        temperature=temperature,
        streaming=streaming,
        max_retries=2,
    )


def _build_context(chunks: list[dict]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        page_info = f" 第{c['page']}页" if c.get("page") else ""
        parts.append(
            f"[{i}] 《{c['title']}》{page_info}\n{c['snippet']}"
        )
    return "\n\n".join(parts)


async def stream_answer(
    question: str,
    history: list[dict],
) -> AsyncGenerator[str, str]:
    """完整 RAG 流程，以 SSE 事件流 yield。

    事件类型：
      rewrite  -> {"question": 改写后的问题}
      citation -> {"citations": [引用块]}
      delta    -> {"content": 增量文本}
      error    -> {"message": 错误信息}
      done     -> {}
    """

    def sse(event: str, data: dict) -> str:
        return f"data: {json.dumps({'event': event, **data}, ensure_ascii=False)}\n\n"

    # ① 改写
    standalone = await rewrite_question(question, history)
    if standalone != question:
        yield sse("rewrite", {"question": standalone})

    # ② 召回 + ③ 重排
    chunks = recall_chunks(standalone)
    chunks = await rerank_chunks(standalone, chunks)
    if not chunks:
        yield sse(
            "error",
            {"message": "馆藏文献库为空，请先由教师/管理员上传文献后再提问。"},
        )
        return

    # 引用块先于正文推送，前端可先渲染溯源卡片
    citations = [
        {
            "index": i,
            "document_id": c["document_id"],
            "title": c["title"],
            "page": c["page"],
            "chunk_index": c["chunk_index"],
            "snippet": c["snippet"][:200],
            "score": round(c["score"], 4),
        }
        for i, c in enumerate(chunks, start=1)
    ]
    yield sse("citation", {"citations": citations})

    # ④ 组装 Prompt
    context = _build_context(chunks)
    messages = [("system", ANSWER_SYSTEM)]
    for m in history[-HISTORY_ROUNDS * 2 :]:
        role = "human" if m["role"] == "user" else "ai"
        messages.append((role, m["content"]))
    messages.append(
        (
            "human",
            f"馆藏文献片段：\n{context}\n\n用户问题：{question}",
        )
    )

    # ⑤ 流式生成
    llm = _get_llm()
    try:
        async for chunk in llm.astream(messages):
            if chunk.content:
                yield sse("delta", {"content": chunk.content})
    except Exception as e:
        yield sse("error", {"message": f"模型调用失败：{e}"})
        return

    yield sse("done", {})
