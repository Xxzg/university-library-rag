"""全局配置：从 .env 加载，模型接入层全部可切换。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ---- 模型接入（OpenAI 兼容，默认硅基流动） ----
    llm_api_base: str = "https://api.siliconflow.cn/v1"
    llm_api_key: str = ""
    llm_model: str = "THUDM/GLM-4-9B-0414"
    embedding_model: str = "BAAI/bge-m3"
    rerank_model: str = "BAAI/bge-reranker-v2-m3"

    # ---- 业务配置 ----
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 720
    database_url: str = "sqlite:///./data/library.db"
    upload_dir: str = "./data/uploads"
    chroma_dir: str = "./data/chroma"

    # ---- RAG 参数 ----
    chunk_size: int = 500
    chunk_overlap: int = 50
    recall_top_k: int = 6
    rerank_top_n: int = 4


settings = Settings()
