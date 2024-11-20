from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path


class Settings(BaseSettings):
    MONITOR_CONTINUOUSLY: bool = True
    CHECK_INTERVAL: int = 30
    MAX_HISTORY_ENTRIES: int = 100
    LOG_LEVEL: str = "INFO"
    CHECKS_FILE: Path = Path("checks.yaml")
    INCIDENTS_FILE: Path = Path("incidents.md")
    TEMPLATE_FILE: str = "index.html.theme"
    HISTORY_TEMPLATE_FILE: str = "history.html.theme"

    # Database configuration
    PRIMARY_DATABASE_URL: str = "sqlite:///status_history.db"

    # Auth settings
    AUTH_ENABLED: bool = True  # Global auth flag

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings():
    return Settings()


# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
