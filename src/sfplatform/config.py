from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://sourceflow:sourceflow@localhost:5432/sourceflow"
    redis_url: str = "redis://localhost:6379/0"
    mistral_api_key: str = ""
    default_tenant_id: int = 1
    upload_dir: str = "./uploads"

    embedding_model: str = "mistral-embed"
    generation_model: str = "mistral-small-latest"

    chunk_size_tokens: int = 800
    chunk_overlap_tokens: int = 128
    retrieval_top_k: int = 4
    # mistral-embed cosine similarities sit in a narrow, high band (~0.60-0.70)
    # even for on-topic content, so 0.75 filtered out every relevant chunk and the
    # bot always answered "No cuento con esa información". The LLM's NO_INFO reply
    # is the real grounding gate; this threshold only drops clearly-unrelated hits.
    similarity_threshold: float = 0.4


@lru_cache
def get_settings() -> Settings:
    return Settings()
