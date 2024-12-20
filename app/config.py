from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path


class Settings(BaseSettings):
    MONITOR_CONTINUOUSLY: bool = True
    CHECK_INTERVAL: int = 30
    MAX_HISTORY_ENTRIES: int = 100
    LOG_LEVEL: str = "INFO"
    DATA_FOLDER: Path = Path("data")
    CHECKS_FILE: Path = DATA_FOLDER / "checks.yaml"
    INCIDENTS_FILE: Path = DATA_FOLDER / "incidents.md"
    TEMPLATE_FILE: str = "index.html.theme"
    HISTORY_TEMPLATE_FILE: str = "history.html.theme"
    PUBLIC_STATUS_MAX_AGE_MINUTES: int = 5  # Maximum age of status data for public endpoint

    # Ensure the data folder exists
    if not DATA_FOLDER.exists():
        DATA_FOLDER.mkdir()

    if not CHECKS_FILE.exists():
        CHECKS_FILE.touch(exist_ok=True)

    if not INCIDENTS_FILE.exists():
        INCIDENTS_FILE.touch(exist_ok=True)

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
