from datetime import date
from decimal import Decimal

from app.models.product import (
    ProductAlias,
    ProductCategory,
    ReviewStatus,
    StandardProductRelation,
    StandardProductRelationType,
)
from app.models.requirement import RequirementType, StandardRequirement
from app.models.standard import Standard, StandardStatus
from app.models.standard_relation import StandardRelation, StandardRelationType
from app.utils.standard_no import StandardNoNormalizer


def make_standard(**overrides: object) -> Standard:
    standard_no = str(overrides.pop("standard_no", "GB 4806.11-2023"))
    normalized_no = overrides.pop("normalized_no", None) or StandardNoNormalizer.normalize(
        standard_no
    )

    values: dict[str, object] = {
        "standard_no": standard_no,
        "normalized_no": normalized_no,
        "standard_name": "食品安全国家标准 食品接触用橡胶材料及制品",
        "standard_type": "GB",
        "status": StandardStatus.ACTIVE,
        "publish_date": date(2023, 9, 6),
        "effective_date": date(2024, 4, 1),
        "expiry_date": None,
        "standard_year": 2023,
        "scope": "适用于食品接触用橡胶材料及制品。",
        "source": "openstd",
        "source_url": "https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=TEST",
    }
    values.update(overrides)
    return Standard(**values)


def make_relation(
    source_standard_id: int,
    target_standard_id: int,
    relation_type: StandardRelationType = StandardRelationType.REPLACES,
) -> StandardRelation:
    return StandardRelation(
        source_standard_id=source_standard_id,
        target_standard_id=target_standard_id,
        relation_type=relation_type,
    )


def make_category(
    name: str = "奶瓶",
    description: str | None = None,
    aliases: tuple[str, ...] = (),
    parent_id: int | None = None,
) -> ProductCategory:
    category = ProductCategory(
        name=name,
        description=description,
        parent_id=parent_id,
    )
    category.aliases = [ProductAlias(alias=alias) for alias in aliases]
    return category


def make_product_relation(
    standard_id: int,
    product_category_id: int,
    relation_type: StandardProductRelationType = (
        StandardProductRelationType.DIRECT_APPLICABLE
    ),
    confidence: Decimal | None = Decimal("1.0"),
    source_type: str = "MANUAL",
    source_reference: str | None = None,
    review_status: ReviewStatus = ReviewStatus.APPROVED,
) -> StandardProductRelation:
    return StandardProductRelation(
        standard_id=standard_id,
        product_category_id=product_category_id,
        relation_type=relation_type,
        confidence=confidence,
        source_type=source_type,
        source_reference=source_reference,
        review_status=review_status,
    )


def make_requirement(
    standard_id: int,
    chapter: str = "4.1",
    requirement_type: RequirementType = RequirementType.LABEL,
    requirement_text: str = "包装上应标注执行标准。",
    verification_method: str = "查看包装标签。",
) -> StandardRequirement:
    return StandardRequirement(
        standard_id=standard_id,
        chapter=chapter,
        requirement_type=requirement_type,
        requirement_text=requirement_text,
        verification_method=verification_method,
    )
