from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai import AIProviderError
from app.ai.base import redact_secret
from app.ai.config import AIConfig
from app.ai.types import AIProviderType
from app.db.session import get_db
from app.models.standard import Standard
from app.schemas.vision import VisionAnalysisResponse
from app.schemas.vision_match import (
    DetectedStandardItem,
    MatchedCategoryItem,
    RelatedStandardsResponse,
    StandardMatchItem,
    VisionMatchResponse,
)
from app.services.vision_match_service import (
    DetectedStandardResult,
    VisionMatchResult,
    match_vision,
    status_label,
)
from app.vision.image import ImageProcessingError
from app.vision.parser import VisionParseError
from app.vision.service import analyze_upload

router = APIRouter(prefix="/vision", tags=["vision"])


async def _close_upload(image: UploadFile) -> None:
    try:
        await image.close()
    except Exception:  # noqa: BLE001 - cleanup must not mask a response
        pass


def _build_config(
    provider: AIProviderType,
    api_base_url: str | None,
    api_key: str,
    model: str,
) -> AIConfig:
    try:
        return AIConfig(
            provider=provider,
            api_base_url=api_base_url,
            api_key=api_key,
            model=model,
        )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc


def _to_standard_item(
    standard: Standard,
    relation_type: str,
) -> StandardMatchItem:
    return StandardMatchItem(
        id=standard.id,
        standard_no=standard.standard_no,
        standard_name=standard.standard_name,
        status=standard.status,
        status_label=status_label(standard.status),
        publish_date=standard.publish_date,
        effective_date=standard.effective_date,
        expiry_date=standard.expiry_date,
        relation_type=relation_type,
        is_historical=standard.is_historical,
    )


def _to_detected_item(result: DetectedStandardResult) -> DetectedStandardItem:
    base = _to_standard_item(result.standard, "DETECTED")
    return DetectedStandardItem(
        **base.model_dump(),
        replaced_by=[
            _to_standard_item(standard, "REPLACES")
            for standard in result.replaced_by
        ],
        latest_current=[
            _to_standard_item(standard, "LATEST_CURRENT")
            for standard in result.latest_current
        ],
        notice=result.notice,
    )


def _related_items(entries) -> list[StandardMatchItem]:
    return [
        _to_standard_item(entry.standard, entry.relation.relation_type.value)
        for entry in entries
    ]


def _to_match_response(
    analysis: VisionAnalysisResponse,
    result: VisionMatchResult,
) -> VisionMatchResponse:
    return VisionMatchResponse(
        image_analysis=analysis,
        detected_standards=[
            _to_detected_item(item) for item in result.detected
        ],
        related_standards=RelatedStandardsResponse(
            current=_related_items(result.current),
            upcoming=_related_items(result.upcoming),
            historical=_related_items(result.historical),
            other=_related_items(result.other),
        ),
        image_stored=False,
        matched_categories=[
            MatchedCategoryItem(
                id=item.category.id,
                name=item.category.name,
                description=item.category.description,
                parent_id=item.category.parent_id,
                aliases=sorted(
                    alias.alias for alias in item.category.aliases
                ),
                score=item.score,
                matched_terms=item.matched_terms,
            )
            for item in result.matched_categories
        ],
        unmatched_visible_standard_numbers=result.unmatched,
    )


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
    try:
        config = _build_config(provider, api_base_url, api_key, model)
    except RequestValidationError:
        await _close_upload(image)
        raise

    try:
        return await analyze_upload(image, config)
    except ImageProcessingError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except AIProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail=redact_secret(exc.message, config),
        ) from exc
    except VisionParseError as exc:
        raise HTTPException(
            status_code=502,
            detail="AI 返回格式异常",
        ) from exc
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 - never leak image/provider internals
        raise HTTPException(
            status_code=502,
            detail="AI 识别失败",
        ) from None


@router.post(
    "/analyze-and-match",
    response_model=VisionMatchResponse,
    response_model_by_alias=True,
    summary="识别图片并与标准库、商品分类匹配",
    description=(
        "先使用用户 AI 配置识别图片，再用图片中的标准号、商品名、类别、材质和用途"
        "匹配标准库与商品分类。所有最终标准均来自数据库。"
    ),
)
async def analyze_and_match(
    image: UploadFile = File(..., description="JPEG / PNG / WebP，最大 10MB"),
    provider: AIProviderType = Form(..., description="AI Provider"),
    api_base_url: str | None = Form(default=None, alias="apiBaseUrl"),
    api_key: str = Form(..., alias="apiKey"),
    model: str = Form(...),
    db: Session = Depends(get_db),
) -> VisionMatchResponse:
    try:
        config = _build_config(provider, api_base_url, api_key, model)
    except RequestValidationError:
        await _close_upload(image)
        raise

    try:
        analysis = await analyze_upload(image, config)
    except ImageProcessingError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.message,
        ) from exc
    except AIProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail=redact_secret(exc.message, config),
        ) from exc
    except VisionParseError as exc:
        raise HTTPException(
            status_code=502,
            detail="AI 返回格式异常",
        ) from exc
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 - never leak image/provider internals
        raise HTTPException(
            status_code=502,
            detail="AI 识别失败",
        ) from None

    try:
        result = match_vision(db, analysis)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="标准库查询失败",
        ) from exc
    except Exception:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail="识别结果匹配失败",
        ) from None

    return _to_match_response(analysis, result)
