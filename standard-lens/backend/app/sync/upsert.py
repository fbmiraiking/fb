"""Dialect-aware upsert helpers for standards and relations."""

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.models.standard import Standard, StandardStatus
from app.models.standard_relation import StandardRelation, StandardRelationType
from app.models.sync_task import utcnow

# When a source omits an optional field, keep whatever is already stored.
_OPTIONAL_COLUMNS = {
    "standard_type",
    "publish_date",
    "effective_date",
    "expiry_date",
    "standard_year",
    "scope",
    "source_url",
}


def upsert_standard(db: Session, values: dict[str, object]) -> Standard:
    """Insert or update a standard by its unique ``normalized_no``."""
    normalized_no = values["normalized_no"]
    status = values.get("status", StandardStatus.UNKNOWN)
    dialect = db.get_bind().dialect.name

    if dialect == "mysql":
        statement = mysql_insert(Standard).values(**values)
        updates: dict[str, object] = {}
        for key, value in values.items():
            if key == "normalized_no":
                continue
            if key == "status":
                updates[key] = (
                    Standard.status
                    if value == StandardStatus.UNKNOWN
                    else getattr(statement.inserted, key)
                )
            elif key in _OPTIONAL_COLUMNS:
                updates[key] = func.coalesce(
                    getattr(statement.inserted, key),
                    getattr(Standard, key),
                )
            else:
                updates[key] = getattr(statement.inserted, key)
        updates["updated_at"] = func.now()
        db.execute(statement.on_duplicate_key_update(**updates))
    elif dialect == "sqlite":
        statement = sqlite_insert(Standard).values(**values)
        updates = {}
        for key, value in values.items():
            if key == "normalized_no":
                continue
            if key == "status":
                updates[key] = (
                    Standard.status
                    if value == StandardStatus.UNKNOWN
                    else getattr(statement.excluded, key)
                )
            elif key in _OPTIONAL_COLUMNS:
                updates[key] = func.coalesce(
                    getattr(statement.excluded, key),
                    getattr(Standard, key),
                )
            else:
                updates[key] = getattr(statement.excluded, key)
        updates["updated_at"] = func.now()
        db.execute(
            statement.on_conflict_do_update(
                index_elements=[Standard.normalized_no],
                set_=updates,
            )
        )
    else:
        existing = db.scalar(
            select(Standard).where(Standard.normalized_no == normalized_no)
        )
        if existing is None:
            db.add(Standard(**values))
        else:
            for key, value in values.items():
                if key == "normalized_no":
                    continue
                if key == "status" and value == StandardStatus.UNKNOWN:
                    continue
                if value is not None or key == "status":
                    setattr(existing, key, value)
            existing.updated_at = utcnow()
        db.flush()

    standard = db.scalar(
        select(Standard)
        .where(Standard.normalized_no == normalized_no)
        .execution_options(populate_existing=True)
    )
    if standard is None:
        raise RuntimeError(f"upsert 后未找到标准: {normalized_no!r}")
    return standard


def upsert_relation(
    db: Session,
    source_standard_id: int,
    target_standard_id: int,
    relation_type: StandardRelationType,
) -> None:
    """Insert a relation if the same directed edge does not exist already."""
    values = {
        "source_standard_id": source_standard_id,
        "target_standard_id": target_standard_id,
        "relation_type": relation_type,
    }
    dialect = db.get_bind().dialect.name

    if dialect == "mysql":
        statement = mysql_insert(StandardRelation).values(**values)
        db.execute(
            statement.on_duplicate_key_update(
                relation_type=statement.inserted.relation_type,
            )
        )
    elif dialect == "sqlite":
        statement = sqlite_insert(StandardRelation).values(**values)
        db.execute(
            statement.on_conflict_do_nothing(
                index_elements=[
                    StandardRelation.source_standard_id,
                    StandardRelation.target_standard_id,
                    StandardRelation.relation_type,
                ]
            )
        )
    else:
        existing = db.scalar(
            select(StandardRelation).where(
                StandardRelation.source_standard_id == source_standard_id,
                StandardRelation.target_standard_id == target_standard_id,
                StandardRelation.relation_type == relation_type,
            )
        )
        if existing is None:
            db.add(StandardRelation(**values))
            db.flush()
