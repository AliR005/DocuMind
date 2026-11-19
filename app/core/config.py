from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RAG API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./rag.db"
    debug: bool = False
    max_upload_size_bytes: int = 10 * 1024 * 1024
    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_relevance_threshold: float = 0.1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_document_processing(self) -> "Settings":
        if self.max_upload_size_bytes <= 0:
            raise ValueError("max_upload_size_bytes must be greater than zero")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        if not 0.0 <= self.min_relevance_threshold <= 1.0:
            raise ValueError("min_relevance_threshold must be between 0 and 1")
        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be between zero and chunk_size - 1")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
