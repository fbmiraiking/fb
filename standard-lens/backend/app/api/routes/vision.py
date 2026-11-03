from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.ai import AIProviderError, get_vision_provider
from app.ai.base import redact_secret
from app.ai.config import AIConfig
from app.ai.types import AIProviderType
from app.schemas.vision import VisionAnalysisResponse
from app.vision.image import ImageProcessingError, prepare_image, read_limited_upload
from app.vision.parser import VisionParseError, parse_vision_json

router = APIRouter(prefix="/vision", tags=["vision"])


@router.post(
    "/analyze",
    response_model=VisionAnalysisResponse,
    response_model_by_alias=True,
    summary="识别商品图片并提取结构化标签信息",
    description=(
        "使用用户随请求提供的多模态 AI 配置识别图片。图片在内存中校验、压缩到最长边 2048，"
        "AI 请求完成后释放；不保存原图，不写日志。"
    ),
)
async def analyze_image(
    image: UploadFile = File(..., description="JPEG / PNG / WebP，最大 10MB"),
    provider: AIProviderType = Form(..., description="AI Provider"),
    api_base_url: str | None = Form(default=None, alias="apiBaseUrl"),
    api_key: str = Form(..., alias="apiKey"),
    model: str = Form(...),
) -> VisionAnalysisResponse:
    raw: bytes | None = None
    processed: bytes | None = None
    config: AIConfig | None = None

    try:
        try:
            config = AIConfig(
                provider=provider,
                api_base_url=api_base_url,
                api_key=api_key,
                model=model,
            )
        except ValidationError as exc:
            raise RequestValidationError(exc.errors()) from exc

        raw = await read_limited_upload(image)
        processed = await run_in_threadpool(prepare_image, raw)
        raw = None

        vision_provider = get_vision_provider(config.provider)
        result = await vision_provider.analyze_image(processed, config)
        processed = None

        try:
            return parse_vision_json(result.text)
        except VisionParseError as exc:
            raise HTTPException(
                status_code=502,
                detail="AI 返回格式异常",
            ) from exc
    except RequestValidationError:
        raise
    except ImageProcessingError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except AIProviderError as exc:
        detail = (
            redact_secret(exc.message, config)
            if config is not None
            else "AI 识别失败"
        )
        raise HTTPException(status_code=502, detail=detail) from exc
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 - never leak image/provider internals
        raise HTTPException(
            status_code=502,
            detail="AI 识别失败",
        ) from None
    finally:
        raw = None
        processed = None
        try:
            await image.close()
        except Exception:  # noqa: BLE001 - upload cleanup must not mask a response
            pass
