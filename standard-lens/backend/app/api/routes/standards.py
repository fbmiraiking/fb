from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.standard import (
    StandardDetail,
    StandardSearchResponse,
    StandardSummary,
    StandardVersionItem,
)
from app.services.standard_service import get_standard, get_version_chain, search_standards

router = APIRouter(prefix="/standards", tags=["standards"])


@router.get(
    "/search",
    response_model=StandardSearchResponse,
    summary="搜索标准",
    description=(
        "支持标准号精确搜索（含 GB4806.11-2023、GB 4806.11—2023 等写法）、"
        "规范化标准号匹配，以及标准名称模糊搜索。"
    ),
)
def search_standards_endpoint(
    q: str = Query(..., min_length=1, max_length=200, description="标准号或标准名称"),
    limit: int = Query(20, ge=1, le=100, description="返回条数上限"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
) -> StandardSearchResponse:
    total, items, normalized_query = search_standards(
        db,
        q,
        limit=limit,
        offset=offset,
    )
    return StandardSearchResponse(
        query=q,
        normalized_query=normalized_query,
        total=total,
        limit=limit,
        offset=offset,
        items=[StandardSummary.model_validate(item) for item in items],
    )


@router.get(
    "/{standard_id}/versions",
    response_model=list[StandardVersionItem],
    response_model_by_alias=True,
    summary="标准版本链",
    description=(
        "返回通过 REPLACES / REPLACED_BY / AMENDS / AMENDED_BY 关联的完整版本链，"
        "按标准年份和生效日期从新到旧排序。RELATED 是关联标准，不进入版本链。"
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "标准不存在"}},
)
def get_standard_versions_endpoint(
    standard_id: int = Path(..., ge=1, description="标准 ID"),
    db: Session = Depends(get_db),
) -> list[StandardVersionItem]:
    standards = get_version_chain(db, standard_id)
    if standards is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标准不存在",
        )
    return [StandardVersionItem.model_validate(item) for item in standards]


@router.get(
    "/{standard_id}",
    response_model=StandardDetail,
    summary="标准详情",
    responses={status.HTTP_404_NOT_FOUND: {"description": "标准不存在"}},
)
def get_standard_endpoint(
    standard_id: int = Path(..., ge=1, description="标准 ID"),
    db: Session = Depends(get_db),
) -> StandardDetail:
    standard = get_standard(db, standard_id)
    if standard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="标准不存在",
        )
    return StandardDetail.model_validate(standard)
