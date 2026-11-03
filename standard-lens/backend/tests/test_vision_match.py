from datetime import date

from sqlalchemy.orm import Session

from app.models.product import ReviewStatus, StandardProductRelationType
from app.models.standard import StandardStatus
from app.schemas.vision import VisionAnalysisResponse
from app.services.vision_match_service import match_vision, status_label
from tests.factories import (
    make_category,
    make_product_relation,
    make_relation,
    make_standard,
)


def _standard(
    standard_no: str,
    name: str,
    status: StandardStatus,
    effective: date,
    expiry: date | None = None,
):
    return make_standard(
        standard_no=standard_no,
        standard_name=name,
        status=status,
        standard_year=effective.year,
        publish_date=date(effective.year, 1, 1),
        effective_date=effective,
        expiry_date=expiry,
    )


def _analysis(**overrides) -> VisionAnalysisResponse:
    values = {
        "product": {
            "name": "婴儿塑料奶瓶",
            "categoryGuess": "婴儿奶瓶",
            "confidence": 0.95,
        },
        "materials": ["PP", "硅胶"],
        "usages": ["婴儿喂养"],
        "visibleText": [
            "GB 1000-2018",
            "GB 2000-2010",
            "生产日期 2024-05-01",
        ],
        "visibleStandardNumbers": [
            "GB 1000-2018",
            "GB 2000-2010",
            "GB 9999-2099",
        ],
        "productionDate": "2024-05-01",
        "manufacturer": "示例公司",
    }
    values.update(overrides)
    return VisionAnalysisResponse.model_validate(values)


def _seed(db_session: Session):
    category = make_category(
        "奶瓶",
        aliases=("婴儿奶瓶", "feeding bottle"),
    )
    material_category = make_category("硅胶制品", aliases=("硅胶",))
    usage_category = make_category("喂养用品", aliases=("婴儿喂养",))

    old = _standard(
        "GB 1000-2018",
        "旧版塑料奶瓶标准",
        StandardStatus.REPLACED,
        date(2018, 7, 1),
        expiry=date(2024, 4, 30),
    )
    current = _standard(
        "GB 1000-2024",
        "现行塑料奶瓶标准",
        StandardStatus.ACTIVE,
        date(2024, 5, 1),
    )
    upcoming = _standard(
        "GB 1000-2027",
        "新版塑料奶瓶标准",
        StandardStatus.UPCOMING,
        date(2027, 7, 1),
    )
    abolished = _standard(
        "GB 2000-2010",
        "已废止标准",
        StandardStatus.ABOLISHED,
        date(2010, 1, 1),
    )

    current_new = _standard(
        "GB 3000-2024",
        "商品现行标准 A",
        StandardStatus.ACTIVE,
        date(2024, 6, 1),
    )
    current_old = _standard(
        "GB 3001-2023",
        "商品现行标准 B",
        StandardStatus.ACTIVE,
        date(2023, 1, 1),
    )
    upcoming_near = _standard(
        "GB 3002-2027",
        "即将实施标准（近）",
        StandardStatus.UPCOMING,
        date(2027, 1, 1),
    )
    upcoming_far = _standard(
        "GB 3003-2027",
        "即将实施标准（远）",
        StandardStatus.UPCOMING,
        date(2027, 8, 1),
    )
    historical_new = _standard(
        "GB 3004-2018",
        "历史标准（较新）",
        StandardStatus.REPLACED,
        date(2018, 7, 1),
    )
    historical_old = _standard(
        "GB 3005-2010",
        "历史标准（较旧）",
        StandardStatus.ABOLISHED,
        date(2010, 1, 1),
    )
    unknown = _standard(
        "GB 3006-2020",
        "状态未知标准",
        StandardStatus.UNKNOWN,
        date(2020, 1, 1),
    )
    possible = _standard(
        "GB 3007-2024",
        "可能相关标准",
        StandardStatus.ACTIVE,
        date(2024, 2, 1),
    )
    rejected = _standard(
        "GB 3008-2024",
        "已驳回关联标准",
        StandardStatus.ACTIVE,
        date(2024, 1, 1),
    )

    db_session.add_all(
        [
            category,
            material_category,
            usage_category,
            old,
            current,
            upcoming,
            abolished,
            current_new,
            current_old,
            upcoming_near,
            upcoming_far,
            historical_new,
            historical_old,
            unknown,
            possible,
            rejected,
        ]
    )
    db_session.commit()

    db_session.add_all(
        [
            make_relation(current.id, old.id),
            make_relation(upcoming.id, current.id),
        ]
    )
    db_session.add_all(
        [
            make_product_relation(
                current_new.id,
                category.id,
                StandardProductRelationType.DIRECT_APPLICABLE,
            ),
            make_product_relation(
                current_old.id,
                category.id,
                StandardProductRelationType.MATERIAL,
            ),
            make_product_relation(
                upcoming_near.id,
                category.id,
                StandardProductRelationType.DIRECT_APPLICABLE,
            ),
            make_product_relation(
                upcoming_far.id,
                category.id,
                StandardProductRelationType.DIRECT_APPLICABLE,
            ),
            make_product_relation(
                historical_new.id,
                category.id,
                StandardProductRelationType.DIRECT_APPLICABLE,
            ),
            make_product_relation(
                historical_old.id,
                category.id,
                StandardProductRelationType.SAFETY,
            ),
            make_product_relation(
                unknown.id,
                category.id,
                StandardProductRelationType.GENERAL,
            ),
            make_product_relation(
                possible.id,
                category.id,
                StandardProductRelationType.POSSIBLE,
            ),
            make_product_relation(
                rejected.id,
                category.id,
                StandardProductRelationType.DIRECT_APPLICABLE,
                review_status=ReviewStatus.REJECTED,
            ),
        ]
    )
    db_session.commit()
    return category, material_category, usage_category, old, current, upcoming, abolished


def test_match_vision_detects_standards_and_explains_old_versions(
    db_session: Session,
) -> None:
    _, _, _, old, current, _, abolished = _seed(db_session)

    result = match_vision(db_session, _analysis())

    assert [item.category.name for item in result.matched_categories] == [
        "奶瓶",
        "喂养用品",
        "硅胶制品",
    ]

    assert len(result.detected) == 2
    old_result = next(
        item for item in result.detected if item.standard.id == old.id
    )
    assert old_result.status_label == "旧标准"
    assert old_result.standard.is_historical is True
    assert [item.id for item in old_result.replaced_by] == [current.id]
    assert [item.id for item in old_result.latest_current] == [current.id]
    assert "旧标准" in old_result.notice
    assert "2018-07-01" in old_result.notice
    assert "GB 1000-2024" in old_result.notice
    assert "当前最新现行标准" in old_result.notice

    abolished_result = next(
        item for item in result.detected if item.standard.id == abolished.id
    )
    assert abolished_result.status_label == "已废止"
    assert abolished_result.replaced_by == []
    assert abolished_result.latest_current == []
    assert "已废止" in abolished_result.notice
    assert "2010-01-01" in abolished_result.notice

    assert result.unmatched == ["GB 9999-2099"]
    assert all(
        item.standard.standard_no != "GB 9999-2099"
        for item in result.detected
    )


def test_match_vision_groups_and_sorts_related_standards(
    db_session: Session,
) -> None:
    _seed(db_session)

    result = match_vision(db_session, _analysis())

    assert [entry.standard.standard_no for entry in result.current] == [
        "GB 3000-2024",
        "GB 3001-2023",
    ]
    assert [entry.standard.standard_no for entry in result.upcoming] == [
        "GB 3002-2027",
        "GB 3003-2027",
    ]
    assert [entry.standard.standard_no for entry in result.historical] == [
        "GB 3004-2018",
        "GB 3005-2010",
    ]
    assert [entry.standard.standard_no for entry in result.other] == [
        "GB 3007-2024",
        "GB 3006-2020",
    ]

    assert all(
        entry.relation.relation_type == StandardProductRelationType.POSSIBLE
        for entry in result.other
        if entry.standard.standard_no == "GB 3007-2024"
    )
    assert all(
        entry.standard.standard_no != "GB 3008-2024"
        for entry in result.current
    )


def test_status_labels() -> None:
    assert status_label(StandardStatus.ACTIVE) == "当前现行"
    assert status_label(StandardStatus.UPCOMING) == "即将实施"
    assert status_label(StandardStatus.REPLACED) == "旧标准"
    assert status_label(StandardStatus.ABOLISHED) == "已废止"
    assert status_label(StandardStatus.UNKNOWN) == "状态未知"


def test_match_vision_without_product_matches(db_session: Session) -> None:
    standard = _standard(
        "GB 4000-2024",
        "无商品分类标准",
        StandardStatus.ACTIVE,
        date(2024, 5, 1),
    )
    db_session.add(standard)
    db_session.commit()

    analysis = _analysis(
        product={"name": "完全不同的商品", "categoryGuess": "", "confidence": 0.5},
        materials=[],
        usages=[],
        visibleText=["GB 4000-2024"],
        visibleStandardNumbers=["GB 4000-2024"],
    )
    result = match_vision(db_session, analysis)

    assert result.matched_categories == []
    assert result.current == []
    assert result.upcoming == []
    assert result.historical == []
    assert result.other == []
    assert len(result.detected) == 1
    assert result.detected[0].status_label == "当前现行"
