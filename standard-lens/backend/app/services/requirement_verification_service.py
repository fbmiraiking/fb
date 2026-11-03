import enum
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.requirement import RequirementType, StandardRequirement
from app.models.standard import Standard
from app.schemas.vision import VisionAnalysisResponse
from app.services.vision_match_service import DetectedStandardResult

VERIFICATION_DISCLAIMER = (
    "图片分析只能辅助核对可见信息，不能替代实验检测、检测报告或合规认证。"
)

MAX_EVIDENCE_ITEMS = 5


class RequirementCheckStatus(str, enum.Enum):
    OBSERVED = "OBSERVED"
    PARTIAL = "PARTIAL"
    NOT_OBSERVED = "NOT_OBSERVED"
    NEEDS_DOCUMENT = "NEEDS_DOCUMENT"
    NOT_POSSIBLE = "NOT_POSSIBLE"
    CANNOT_VERIFY = "CANNOT_VERIFY"


STATUS_LABELS: dict[RequirementCheckStatus, str] = {
    RequirementCheckStatus.OBSERVED: "图片中可见",
    RequirementCheckStatus.PARTIAL: "部分可见，需人工核对",
    RequirementCheckStatus.NOT_OBSERVED: "图片中未观察到",
    RequirementCheckStatus.NEEDS_DOCUMENT: "需要证书或文档",
    RequirementCheckStatus.NOT_POSSIBLE: "无法通过图片判断",
    RequirementCheckStatus.CANNOT_VERIFY: "无法判断",
}

EXTERNAL_STATUSES = frozenset(
    {
        RequirementCheckStatus.NEEDS_DOCUMENT,
        RequirementCheckStatus.NOT_POSSIBLE,
        RequirementCheckStatus.CANNOT_VERIFY,
    }
)

_STANDARD_TERMS = (
    "执行标准",
    "标准号",
    "标准编号",
    "产品标准",
    "标准代号",
)
_MANUFACTURER_TERMS = (
    "生产厂家",
    "制造商",
    "生产企业",
    "生产者",
    "生产商",
    "厂名",
    "出品方",
)
_PRODUCTION_TERMS = (
    "生产日期",
    "制造日期",
    "保质期",
    "有效期",
    "限用日期",
)
_NET_CONTENT_TERMS = ("净含量", "规格", "容量", "数量", "重量")
_ADDRESS_TERMS = ("地址", "住所", "产地", "生产地址")
_INGREDIENT_TERMS = ("成分", "配料", "材质", "材料", "原料")
_WARNING_TERMS = ("警示", "警告", "注意")
_AGE_TERMS = ("适用年龄", "年龄", "适用人群", "适用范围")

_LAB_ONLY_TERMS = (
    "迁移量",
    "重金属",
    "微生物",
    "菌落",
    "甲醛释放",
    "有害物质限量",
    "溶剂残留",
    "检测方法",
    "实验室检测",
)

_STANDARD_NO_RE = re.compile(
    r"(?:GB(?:/T)?|QB/T|YY/T|SN/T|ISO|IEC|EN)\s*[\d.]+(?:[-—–]\d{4})?",
    re.IGNORECASE,
)
_MANUFACTURER_RE = re.compile(
    r"[^\s，,。；;：:]{2,}(?:有限公司|股份有限公司|集团|厂|制造商|生产企业)"
)
_PRODUCTION_RE = re.compile(
    r"(?:生产日期|制造日期|保质期至|有效期至|限用日期)"
    r"[:：\s]*[0-9]{4}[-年./][0-9]{1,2}(?:[-月./][0-9]{1,2}日?)?"
)
_NET_CONTENT_RE = re.compile(
    r"(?:净含量|规格|容量|重量)"
    r"[:：\s]*[0-9.]+\s*(?:ml|mL|L|g|kg|克|千克|毫升|升|个|件|片)"
)
_ADDRESS_RE = re.compile(r"(?:地址|住所|产地|生产地址)[:：\s]*[^\n，,；;]{2,}")
_INGREDIENT_RE = re.compile(r"(?:成分|配料|材质|材料|原料)[:：\s]*[^\n]{1,}")
_WARNING_RE = re.compile(r"(?:警示|警告|注意)[^\n]{0,80}")
_AGE_RE = re.compile(r"(?:适用年龄|年龄|适用人群|适用范围)[^\n]{0,80}")
_MEASUREMENT_RE = re.compile(
    r"[0-9]+(?:\.[0-9]+)?\s*"
    r"(?:mm|cm|mL|ml|mg|kg|MPa|℃|°C|Pa|N|g|m|L|%|次|层)"
)


@dataclass(frozen=True, slots=True)
class RequirementCheckResult:
    requirement: StandardRequirement
    status: RequirementCheckStatus
    status_label: str
    image_checkable: bool
    evidence: list[str]
    message: str


@dataclass(frozen=True, slots=True)
class StandardVerificationResult:
    standard: Standard
    replacement_standards: list[Standard]
    latest_current: list[Standard]
    lifecycle_notice: str
    requirements: list[RequirementCheckResult]
    observed_count: int
    partial_count: int
    not_observed_count: int
    external_check_count: int
    summary: str


@dataclass(frozen=True, slots=True)
class _EvidenceCheck:
    found: bool
    detail: str


def _visible_lines(analysis: VisionAnalysisResponse) -> list[str]:
    return [line for line in analysis.visible_text if line]


def _first_match(pattern: re.Pattern[str], lines: list[str]) -> str | None:
    for line in lines:
        match = pattern.search(line)
        if match:
            return match.group(0).strip()
    return None


def _evidence_checks(
    requirement_text: str,
    analysis: VisionAnalysisResponse,
) -> list[_EvidenceCheck]:
    lines = _visible_lines(analysis)
    checks: list[_EvidenceCheck] = []

    if any(term in requirement_text for term in _STANDARD_TERMS):
        numbers = analysis.visible_standard_numbers
        if numbers:
            checks.append(
                _EvidenceCheck(True, f"可见标准号：{'、'.join(numbers[:MAX_EVIDENCE_ITEMS])}")
            )
        else:
            found = _first_match(_STANDARD_NO_RE, lines)
            checks.append(
                _EvidenceCheck(
                    bool(found),
                    f"可见标准号：{found}" if found else "未在图片文字中观察到标准号",
                )
            )

    if any(term in requirement_text for term in _MANUFACTURER_TERMS):
        manufacturer = analysis.manufacturer
        found = manufacturer or _first_match(_MANUFACTURER_RE, lines)
        checks.append(
            _EvidenceCheck(
                bool(found),
                f"可见生产厂家：{found}" if found else "未在图片文字中观察到生产厂家",
            )
        )

    if any(term in requirement_text for term in _PRODUCTION_TERMS):
        production = analysis.production_date
        found = production or _first_match(_PRODUCTION_RE, lines)
        checks.append(
            _EvidenceCheck(
                bool(found),
                f"可见日期：{found}" if found else "未在图片文字中观察到生产日期或有效期",
            )
        )

    if any(term in requirement_text for term in _NET_CONTENT_TERMS):
        found = _first_match(_NET_CONTENT_RE, lines)
        checks.append(
            _EvidenceCheck(
                bool(found),
                f"可见规格/净含量：{found}" if found else "未在图片文字中观察到净含量或规格",
            )
        )

    if any(term in requirement_text for term in _ADDRESS_TERMS):
        found = _first_match(_ADDRESS_RE, lines)
        checks.append(
            _EvidenceCheck(
                bool(found),
                f"可见地址信息：{found}" if found else "未在图片文字中观察到地址信息",
            )
        )

    if any(term in requirement_text for term in _INGREDIENT_TERMS):
        found = "、".join(analysis.materials) or _first_match(_INGREDIENT_RE, lines)
        checks.append(
            _EvidenceCheck(
                bool(found),
                f"可见材质/成分：{found}" if found else "未在图片文字中观察到材质或成分",
            )
        )

    if any(term in requirement_text for term in _WARNING_TERMS):
        found = _first_match(_WARNING_RE, lines)
        checks.append(
            _EvidenceCheck(
                bool(found),
                f"可见警示语：{found}" if found else "未在图片文字中观察到警示语",
            )
        )

    if any(term in requirement_text for term in _AGE_TERMS):
        found = _first_match(_AGE_RE, lines)
        checks.append(
            _EvidenceCheck(
                bool(found),
                f"可见适用信息：{found}" if found else "未在图片文字中观察到适用年龄或范围",
            )
        )

    return checks


def _observable_summary(analysis: VisionAnalysisResponse) -> list[str]:
    items: list[str] = []
    if analysis.product.name:
        items.append(f"商品名称：{analysis.product.name}")
    if analysis.product.category_guess:
        items.append(f"商品类别：{analysis.product.category_guess}")
    if analysis.materials:
        items.append(f"材质：{'、'.join(analysis.materials[:MAX_EVIDENCE_ITEMS])}")
    if analysis.usages:
        items.append(f"用途：{'、'.join(analysis.usages[:MAX_EVIDENCE_ITEMS])}")
    if analysis.visible_text:
        items.append(f"标签文字 {len(analysis.visible_text)} 条")
    return items


def _check_observable(
    requirement: StandardRequirement,
    analysis: VisionAnalysisResponse,
) -> RequirementCheckResult:
    text = requirement.requirement_text

    if any(term in text for term in _LAB_ONLY_TERMS):
        return _result(
            requirement,
            RequirementCheckStatus.CANNOT_VERIFY,
            [],
            "该要求涉及实验检测指标，无法通过图片判断。",
        )

    checks = _evidence_checks(text, analysis)
    if checks:
        found = [item.detail for item in checks if item.found]
        missing = [item.detail for item in checks if not item.found]
        if found and not missing:
            return _result(
                requirement,
                RequirementCheckStatus.OBSERVED,
                found,
                "AI 辅助：图片中可见上述信息；仅代表图片可见内容，不代表商品满足该标准的全部要求。",
            )
        if found and missing:
            return _result(
                requirement,
                RequirementCheckStatus.PARTIAL,
                found,
                "AI 辅助：图片中可见部分信息，仍有信息未观察到，需人工对照标准原文核对。",
            )
        return _result(
            requirement,
            RequirementCheckStatus.NOT_OBSERVED,
            [],
            "图片中未观察到该项信息；照片未拍到不代表商品不符合，需人工核对。",
        )

    observable = _observable_summary(analysis)
    if observable:
        return _result(
            requirement,
            RequirementCheckStatus.PARTIAL,
            observable,
            "AI 辅助：图片中可见部分商品或标签信息，但无法确认是否完整满足该要求，需人工核对。",
        )
    return _result(
        requirement,
        RequirementCheckStatus.NOT_OBSERVED,
        [],
        "图片中未观察到可用于核对该要求的信息，需人工核对。",
    )


def _result(
    requirement: StandardRequirement,
    status: RequirementCheckStatus,
    evidence: list[str],
    message: str,
) -> RequirementCheckResult:
    return RequirementCheckResult(
        requirement=requirement,
        status=status,
        status_label=STATUS_LABELS[status],
        image_checkable=requirement.requirement_type
        in (RequirementType.VISUAL, RequirementType.LABEL)
        and status not in EXTERNAL_STATUSES,
        evidence=evidence[:MAX_EVIDENCE_ITEMS],
        message=message,
    )


def _measurement_values(analysis: VisionAnalysisResponse) -> list[str]:
    values: list[str] = []
    for line in _visible_lines(analysis):
        for match in _MEASUREMENT_RE.findall(line):
            if match not in values:
                values.append(match)
    return values


def evaluate_requirement(
    requirement: StandardRequirement,
    analysis: VisionAnalysisResponse,
) -> RequirementCheckResult:
    requirement_type = requirement.requirement_type

    if requirement_type == RequirementType.DOCUMENT:
        return _result(
            requirement,
            RequirementCheckStatus.NEEDS_DOCUMENT,
            [],
            "需要提供证书、检测报告或合规文件，图片无法核验。",
        )
    if requirement_type == RequirementType.LAB_TEST:
        return _result(
            requirement,
            RequirementCheckStatus.NOT_POSSIBLE,
            [],
            "无法通过图片判断，需要按标准方法进行实验室检测。",
        )
    if requirement_type == RequirementType.MEASUREMENT:
        values = _measurement_values(analysis)
        if values:
            return _result(
                requirement,
                RequirementCheckStatus.CANNOT_VERIFY,
                [f"图片中可见数值：{'、'.join(values[:MAX_EVIDENCE_ITEMS])}"],
                "图片中有数值信息，但无法确认测量条件、工具与精度，无法判断。",
            )
        return _result(
            requirement,
            RequirementCheckStatus.CANNOT_VERIFY,
            [],
            "没有可靠测量信息，无法判断；需要按标准方法测量。",
        )
    return _check_observable(requirement, analysis)


def _chapter_key(chapter: str) -> tuple[tuple[int, object], ...]:
    parts = re.split(r"(\d+)", chapter or "")
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in parts
        if part
    )


def _summary(checks: list[RequirementCheckResult]) -> str:
    if not checks:
        return "标准库暂未录入该标准的图片核验要求。"
    observed = sum(
        1 for item in checks if item.status == RequirementCheckStatus.OBSERVED
    )
    partial = sum(
        1 for item in checks if item.status == RequirementCheckStatus.PARTIAL
    )
    not_observed = sum(
        1 for item in checks if item.status == RequirementCheckStatus.NOT_OBSERVED
    )
    external = sum(1 for item in checks if item.status in EXTERNAL_STATUSES)
    parts = [f"图片可核对 {len(checks)} 项要求", f"{observed} 项在图片中可见"]
    if partial:
        parts.append(f"{partial} 项仅部分可见")
    if not_observed:
        parts.append(f"{not_observed} 项未观察到")
    if external:
        parts.append(f"{external} 项需证书、实验或测量")
    return "：".join((parts[0], "，".join(parts[1:]))) + "。"


def verify_detected_standards(
    db: Session,
    analysis: VisionAnalysisResponse,
    detected: list[DetectedStandardResult],
) -> list[StandardVerificationResult]:
    """Evaluate DB requirements against image-visible evidence only."""
    if not detected:
        return []

    standard_ids = [item.standard.id for item in detected]
    rows = list(
        db.scalars(
            select(StandardRequirement).where(
                StandardRequirement.standard_id.in_(standard_ids)
            )
        ).all()
    )

    grouped: dict[int, list[StandardRequirement]] = {sid: [] for sid in standard_ids}
    for requirement in rows:
        grouped.setdefault(requirement.standard_id, []).append(requirement)

    results: list[StandardVerificationResult] = []
    for item in detected:
        requirements = sorted(
            grouped.get(item.standard.id, []),
            key=lambda requirement: (
                _chapter_key(requirement.chapter),
                requirement.id,
            ),
        )
        checks = [evaluate_requirement(requirement, analysis) for requirement in requirements]
        observed_count = sum(
            1 for check in checks if check.status == RequirementCheckStatus.OBSERVED
        )
        partial_count = sum(
            1 for check in checks if check.status == RequirementCheckStatus.PARTIAL
        )
        not_observed_count = sum(
            1 for check in checks if check.status == RequirementCheckStatus.NOT_OBSERVED
        )
        external_check_count = sum(
            1 for check in checks if check.status in EXTERNAL_STATUSES
        )
        results.append(
            StandardVerificationResult(
                standard=item.standard,
                replacement_standards=item.replaced_by,
                latest_current=item.latest_current,
                lifecycle_notice=item.notice,
                requirements=checks,
                observed_count=observed_count,
                partial_count=partial_count,
                not_observed_count=not_observed_count,
                external_check_count=external_check_count,
                summary=_summary(checks),
            )
        )
    return results
