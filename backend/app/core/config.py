from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Utsav"
    VERSION: str = "1.0.0-RELEASE"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str = "sqlite:///./utsav_dev.db"  # Defaults to SQLite for local development/testing, overridden by env for PostgreSQL
    
    # M4: WhatsApp Native Guest Coordination Settings
    WHATSAPP_PROVIDER: str = "mock"  # "mock" or "cloud_api"
    WHATSAPP_API_TOKEN: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_WEBHOOK_VERIFY_TOKEN: str = "utsav_webhook_verify_token_secure"
    WHATSAPP_APP_SECRET: Optional[str] = None
    
    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def assemble_db_connection(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql://", 1)
        if v.startswith("postgresql+psycopg://"):
            return v.replace("postgresql+psycopg://", "postgresql://", 1)
        return v

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
