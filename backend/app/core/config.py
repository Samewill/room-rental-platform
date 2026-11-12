from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: SecretStr | None = None
    access_token_expire_minutes: int = Field(default=30, gt=0)
    rental_interest_expiry_days: int = Field(default=90, gt=0)
    rental_interest_max_submissions_per_day: int = Field(default=20, gt=0)
    cors_allowed_origins: str = (
        "http://127.0.0.1:5173,http://localhost:5173,"
        "http://127.0.0.1:5174,http://localhost:5174"
    )
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: SecretStr | None = None
    whatsapp_access_token: SecretStr | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_app_secret: SecretStr | None = None
    whatsapp_verify_token: SecretStr | None = None
    whatsapp_phone_encryption_key: SecretStr | None = None
    whatsapp_phone_lookup_key: SecretStr | None = None
    whatsapp_graph_api_version: str = "v23.0"
    whatsapp_template_language: str = "en_US"
    whatsapp_verification_template_name: str = "rental_phone_verification"
    whatsapp_message_template_name: str = "rental_message_notification"
    whatsapp_room_alert_template_name: str = "room_rental_new_listing_alert"
    groq_api_key: SecretStr | None = None
    groq_model: str = "llama-3.3-70b-versatile"
    groq_max_tokens: int = Field(default=1024, gt=0)
    google_maps_server_api_key: SecretStr | None = None
    inception_api_key: SecretStr | None = None
    inception_base_url: str = "https://api.inceptionlabs.ai/v1"
    inception_model: str = "mercury-3"
    inception_max_tokens: int = Field(default=1024, gt=0)
    inception_max_retries: int = Field(default=2, ge=0)
    inception_backoff_base_seconds: float = Field(default=1, gt=0)
    inception_backoff_max_seconds: float = Field(default=8, gt=0)
    llm_call_timeout_seconds: float = Field(default=20, gt=0)

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()