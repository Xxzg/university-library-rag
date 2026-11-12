"""向量数据库封装：Chroma + OpenAI 兼容 Embedding（默认硅基流动 bge-m3）。"""
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.config import settings

COLLECTION_NAME = "library_docs"


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
        # bge-m3 系列需要关闭 extra_headers 里的一些默认行为
        check_embedding_ctx_length=False,
    )


def get_vectorstore() -> Chroma:
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_dir,
    )
