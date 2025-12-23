from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"

    # ChromaDB
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "redis_knowledge"

    # App
    app_env: str = "development"
    app_debug: bool = True
    log_level: str = "INFO"

    # RAG
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
