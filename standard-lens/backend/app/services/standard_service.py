from datetime import date

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.standard import Standard
from app.models.standard_relation import StandardRelation, StandardRelationType
from app.utils.standard_no import StandardNoNormalizer

LINEAGE_RELATION_TYPES = (
    StandardRelationType.REPLACES,
    StandardRelationType.REPLACED_BY,
    StandardRelationType.AMENDS,
    StandardRelationType.AMENDED_BY,
)


def _escape_like(value: str) -> str:
    """Escape SQL LIKE wildcards so user input is always treated literally.

    ``!`` is used as the escape character instead of backslash so the query is
    also safe when MySQL runs with ``NO_BACKSLASH_ESCAPES``.
    """
    return value.replace("!", "!!").replace("%", "!%").replace("_", "!_")


def search_standards(
    db: Session,
    query: str,
    *,
    limit: int,
    offset: int,
) -> tuple[int, list[Standard], str | None]:
    """Search by exact standard number, normalized number, or fuzzy name.

    Returns ``(total, items, normalized_query)`` where ``total`` is the number
    of matches before pagination.
    """
    raw_query = query.strip()
    normalized_query = StandardNoNormalizer.try_normalize(raw_query)
    if not raw_query:
        return 0, [], normalized_query

    lowered_query = raw_query.lower()
    name_pattern = f"%{_escape_like(raw_query)}%"

    conditions = [
        Standard.standard_name.ilike(name_pattern, escape="!"),
        func.lower(Standard.standard_no) == lowered_query,
    ]
    if normalized_query is not None:
        conditions.append(Standard.normalized_no == normalized_query)

    where_clause = or_(*conditions)
    total = db.scalar(
        select(func.count()).select_from(Standard).where(where_clause)
    ) or 0

    statement = select(Standard).where(where_clause)
    if normalized_query is not None:
        relevance = case(
            (Standard.normalized_no == normalized_query, 0),
            (func.lower(Standard.standard_no) == lowered_query, 1),
            else_=2,
        )
        statement = statement.order_by(relevance, Standard.standard_no, Standard.id)
    else:
        statement = statement.order_by(Standard.standard_no, Standard.id)

    statement = statement.limit(limit).offset(offset)
    items = list(db.scalars(statement).all())
    return total, items, normalized_query


def get_standard(db: Session, standard_id: int) -> Standard | None:
    return db.get(Standard, standard_id)


def _version_year(standard: Standard) -> int:
    if standard.standard_year is not None:
        return standard.standard_year
    if standard.effective_date is not None:
        return standard.effective_date.year
    if standard.publish_date is not None:
        return standard.publish_date.year
    return 0


def _version_sort_key(standard: Standard) -> tuple[int, date, date, int]:
    return (
        _version_year(standard),
        standard.effective_date or date.min,
        standard.publish_date or date.min,
        standard.id,
    )


def get_version_chain(db: Session, standard_id: int) -> list[Standard] | None:
    """Return all standards connected through version-lineage relations.

    Traversal is bidirectional and follows REPLACES / REPLACED_BY / AMENDS /
    AMENDED_BY. RELATED edges are intentionally excluded because they are
    "see also" links, not version edges.

    Returns ``None`` when the requested standard does not exist. A standard
    without relations returns a single-item chain containing itself.
    """
    standard = db.get(Standard, standard_id)
    if standard is None:
        return None

    visited: set[int] = {standard_id}
    frontier: set[int] = {standard_id}

    while frontier:
        frontier_ids = list(frontier)
        relations = db.scalars(
            select(StandardRelation).where(
                StandardRelation.relation_type.in_(LINEAGE_RELATION_TYPES),
                or_(
                    StandardRelation.source_standard_id.in_(frontier_ids),
                    StandardRelation.target_standard_id.in_(frontier_ids),
                ),
            )
        ).all()

        next_frontier: set[int] = set()
        for relation in relations:
            if relation.source_standard_id in visited:
                neighbor_id = relation.target_standard_id
            else:
                neighbor_id = relation.source_standard_id

            if neighbor_id not in visited:
                visited.add(neighbor_id)
                next_frontier.add(neighbor_id)

        frontier = next_frontier

    standards = list(
        db.scalars(select(Standard).where(Standard.id.in_(list(visited)))).all()
    )
    return sorted(standards, key=_version_sort_key, reverse=True)
