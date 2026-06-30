from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "lingban-backend"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me"

    # Database
    database_url: str = "postgresql+asyncpg://lingban:lingban@localhost:5432/lingban"
    database_pool_size: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # AI
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Push (极光推送)
    jpush_app_key: str = ""
    jpush_master_secret: str = ""

    # TTS
    fish_audio_api_key: str = ""

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # Embedding
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
