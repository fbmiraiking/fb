from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.product import (
    ProductAlias,
    ProductCategory,
    ReviewStatus,
    StandardProductRelation,
    StandardProductRelationType,
)
from app.models.standard import Standard, StandardStatus

# Higher-priority relation types win when one standard has multiple relations
# with the same category.
_RELATION_PRIORITY: dict[StandardProductRelationType, int] = {
    StandardProductRelationType.DIRECT_APPLICABLE: 0,
    StandardProductRelationType.SAFETY: 1,
    StandardProductRelationType.MATERIAL: 2,
    StandardProductRelationType.LABELING: 3,
    StandardProductRelationType.TEST_METHOD: 4,
    StandardProductRelationType.PACKAGING: 5,
    StandardProductRelationType.GENERAL: 6,
    StandardProductRelationType.POSSIBLE: 7,
}


@dataclass(frozen=True, slots=True)
class ProductStandardEntry:
    standard: Standard
    relation: StandardProductRelation


@dataclass(frozen=True, slots=True)
class ProductStandardsResult:
    product: ProductCategory
    current: list[ProductStandardEntry]
    upcoming: list[ProductStandardEntry]
    historical: list[ProductStandardEntry]
    related: list[ProductStandardEntry]


def _escape_like(value: str) -> str:
    return value.replace("!", "!!").replace("%", "!%").replace("_", "!_")


def _relation_rank(relation: StandardProductRelation) -> tuple[int, Decimal, int]:
    confidence = (
        relation.confidence if relation.confidence is not None else Decimal("-1")
    )
    return (_RELATION_PRIORITY[relation.relation_type], -confidence, relation.id)


def _entry_sort_key(entry: ProductStandardEntry) -> tuple[date, int, int]:
    standard = entry.standard
    return (
        standard.effective_date or date.min,
        standard.standard_year or 0,
        standard.id,
    )


def _group_key(entry: ProductStandardEntry) -> str:
    relation_type = entry.relation.relation_type
    status = entry.standard.status

    if relation_type == StandardProductRelationType.POSSIBLE:
        return "related"
    if status == StandardStatus.ACTIVE:
        return "current"
    if status == StandardStatus.UPCOMING:
        return "upcoming"
    if status in (StandardStatus.REPLACED, StandardStatus.ABOLISHED):
        return "historical"
    return "related"


def search_products(
    db: Session,
    query: str,
    *,
    limit: int,
    offset: int,
) -> tuple[int, list[ProductCategory]]:
    raw_query = query.strip()
    if not raw_query:
        return 0, []

    pattern = f"%{_escape_like(raw_query)}%"
    alias_match = exists(
        select(ProductAlias.id).where(
            ProductAlias.category_id == ProductCategory.id,
            ProductAlias.alias.ilike(pattern, escape="!"),
        )
    )
    where_clause = or_(
        ProductCategory.name.ilike(pattern, escape="!"),
        alias_match,
    )

    total = db.scalar(
        select(func.count()).select_from(ProductCategory).where(where_clause)
    ) or 0

    relevance = case(
        (func.lower(ProductCategory.name) == raw_query.lower(), 0),
        else_=1,
    )
    statement = (
        select(ProductCategory)
        .where(where_clause)
        .options(selectinload(ProductCategory.aliases))
        .order_by(relevance, ProductCategory.name, ProductCategory.id)
        .limit(limit)
        .offset(offset)
    )
    return total, list(db.scalars(statement).all())


def get_product_standards(
    db: Session,
    product_id: int,
) -> ProductStandardsResult | None:
    product = db.scalar(
        select(ProductCategory)
        .where(ProductCategory.id == product_id)
        .options(selectinload(ProductCategory.aliases))
    )
    if product is None:
        return None

    rows = db.execute(
        select(Standard, StandardProductRelation)
        .join(
            StandardProductRelation,
            StandardProductRelation.standard_id == Standard.id,
        )
        .where(
            StandardProductRelation.product_category_id == product_id,
            StandardProductRelation.review_status != ReviewStatus.REJECTED,
        )
    ).all()

    # One item per standard, using the most relevant relation type. Confidence
    # breaks ties between relations of the same type priority.
    best: dict[int, ProductStandardEntry] = {}
    for standard, relation in rows:
        existing = best.get(standard.id)
        if existing is None or _relation_rank(relation) < _relation_rank(existing.relation):
            best[standard.id] = ProductStandardEntry(standard=standard, relation=relation)

    groups: dict[str, list[ProductStandardEntry]] = {
        "current": [],
        "upcoming": [],
        "historical": [],
        "related": [],
    }
    for entry in best.values():
        groups[_group_key(entry)].append(entry)

    for entries in groups.values():
        entries.sort(key=_entry_sort_key, reverse=True)

    return ProductStandardsResult(product=product, **groups)
