from pathlib import Path

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource


BACKEND_DIR = Path(__file__).resolve().parents[2]


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
    openai_base_url: str = "https://api.openai.com/v1"
    openai_chat_model: str = "qwen3.7-plus"
    openai_chat_max_tokens: int = 384
    openai_audio_transcription_model: str = "whisper-1"
    ai_local_stream_chunk_delay_ms: int = 25
    ai_memory_recall_timeout_ms: int = 800

    # Push providers
    jpush_app_key: str = ""
    jpush_master_secret: str = ""
    jpush_api_url: str = "https://api.jpush.cn/v3/push"
    fcm_service_account_path: str = ""
    fcm_project_id: str = ""
    fcm_oauth_token_url: str = "https://oauth2.googleapis.com/token"
    fcm_scope: str = "https://www.googleapis.com/auth/firebase.messaging"
    apns_key_id: str = ""
    apns_team_id: str = ""
    apns_bundle_id: str = ""
    apns_private_key_path: str = ""
    apns_use_sandbox: bool = True

    # TTS
    fish_audio_api_key: str = ""
    fish_audio_base_url: str = "https://api.fish.audio"
    fish_audio_tts_model: str = "s2-pro"
    fish_audio_reference_id: str = ""
    fish_audio_tts_format: str = "mp3"
    fish_audio_asr_language: str = ""
    fish_audio_asr_ignore_timestamps: bool = True

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440

    # Admin
    admin_api_token: str = ""

    # WeChat Pay
    wechat_pay_api_base_url: str = "https://api.mch.weixin.qq.com"
    wechat_pay_app_id: str = ""
    wechat_pay_mch_id: str = ""
    wechat_pay_merchant_serial_no: str = ""
    wechat_pay_api_v3_key: str = ""
    wechat_pay_private_key_path: str = ""
    wechat_pay_platform_public_key_path: str = ""
    wechat_pay_notify_url: str = ""

    # Embedding
    embedding_provider: str = "siliconflow"
    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.siliconflow.cn/v1"
    embedding_model: str = "Qwen/Qwen3-VL-Embedding-8B"
    embedding_dimensions: int = 4096

    model_config = {
        "env_file": BACKEND_DIR / ".env",
        "env_file_encoding": "utf-8",
    }

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, dotenv_settings, env_settings, file_secret_settings


settings = Settings()
