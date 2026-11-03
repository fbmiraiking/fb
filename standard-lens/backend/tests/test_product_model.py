from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.product import (
    ProductAlias,
    ReviewStatus,
    StandardProductRelation,
    StandardProductRelationType,
)
from tests.factories import make_category, make_product_relation, make_standard


def test_product_alias_is_unique_within_category(db_session: Session) -> None:
    category = make_category("奶瓶", aliases=("婴儿奶瓶",))
    db_session.add(category)
    db_session.commit()

    category.aliases.append(ProductAlias(alias="婴儿奶瓶"))

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_product_relation_is_unique_per_type(db_session: Session) -> None:
    category = make_category("奶瓶")
    standard = make_standard(standard_no="GB 1200-2024")
    db_session.add_all([category, standard])
    db_session.commit()

    db_session.add(
        make_product_relation(
            standard.id,
            category.id,
            StandardProductRelationType.DIRECT_APPLICABLE,
        )
    )
    db_session.add(
        make_product_relation(
            standard.id,
            category.id,
            StandardProductRelationType.DIRECT_APPLICABLE,
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_product_relation_confidence_must_be_between_zero_and_one(
    db_session: Session,
) -> None:
    category = make_category("奶瓶")
    standard = make_standard(standard_no="GB 1300-2024")
    db_session.add_all([category, standard])
    db_session.commit()

    db_session.add(
        make_product_relation(
            standard.id,
            category.id,
            confidence=Decimal("1.5000"),
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_product_relation_defaults(db_session: Session) -> None:
    category = make_category("奶瓶")
    standard = make_standard(standard_no="GB 1400-2024")
    db_session.add_all([category, standard])
    db_session.commit()

    relation = StandardProductRelation(
        standard_id=standard.id,
        product_category_id=category.id,
        relation_type=StandardProductRelationType.SAFETY,
    )
    db_session.add(relation)
    db_session.commit()
    db_session.refresh(relation)

    assert relation.source_type == "MANUAL"
    assert relation.review_status == ReviewStatus.PENDING
    assert relation.confidence is None
