from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.product import (
    ProductSearchResponse,
    ProductStandardItem,
    ProductStandardsResponse,
    ProductSummary,
)
from app.services.product_service import (
    ProductStandardEntry,
    get_product_standards,
    search_products,
)

router = APIRouter(prefix="/products", tags=["products"])


def _to_standard_item(entry: ProductStandardEntry) -> ProductStandardItem:
    return ProductStandardItem(
        id=entry.standard.id,
        standard_no=entry.standard.standard_no,
        standard_name=entry.standard.standard_name,
        status=entry.standard.status,
        effective_date=entry.standard.effective_date,
        expiry_date=entry.standard.expiry_date,
        relation_type=entry.relation.relation_type,
        review_status=entry.relation.review_status,
    )


@router.get(
    "/search",
    response_model=ProductSearchResponse,
    response_model_by_alias=True,
    summary="搜索商品分类",
    description="按商品分类名称或别名模糊搜索，返回分类及其别名。",
)
def search_products_endpoint(
    q: str = Query(..., min_length=1, max_length=200, description="商品名称或别名"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> ProductSearchResponse:
    total, categories = search_products(db, q, limit=limit, offset=offset)
    return ProductSearchResponse(
        query=q,
        total=total,
        limit=limit,
        offset=offset,
        items=[ProductSummary.from_category(category) for category in categories],
    )


@router.get(
    "/{product_id}/standards",
    response_model=ProductStandardsResponse,
    response_model_by_alias=True,
    summary="商品分类关联标准",
    description=(
        "返回商品分类关联的标准，并按 current / upcoming / historical / related 分组。"
        "同一标准有多个关联类型时只返回优先级最高的一条；已驳回的关联不返回。"
    ),
    responses={status.HTTP_404_NOT_FOUND: {"description": "商品分类不存在"}},
)
def get_product_standards_endpoint(
    product_id: int = Path(..., ge=1, description="商品分类 ID"),
    db: Session = Depends(get_db),
) -> ProductStandardsResponse:
    result = get_product_standards(db, product_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="商品分类不存在",
        )

    return ProductStandardsResponse(
        product=ProductSummary.from_category(result.product),
        current=[_to_standard_item(item) for item in result.current],
        upcoming=[_to_standard_item(item) for item in result.upcoming],
        historical=[_to_standard_item(item) for item in result.historical],
        related=[_to_standard_item(item) for item in result.related],
    )
