from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "Utsav"
    VERSION: str = "1.0.0-RELEASE"
    API_V1_STR: str = "/api/v1"
    
    DATABASE_URL: str = "sqlite:///./utsav_dev.db"  # Defaults to SQLite for local development/testing, overridden by env for PostgreSQL
    
    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
