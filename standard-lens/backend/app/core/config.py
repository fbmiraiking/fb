from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables and backend/.env."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Standard Lens API"
    app_version: str = "0.7.0"
    app_env: str = "development"
    debug: bool = True
    api_prefix: str = "/api"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # MySQL
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "standard_lens"
    mysql_password: str = ""
    mysql_database: str = "standard_lens"
    mysql_charset: str = "utf8mb4"
    database_url: str | None = None

    # Connection pool
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600
    db_connect_timeout: int = 3

    # Admin / standard sync
    admin_sync_token: str = ""
    sync_source: str = "std_samr"
    sync_scheduler_enabled: bool = True
    sync_recover_stale_tasks: bool = True
    sync_schedule_hour: int = 2
    sync_schedule_minute: int = 0
    sync_request_interval_seconds: float = 1.0
    sync_timeout_seconds: float = 20.0
    sync_max_retries: int = 3
    sync_retry_backoff_seconds: float = 1.0
    sync_page_size: int = 50
    # 0 means unlimited. The first full initialization is admin-triggered.
    sync_max_items_per_run: int = 0
    sync_update_max_pages: int = 20
    sync_overlap_hours: int = 24
    sync_user_agent: str = "StandardLens/0.4"

    # AI requests are user-supplied and only live for the request lifetime.
    ai_request_timeout_seconds: float = 20.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url

        user = quote_plus(self.mysql_user)
        password = quote_plus(self.mysql_password)
        return (
            f"mysql+pymysql://{user}:{password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset={self.mysql_charset}&connect_timeout={self.db_connect_timeout}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
