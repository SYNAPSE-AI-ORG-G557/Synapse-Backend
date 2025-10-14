from typing import Optional

from pydantic import PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---------------- Core App ----------------
    PROJECT_NAME: str = "Synapse Project"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = "production"

    # ---------------- PostgreSQL ----------------
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str  # host or host:port
    POSTGRES_DB: str
    DATABASE_DSN: Optional[str] = None
    DATABASE_DSN_SYNC: Optional[str] = None
    
    # ---------------- Database Connection Pooling ----------------
    DB_POOL_SIZE: int = 5  # Base pool size per service
    DB_MAX_OVERFLOW: int = 10  # Additional connections beyond pool_size
    DB_POOL_TIMEOUT: int = 30  # Seconds to wait for connection
    DB_POOL_RECYCLE: int = 1800  # Seconds before connection is recycled
    DB_POOL_PRE_PING: bool = True  # Validate connections before use

    @field_validator("DATABASE_DSN", mode="before")
    @classmethod
    def assemble_db_connection(cls, v, info):
        if isinstance(v, str) and v:
            return v
        # IMPORTANT: no leading slash here; PostgresDsn.build will assemble "/<db>" correctly.
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=info.data["POSTGRES_USER"],
                password=info.data["POSTGRES_PASSWORD"],
                host=info.data["POSTGRES_SERVER"],
                path=f"{info.data['POSTGRES_DB']}",
            )
        )

    @field_validator("DATABASE_DSN_SYNC", mode="before")
    @classmethod
    def assemble_sync_db_connection(cls, v, info):
        if isinstance(v, str) and v:
            return v
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg2",
                username=info.data["POSTGRES_USER"],
                password=info.data["POSTGRES_PASSWORD"],
                host=info.data["POSTGRES_SERVER"],
                path=f"{info.data['POSTGRES_DB']}",
            )
        )

    # ---------------- Redis ----------------
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_URL: Optional[str] = None

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v, info):
        if isinstance(v, str) and v:
            return v
        return str(
            RedisDsn.build(
                scheme="redis",
                host=info.data["REDIS_HOST"],
                port=info.data["REDIS_PORT"],
                path=f"/{info.data['REDIS_DB']}",
            )
        )

    # ---------------- Celery ----------------
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def assemble_celery_broker(cls, v, info):
        if isinstance(v, str) and v:
            return v
        return str(
            RedisDsn.build(
                scheme="redis",
                host=info.data["REDIS_HOST"],
                port=info.data["REDIS_PORT"],
                path="/1",  # Broker uses Redis DB 1
            )
        )

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def assemble_celery_backend(cls, v, info):
        if isinstance(v, str) and v:
            return v
        return str(
            RedisDsn.build(
                scheme="redis",
                host=info.data["REDIS_HOST"],
                port=info.data["REDIS_PORT"],
                path="/2",  # Results use Redis DB 2
            )
        )

    # ---------------- Authentication ----------------
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # ---------------- Google OAuth2 ----------------
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str

    # ---------------- Session Management ----------------
    SESSION_SECRET_KEY: str

    # ---------------- Qdrant ----------------
    QDRANT_HOST: str
    QDRANT_PORT: int
    QDRANT_GRPC_PORT: int

    # ---------------- ML / AI Worker ----------------
    ML_DEVICE: str = "cpu"
    USE_API_LLM: bool = False

    # Gemini (primary)
    GEMINI_API_KEY: str | None = None
    # Default to a fast/stable 2.5 family; override in .env if you want.
    GEMINI_MODEL: str = "gemini-2.5-flash"

    ML_MODEL_PATH: Optional[str] = None

    # ---------------- Local LLM (Ollama) Fallback ----------------
    # Base URL for your local Ollama daemon
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Comma-separated preference order. First available non-empty response wins.
    # Example env override:
    #   OLLAMA_MODEL_PREFERENCE="phi3:mini,phi3:latest,mistral:latest"
    OLLAMA_MODEL_PREFERENCE: str = "phi3:mini,phi3:latest,mistral:latest"

    @field_validator("OLLAMA_BASE_URL", mode="before")
    @classmethod
    def normalize_ollama_base(cls, v: Optional[str]):
        # Ensure we have a sane base URL and no trailing slash
        if not isinstance(v, str) or not v.strip():
            return "http://localhost:11434"
        v = v.strip().rstrip("/")
        if not (v.startswith("http://") or v.startswith("https://")):
            v = "http://" + v
        return v

    @field_validator("OLLAMA_MODEL_PREFERENCE", mode="before")
    @classmethod
    def normalize_ollama_models(cls, v: Optional[str]):
        # Normalize CSV (trim, dedupe in-order)
        default = "phi3:mini,phi3:latest,mistral:latest"
        if not isinstance(v, str) or not v.strip():
            return default
        items = [x.strip() for x in v.split(",") if x.strip()]
        seen = set()
        ordered = []
        for x in items:
            if x not in seen:
                seen.add(x)
                ordered.append(x)
        return ",".join(ordered) if ordered else default

    # ---------------- Pydantic Settings Config ----------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Global settings instance
settings = Settings()
