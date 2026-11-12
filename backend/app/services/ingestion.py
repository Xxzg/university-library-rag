"""文献入库管线：解析（PDF/DOCX/TXT/MD）→ 按页切分 → 向量化 → Chroma 入库。

溯源设计：每个 chunk 的 metadata 携带 doc_id / title / page / chunk_index，
答案引用时可直接定位到书名和页码。
"""
from pathlib import Path

import pymupdf
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.services.vectorstore import get_vectorstore

SUPPORTED_TYPES = {".pdf", ".docx", ".txt", ".md"}


# ---------- 解析：统一输出 [(page_no, text)]，TXT/MD 无页码记 0 ----------

def parse_file(file_path: str) -> list[tuple[int, str]]:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(file_path)
    if suffix == ".docx":
        return _parse_docx(file_path)
    if suffix in (".txt", ".md"):
        return _parse_txt(file_path)
    raise ValueError(f"不支持的文件类型：{suffix}")


def _parse_pdf(file_path: str) -> list[tuple[int, str]]:
    pages = []
    with pymupdf.open(file_path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append((i, text))
    return pages


def _parse_docx(file_path: str) -> list[tuple[int, str]]:
    doc = DocxDocument(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return [(0, "\n".join(paragraphs))]


def _parse_txt(file_path: str) -> list[tuple[int, str]]:
    text = Path(file_path).read_text(encoding="utf-8", errors="ignore").strip()
    return [(0, text)] if text else []


# ---------- 切分：页内递归切分，保留页码 ----------

def split_pages(
    pages: list[tuple[int, str]],
) -> tuple[list[str], list[dict]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    )
    texts, metadatas = [], []
    for page_no, page_text in pages:
        for j, chunk in enumerate(splitter.split_text(page_text)):
            if chunk.strip():
                texts.append(chunk.strip())
                metadatas.append({"page": page_no, "chunk_index": j})
    return texts, metadatas


# ---------- 入库主流程 ----------

def ingest_document(doc_id: int, title: str, file_path: str) -> int:
    """解析并入库一篇文献，返回 chunk 数量。失败抛异常由调用方落库。"""
    pages = parse_file(file_path)
    if not pages:
        raise ValueError("未能从文件中提取到文本内容（可能是纯图片扫描件）")

    texts, metas = split_pages(pages)
    if not texts:
        raise ValueError("切分后无有效文本片段")

    store = get_vectorstore()
    ids = [f"doc{doc_id}_p{m['page']}_c{m['chunk_index']}" for m in metas]
    full_metas = [
        {
            "doc_id": doc_id,
            "title": title,
            "page": m["page"],
            "chunk_index": m["chunk_index"],
        }
        for m in metas
    ]
    # 分批入库，避免单次请求过大
    batch = 32
    for i in range(0, len(texts), batch):
        store.add_texts(
            texts=texts[i : i + batch],
            metadatas=full_metas[i : i + batch],
            ids=ids[i : i + batch],
        )
    return len(texts)


def remove_document_from_store(doc_id: int) -> None:
    store = get_vectorstore()
    store.delete(where={"doc_id": doc_id})
