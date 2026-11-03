import time

from fastapi import APIRouter

from app.ai import get_vision_provider
from app.ai.base import redact_secret
from app.ai.config import AIConfig
from app.ai.types import ProviderTestResult
from app.schemas.ai import AITestConnectionResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/test-connection",
    response_model=AITestConnectionResponse,
    response_model_by_alias=True,
    summary="测试用户 AI 配置",
    description=(
        "使用请求体中的用户配置测试 Provider 连通性。配置仅在本次请求内使用，"
        "不写入数据库，不记录 API Key。"
    ),
)
async def test_ai_connection(config: AIConfig) -> AITestConnectionResponse:
    started = time.perf_counter()
    try:
        provider = get_vision_provider(config.provider)
        result = await provider.test_connection(config)
    except Exception:  # noqa: BLE001 - never leak provider internals or the key
        result = ProviderTestResult(ok=False, message="测试连接失败")

    latency_ms = round((time.perf_counter() - started) * 1000)
    return AITestConnectionResponse(
        ok=result.ok,
        provider=config.provider,
        model=config.model,
        message=redact_secret(result.message, config),
        latency_ms=latency_ms,
    )
