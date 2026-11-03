import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


class DatabaseHealth(BaseModel):
    status: str = Field(description="'ok' when a SELECT 1 round trip succeeds")
    latency_ms: float | None = Field(default=None, description="Database round-trip time")
    detail: str | None = Field(default=None, description="Short failure reason when status is 'down'")


class HealthResponse(BaseModel):
    status: str = Field(description="'ok' when the API and database are both healthy, otherwise 'degraded'")
    service: str
    version: str
    environment: str
    database: DatabaseHealth
    checked_at: datetime
    latency_ms: float


def _describe_database_error(exc: Exception) -> str:
    """Turn common driver errors into a short, actionable message for the UI."""
    message = str(exc)
    lowered = message.lower()

    if "1045" in message or "access denied" in lowered:
        return "数据库认证失败，请检查 backend/.env 中的 MYSQL_USER / MYSQL_PASSWORD。"
    if "1049" in message or "unknown database" in lowered:
        return "数据库不存在，请先执行 deploy/mysql/init.sql 或 python -m scripts.init_db。"
    if "1044" in message:
        return "当前数据库账号无权访问目标数据库，请检查授权。"
    if "2003" in message or "2002" in message or "10061" in message or "can't connect" in lowered:
        return "无法连接 MySQL，请确认 MySQL 8 已启动，并检查 MYSQL_HOST / MYSQL_PORT。"
    if "2005" in message or "unknown host" in lowered:
        return "无法解析 MySQL 主机名，请检查 MYSQL_HOST。"

    first_line = message.strip().splitlines()[0] if message.strip() else exc.__class__.__name__
    return first_line[:240]


def _check_database() -> DatabaseHealth:
    started = time.perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - a health probe must never raise
        logger.warning("Database health check failed: %s", exc)
        return DatabaseHealth(status="down", detail=_describe_database_error(exc))
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    return DatabaseHealth(status="ok", latency_ms=elapsed)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service and database health",
    description=(
        "Always returns HTTP 200 while the API process is alive. Inspect the "
        "'status' field: 'ok' means the database answered as well."
    ),
)
def health() -> HealthResponse:
    started = time.perf_counter()
    database = _check_database()
    elapsed = round((time.perf_counter() - started) * 1000, 1)
    return HealthResponse(
        status="ok" if database.status == "ok" else "degraded",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database=database,
        checked_at=datetime.now(timezone.utc),
        latency_ms=elapsed,
    )
