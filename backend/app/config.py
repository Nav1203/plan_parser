from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    app_name: str = "Production Planning Parser API"
    app_version: str = "1.0.0"
    debug: bool = False

    # MongoDB settings
    mongodb_url: str = "mongodb://admin:pass1234@localhost:27017/production?authSource=admin"
    mongodb_database: str = "production"

    # CORS settings
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore" 


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
