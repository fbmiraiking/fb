from datetime import date

from sqlalchemy.orm import Session

from app.models.requirement import RequirementType
from app.models.standard import StandardStatus
from app.schemas.vision import VisionAnalysisResponse
from app.services.requirement_verification_service import (
    VERIFICATION_DISCLAIMER,
    RequirementCheckStatus,
    evaluate_requirement,
    verify_detected_standards,
)
from app.services.vision_match_service import DetectedStandardResult
from tests.factories import make_requirement, make_standard


def _analysis(**overrides) -> VisionAnalysisResponse:
    values = {
        "product": {
            "name": "婴儿塑料奶瓶",
            "category_guess": "婴儿奶瓶",
            "confidence": 0.95,
        },
        "materials": ["PP", "硅胶"],
        "usages": ["婴儿喂养"],
        "visible_text": [
            "执行标准：GB 1000-2018",
            "生产厂家：示例塑料制品有限公司",
            "净含量：250mL",
            "生产日期 2024-05-01",
        ],
        "visible_standard_numbers": ["GB 1000-2018"],
        "production_date": "2024-05-01",
        "manufacturer": "示例塑料制品有限公司",
    }
    values.update(overrides)
    return VisionAnalysisResponse.model_validate(values)


def test_requirement_types_have_safe_image_boundaries() -> None:
    analysis = _analysis()

    visual = evaluate_requirement(
        make_requirement(
            1,
            chapter="4.1",
            requirement_type=RequirementType.VISUAL,
            requirement_text="产品外观应清洁、无破损。",
        ),
        analysis,
    )
    assert visual.status == RequirementCheckStatus.PARTIAL
    assert visual.image_checkable is True

    label = evaluate_requirement(
        make_requirement(
            1,
            chapter="4.2",
            requirement_type=RequirementType.LABEL,
            requirement_text="包装上应标注执行标准号。",
        ),
        analysis,
    )
    assert label.status == RequirementCheckStatus.OBSERVED
    assert label.evidence == ["可见标准号：GB 1000-2018"]
    assert label.image_checkable is True

    document = evaluate_requirement(
        make_requirement(
            1,
            chapter="5.1",
            requirement_type=RequirementType.DOCUMENT,
            requirement_text="应提供符合性声明。",
        ),
        analysis,
    )
    assert document.status == RequirementCheckStatus.NEEDS_DOCUMENT
    assert document.image_checkable is False

    lab_test = evaluate_requirement(
        make_requirement(
            1,
            chapter="5.2",
            requirement_type=RequirementType.LAB_TEST,
            requirement_text="材料迁移量应符合限量要求。",
        ),
        analysis,
    )
    assert lab_test.status == RequirementCheckStatus.NOT_POSSIBLE
    assert lab_test.image_checkable is False
    assert "无法通过图片判断" in lab_test.message

    measurement = evaluate_requirement(
        make_requirement(
            1,
            chapter="5.3",
            requirement_type=RequirementType.MEASUREMENT,
            requirement_text="瓶口直径应为 40 mm。",
        ),
        analysis,
    )
    assert measurement.status == RequirementCheckStatus.CANNOT_VERIFY
    assert measurement.image_checkable is False
    assert "无法确认测量条件" in measurement.message


def test_measurement_without_values_says_cannot_judge() -> None:
    result = evaluate_requirement(
        make_requirement(
            1,
            requirement_type=RequirementType.MEASUREMENT,
            requirement_text="瓶口直径应为 40 mm。",
        ),
        _analysis(visible_text=[], visible_standard_numbers=[]),
    )

    assert result.status == RequirementCheckStatus.CANNOT_VERIFY
    assert result.evidence == []
    assert "没有可靠测量信息，无法判断" in result.message


def test_lab_terms_in_visual_requirement_are_not_claimed_from_image() -> None:
    result = evaluate_requirement(
        make_requirement(
            1,
            requirement_type=RequirementType.VISUAL,
            requirement_text="重金属迁移量应符合限量要求。",
        ),
        _analysis(),
    )

    assert result.status == RequirementCheckStatus.CANNOT_VERIFY
    assert "实验检测" in result.message


def test_label_requirement_without_evidence_is_not_observed() -> None:
    result = evaluate_requirement(
        make_requirement(
            1,
            requirement_type=RequirementType.LABEL,
            requirement_text="包装上应标注生产厂家名称。",
        ),
        _analysis(
            product={"name": "", "categoryGuess": "", "confidence": 0},
            materials=[],
            usages=[],
            visible_text=[],
            visible_standard_numbers=[],
            manufacturer=None,
            production_date=None,
        ),
    )

    assert result.status == RequirementCheckStatus.NOT_OBSERVED
    assert "照片未拍到不代表商品不符合" in result.message


def test_verify_detected_standards_orders_and_groups(db_session: Session) -> None:
    old = make_standard(
        standard_no="GB 1000-2018",
        standard_name="旧版塑料奶瓶标准",
        status=StandardStatus.REPLACED,
        effective_date=date(2018, 7, 1),
        standard_year=2018,
    )
    current = make_standard(
        standard_no="GB 1000-2024",
        standard_name="现行塑料奶瓶标准",
        status=StandardStatus.ACTIVE,
        effective_date=date(2024, 5, 1),
        standard_year=2024,
    )
    other = make_standard(
        standard_no="GB 2000-2020",
        standard_name="无要求标准",
        status=StandardStatus.ACTIVE,
        effective_date=date(2020, 1, 1),
        standard_year=2020,
    )
    db_session.add_all([old, current, other])
    db_session.commit()

    requirements = [
        make_requirement(
            old.id,
            "5.3",
            RequirementType.MEASUREMENT,
            "瓶口直径应为 40 mm。",
        ),
        make_requirement(
            old.id,
            "5.2",
            RequirementType.LAB_TEST,
            "材料迁移量应符合限量要求。",
        ),
        make_requirement(
            old.id,
            "5.1",
            RequirementType.DOCUMENT,
            "应提供符合性声明或检测报告。",
        ),
        make_requirement(
            old.id,
            "4.10",
            RequirementType.VISUAL,
            "产品外观应清洁、无破损。",
        ),
        make_requirement(
            old.id,
            "4.3",
            RequirementType.LABEL,
            "应标注净含量。",
        ),
        make_requirement(
            old.id,
            "4.2",
            RequirementType.LABEL,
            "包装上应标注生产厂家名称。",
        ),
        make_requirement(
            old.id,
            "4.1",
            RequirementType.LABEL,
            "包装上应标注执行标准号。",
        ),
    ]
    db_session.add_all(requirements)
    db_session.commit()

    detected = DetectedStandardResult(
        standard=old,
        status_label="旧标准",
        replaced_by=[current],
        latest_current=[current],
        notice="图片上的标准 GB 1000-2018 是旧标准。",
    )
    result = verify_detected_standards(
        db_session,
        _analysis(),
        [
            detected,
            DetectedStandardResult(
                standard=other,
                status_label="当前现行",
                replaced_by=[],
                latest_current=[other],
                notice="当前为现行标准。",
            ),
        ],
    )

    assert len(result) == 2
    first = result[0]
    assert first.standard.id == old.id
    assert [item.requirement.chapter for item in first.requirements] == [
        "4.1",
        "4.2",
        "4.3",
        "4.10",
        "5.1",
        "5.2",
        "5.3",
    ]
    statuses = [item.status for item in first.requirements]
    assert statuses[:4] == [
        RequirementCheckStatus.OBSERVED,
        RequirementCheckStatus.OBSERVED,
        RequirementCheckStatus.OBSERVED,
        RequirementCheckStatus.PARTIAL,
    ]
    assert statuses[4:] == [
        RequirementCheckStatus.NEEDS_DOCUMENT,
        RequirementCheckStatus.NOT_POSSIBLE,
        RequirementCheckStatus.CANNOT_VERIFY,
    ]
    assert first.observed_count == 3
    assert first.partial_count == 1
    assert first.external_check_count == 3
    assert [item.id for item in first.replacement_standards] == [current.id]
    assert first.lifecycle_notice == "图片上的标准 GB 1000-2018 是旧标准。"
    assert "图片可核对 7 项要求" in first.summary
    assert (
        VERIFICATION_DISCLAIMER
        == "图片分析只能辅助核对可见信息，不能替代实验检测、检测报告或合规认证。"
    )

    second = result[1]
    assert second.requirements == []
    assert second.summary == "标准库暂未录入该标准的图片核验要求。"
