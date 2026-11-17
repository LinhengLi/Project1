"""Application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str = "EM Situational Awareness System"
    api_version: str = "0.1.0"
    database_url: str = "sqlite:///./ems.db"
    redis_url: str = "redis://localhost:6379/0"
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    static_dir: Path = Path(__file__).resolve().parents[2] / "frontend" / "static"
    startup_scenario: str = "three_constellations.json"
    enable_db_bootstrap: bool = True


settings = Settings()
