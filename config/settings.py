"""
Central application settings — loaded from environment / .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_env: str = Field("development", alias="APP_ENV")
    app_secret_key: str = Field("dev-secret", alias="APP_SECRET_KEY")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # ── APIs ─────────────────────────────────────────────────────────────────
    alpha_vantage_api_key: str = Field("", alias="ALPHA_VANTAGE_API_KEY")
    polygon_api_key: str = Field("", alias="POLYGON_API_KEY")

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        "sqlite:///./alphasignal.db", alias="DATABASE_URL"
    )

    # ── Redis / Celery ───────────────────────────────────────────────────────
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(
        "redis://localhost:6379/0", alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        "redis://localhost:6379/1", alias="CELERY_RESULT_BACKEND"
    )

    # ── Twilio ───────────────────────────────────────────────────────────────
    twilio_account_sid: str = Field("", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field("", alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field("", alias="TWILIO_FROM_NUMBER")
    alert_to_number: str = Field("", alias="ALERT_TO_NUMBER")

    # ── SendGrid ─────────────────────────────────────────────────────────────
    sendgrid_api_key: str = Field("", alias="SENDGRID_API_KEY")
    alert_from_email: str = Field("", alias="ALERT_FROM_EMAIL")
    alert_to_email: str = Field("", alias="ALERT_TO_EMAIL")

    # ── Slack ────────────────────────────────────────────────────────────────
    slack_bot_token: str = Field("", alias="SLACK_BOT_TOKEN")
    slack_channel: str = Field("#trading-alerts", alias="SLACK_CHANNEL")

    # ── ML ───────────────────────────────────────────────────────────────────
    signal_confidence_threshold: float = Field(
        0.65, alias="SIGNAL_CONFIDENCE_THRESHOLD"
    )
    model_save_path: str = Field("./models/saved", alias="MODEL_SAVE_PATH")

    # ── Server ───────────────────────────────────────────────────────────────
    streamlit_port: int = Field(8501, alias="STREAMLIT_PORT")
    fastapi_port: int = Field(8000, alias="FASTAPI_PORT")
    fastapi_host: str = Field("0.0.0.0", alias="FASTAPI_HOST")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
