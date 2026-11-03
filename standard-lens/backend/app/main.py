import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.sync.scheduler import shutdown_scheduler, start_scheduler
from app.sync.service import mark_stale_sync_tasks_failed

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("standard_lens")


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s v%s (%s)", settings.app_name, settings.app_version, settings.app_env)
    logger.info(
        "MySQL target: %s:%s/%s",
        settings.mysql_host,
        settings.mysql_port,
        settings.mysql_database,
    )

    if settings.sync_recover_stale_tasks:
        db = SessionLocal()
        try:
            recovered = mark_stale_sync_tasks_failed(db)
            if recovered:
                logger.warning("Marked %d stale sync task(s) as FAILED", recovered)
        except Exception:  # noqa: BLE001 - database may not be ready at startup
            logger.exception("Could not recover stale sync tasks")
        finally:
            db.close()

    if settings.sync_scheduler_enabled:
        try:
            start_scheduler(settings)
        except Exception:  # noqa: BLE001 - scheduler must not prevent API startup
            logger.exception("Could not start the standard sync scheduler")

    yield

    shutdown_scheduler()
    engine.dispose()
    logger.info("Application stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Standard Lens API - standards, versions, sync, products, AI settings, vision and standard matching (Phase 7)",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
    openapi_url="/openapi.json",
)


@app.exception_handler(RequestValidationError)
async def _sanitized_validation_errors(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return validation errors without echoing request input.

    Pydantic's default error payload can include the submitted ``apiKey`` value
    in ``input``/``ctx``. The AI settings endpoint must never reflect it.
    """
    detail = [
        {
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg", "Invalid input"),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": detail})

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials="*" not in settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{settings.api_prefix}/health",
        "standards": f"{settings.api_prefix}/v1/standards/search",
        "products": f"{settings.api_prefix}/v1/products/search",
        "admin_sync": f"{settings.api_prefix}/admin/sync/standards",
    }
