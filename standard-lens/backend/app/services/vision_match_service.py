import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.product import (
    ProductCategory,
    ReviewStatus,
    StandardProductRelation,
    StandardProductRelationType,
)
from app.models.standard import Standard, StandardStatus
from app.models.standard_relation import StandardRelation, StandardRelationType
from app.schemas.vision import VisionAnalysisResponse
from app.services.product_service import ProductStandardEntry, relation_rank
from app.services.standard_service import get_version_chain
from app.utils.standard_no import StandardNoNormalizer

STATUS_LABELS: dict[StandardStatus, str] = {
    StandardStatus.ACTIVE: "当前现行",
    StandardStatus.UPCOMING: "即将实施",
    StandardStatus.REPLACED: "旧标准",
    StandardStatus.ABOLISHED: "已废止",
    StandardStatus.UNKNOWN: "状态未知",
}

MAX_MATCHED_CATEGORIES = 5


@dataclass(frozen=True, slots=True)
class MatchedCategoryResult:
    category: ProductCategory
    score: float
    matched_terms: list[str]


@dataclass(frozen=True, slots=True)
class DetectedStandardResult:
    standard: Standard
    status_label: str
    replaced_by: list[Standard]
    latest_current: list[Standard]
    notice: str


@dataclass(frozen=True, slots=True)
class VisionMatchResult:
    detected: list[DetectedStandardResult]
    unmatched: list[str]
    matched_categories: list[MatchedCategoryResult]
    current: list[ProductStandardEntry]
    upcoming: list[ProductStandardEntry]
    historical: list[ProductStandardEntry]
    other: list[ProductStandardEntry]


def status_label(status: StandardStatus) -> str:
    return STATUS_LABELS.get(status, "状态未知")


def _normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).strip().casefold()
    return re.sub(r"\s+", "", text)


def _match_score(term: str, text: str) -> float:
    if not term or not text:
        return 0.0
    if term == text:
        return 1.0
    if term in text or text in term:
        return 0.6
    return 0.0


def _term_specs(analysis: VisionAnalysisResponse) -> dict[str, int]:
    specs: dict[str, int] = {}

    def add(value: str | None, weight: int) -> None:
        if not value:
            return
        term = _normalize_text(value)
        if len(term) < 2:
            return
        specs[term] = max(specs.get(term, 0), weight)

    add(analysis.product.name, 5)
    add(analysis.product.category_guess, 5)
    for material in analysis.materials:
        add(material, 2)
    for usage in analysis.usages:
        add(usage, 2)
    return specs


def match_product_categories(
    db: Session,
    analysis: VisionAnalysisResponse,
) -> list[MatchedCategoryResult]:
    specs = _term_specs(analysis)
    if not specs:
        return []

    categories = list(
        db.scalars(
            select(ProductCategory)
            .options(selectinload(ProductCategory.aliases))
            .order_by(ProductCategory.id)
        ).all()
    )

    results: list[MatchedCategoryResult] = []
    for category in categories:
        texts = [
            _normalize_text(category.name),
            *(_normalize_text(alias.alias) for alias in category.aliases),
        ]
        texts = [text for text in texts if text]
        score = 0.0
        matched_terms: list[str] = []

        for term, weight in specs.items():
            best = max((_match_score(term, text) for text in texts), default=0.0)
            if best > 0:
                score += weight * best
                matched_terms.append(term)

        if score > 0:
            results.append(
                MatchedCategoryResult(
                    category=category,
                    score=round(score, 2),
                    matched_terms=matched_terms,
                )
            )

    results.sort(
        key=lambda item: (
            -item.score,
            _normalize_text(item.category.name),
            item.category.id,
        )
    )
    return results[:MAX_MATCHED_CATEGORIES]


def _standard_desc_key(standard: Standard) -> tuple[bool, int, int, int]:
    return (
        standard.effective_date is None,
        -(standard.effective_date.toordinal() if standard.effective_date else 0),
        -(standard.standard_year or 0),
        -standard.id,
    )


def _sort_standards_desc(standards: list[Standard]) -> None:
    standards.sort(key=_standard_desc_key)


def _entry_desc_key(entry: ProductStandardEntry) -> tuple[bool, int, int, int]:
    return _standard_desc_key(entry.standard)


def _sort_entries_desc(entries: list[ProductStandardEntry]) -> None:
    entries.sort(key=_entry_desc_key)


def _sort_entries_upcoming(entries: list[ProductStandardEntry]) -> None:
    entries.sort(
        key=lambda entry: (
            entry.standard.effective_date is None,
            entry.standard.effective_date or date.max,
            entry.standard.standard_year or 0,
            entry.standard.id,
        )
    )


def _direct_replacements(db: Session, standard_id: int) -> list[Standard]:
    relations = list(
        db.scalars(
            select(StandardRelation).where(
                or_(
                    and_(
                        StandardRelation.relation_type
                        == StandardRelationType.REPLACES,
                        StandardRelation.target_standard_id == standard_id,
                    ),
                    and_(
                        StandardRelation.relation_type
                        == StandardRelationType.REPLACED_BY,
                        StandardRelation.source_standard_id == standard_id,
                    ),
                )
            )
        ).all()
    )

    successor_ids: set[int] = set()
    for relation in relations:
        if relation.relation_type == StandardRelationType.REPLACES:
            successor_ids.add(relation.source_standard_id)
        else:
            successor_ids.add(relation.target_standard_id)
    successor_ids.discard(standard_id)
    if not successor_ids:
        return []

    standards = list(
        db.scalars(
            select(Standard).where(Standard.id.in_(successor_ids))
        ).all()
    )
    _sort_standards_desc(standards)
    return standards


def _format_date(value: date | None) -> str:
    return value.isoformat() if value is not None else "未提供"


def _format_standards(standards: list[Standard], empty_text: str) -> str:
    if not standards:
        return empty_text
    return "、".join(
        f"{standard.standard_no}（{status_label(standard.status)}）"
        for standard in standards
    )


def _build_notice(
    standard: Standard,
    replaced_by: list[Standard],
    latest_current: list[Standard],
) -> str:
    effective = _format_date(standard.effective_date)

    if standard.status == StandardStatus.REPLACED:
        return (
            f"图片上的标准 {standard.standard_no} 是旧标准，实施于 {effective}；"
            f"当前替代标准：{_format_standards(replaced_by, '数据库中暂未记录')}；"
            f"当前最新现行标准：{_format_standards(latest_current, '暂未找到')}。"
        )
    if standard.status == StandardStatus.ABOLISHED:
        return (
            f"图片上的标准 {standard.standard_no} 已废止，实施于 {effective}；"
            f"当前替代标准：{_format_standards(replaced_by, '数据库中暂未记录')}；"
            f"当前最新现行标准：{_format_standards(latest_current, '暂未找到')}。"
        )
    if standard.status == StandardStatus.ACTIVE:
        return f"图片上的标准 {standard.standard_no} 当前为现行标准，实施于 {effective}。"
    if standard.status == StandardStatus.UPCOMING:
        return f"图片上的标准 {standard.standard_no} 即将实施，预计 {effective} 生效。"
    return f"图片上的标准 {standard.standard_no} 状态未知。"


def match_detected_standards(
    db: Session,
    analysis: VisionAnalysisResponse,
) -> tuple[list[DetectedStandardResult], list[str]]:
    detected: list[DetectedStandardResult] = []
    unmatched: list[str] = []
    seen: set[str] = set()

    for raw_number in analysis.visible_standard_numbers:
        normalized = StandardNoNormalizer.try_normalize(raw_number)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)

        standard = db.scalar(
            select(Standard).where(Standard.normalized_no == normalized)
        )
        if standard is None:
            unmatched.append(normalized)
            continue

        replaced_by = _direct_replacements(db, standard.id)
        chain = get_version_chain(db, standard.id) or [standard]
        latest_current = [
            item for item in chain if item.status == StandardStatus.ACTIVE
        ]
        _sort_standards_desc(latest_current)
        detected.append(
            DetectedStandardResult(
                standard=standard,
                status_label=status_label(standard.status),
                replaced_by=replaced_by,
                latest_current=latest_current,
                notice=_build_notice(
                    standard,
                    replaced_by,
                    latest_current,
                ),
            )
        )

    return detected, unmatched


def match_related_standards(
    db: Session,
    category_ids: list[int],
) -> tuple[
    list[ProductStandardEntry],
    list[ProductStandardEntry],
    list[ProductStandardEntry],
    list[ProductStandardEntry],
]:
    if not category_ids:
        return [], [], [], []

    rows = db.execute(
        select(Standard, StandardProductRelation)
        .join(
            StandardProductRelation,
            StandardProductRelation.standard_id == Standard.id,
        )
        .where(
            StandardProductRelation.product_category_id.in_(category_ids),
            StandardProductRelation.review_status != ReviewStatus.REJECTED,
        )
    ).all()

    best: dict[int, ProductStandardEntry] = {}
    for standard, relation in rows:
        existing = best.get(standard.id)
        if existing is None or relation_rank(relation) < relation_rank(existing.relation):
            best[standard.id] = ProductStandardEntry(
                standard=standard,
                relation=relation,
            )

    groups: dict[str, list[ProductStandardEntry]] = {
        "current": [],
        "upcoming": [],
        "historical": [],
        "other": [],
    }
    for entry in best.values():
        relation_type = entry.relation.relation_type
        status = entry.standard.status
        if (
            relation_type == StandardProductRelationType.POSSIBLE
            or status == StandardStatus.UNKNOWN
        ):
            groups["other"].append(entry)
        elif status == StandardStatus.ACTIVE:
            groups["current"].append(entry)
        elif status == StandardStatus.UPCOMING:
            groups["upcoming"].append(entry)
        elif status in (StandardStatus.REPLACED, StandardStatus.ABOLISHED):
            groups["historical"].append(entry)
        else:
            groups["other"].append(entry)

    _sort_entries_desc(groups["current"])
    _sort_entries_upcoming(groups["upcoming"])
    _sort_entries_desc(groups["historical"])
    _sort_entries_desc(groups["other"])

    return (
        groups["current"],
        groups["upcoming"],
        groups["historical"],
        groups["other"],
    )


def match_vision(
    db: Session,
    analysis: VisionAnalysisResponse,
) -> VisionMatchResult:
    matched_categories = match_product_categories(db, analysis)
    detected, unmatched = match_detected_standards(db, analysis)
    current, upcoming, historical, other = match_related_standards(
        db,
        [item.category.id for item in matched_categories],
    )
    return VisionMatchResult(
        detected=detected,
        unmatched=unmatched,
        matched_categories=matched_categories,
        current=current,
        upcoming=upcoming,
        historical=historical,
        other=other,
    )
