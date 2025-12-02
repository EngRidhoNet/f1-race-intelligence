"""
Configuration module using Pydantic BaseSettings.
All configuration is loaded from environment variables.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "F1 Race Intelligence Backend"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/f1_intelligence"
    
    # LLM Configuration
    llm_provider: str = "ollama"  # Options: "ollama", "openai_compatible"
    llm_api_base_url: str = "http://localhost:11434"
    llm_model_name: str = "llama3"
    llm_api_key: str | None = None
    llm_timeout: int = 60  # seconds
    
    # WebSocket Replay
    replay_fps: int = 10  # frames per second for telemetry replay
    
    # FastF1 Cache
    fastf1_cache_dir: str = "./fastf1_cache"
    
    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()