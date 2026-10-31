from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(ValueError):
    """Raised when required deployment configuration is unsafe or incomplete."""

    @classmethod
    def whatsapp_mock_in_production(cls) -> "ConfigurationError":
        return cls("WHATSAPP_PROVIDER=mock is not allowed when WhatsApp is enabled in production")

    @classmethod
    def missing_webhook_token(cls) -> "ConfigurationError":
        return cls("WHATSAPP_WEBHOOK_VERIFY_TOKEN is required when WhatsApp is enabled")

    @classmethod
    def missing_cloud_api_credentials(cls) -> "ConfigurationError":
        return cls("WHATSAPP_API_TOKEN and WHATSAPP_PHONE_NUMBER_ID are required for cloud_api")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Utsav"
    VERSION: str = "1.0.0-RELEASE"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Defaults to SQLite for local development/testing, overridden by env for PostgreSQL
    DATABASE_URL: str = "sqlite:///./utsav_dev.db"

    # M4: WhatsApp Native Guest Coordination Settings
    ENABLE_M4_WHATSAPP: bool = False
    WHATSAPP_PROVIDER: str = "mock"  # "mock" or "cloud_api"
    WHATSAPP_API_TOKEN: str | None = None
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str | None = None
    WHATSAPP_APP_SECRET: str | None = None

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        if v.startswith("postgresql+psycopg://"):
            return v.replace("postgresql+psycopg://", "postgresql://", 1)
        return v

    @model_validator(mode="after")
    def validate_whatsapp_configuration(self) -> "Settings":
        if not self.ENABLE_M4_WHATSAPP:
            return self
        if self.ENVIRONMENT.lower() == "production" and self.WHATSAPP_PROVIDER == "mock":
            raise ConfigurationError.whatsapp_mock_in_production()
        if not self.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            raise ConfigurationError.missing_webhook_token()
        if self.WHATSAPP_PROVIDER == "cloud_api" and (
            not self.WHATSAPP_API_TOKEN or not self.WHATSAPP_PHONE_NUMBER_ID
        ):
            raise ConfigurationError.missing_cloud_api_credentials()
        return self


settings = Settings()
