import enum
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.models.standard import Standard, StandardStatus
from app.models.standard_relation import StandardRelationType
from app.models.sync_task import SyncTask, SyncTaskStatus, utcnow
from app.sync.base import (
    StandardDataSource,
    StandardDetailData,
    StandardListItem,
    StandardRelationData,
)
from app.sync.std_samr import StdSamrDataSource
from app.sync.upsert import upsert_relation, upsert_standard
from app.utils.standard_no import StandardNoNormalizer

logger = logging.getLogger(__name__)

# Guards task creation within one process. Run the API with one worker when the
# in-process scheduler is enabled; see README/deployment notes.
_task_lock = threading.Lock()

# Catalog-only imports upsert tens of thousands of rows. Committing once per
# row is the bottleneck, so batch the commits while keeping progress visible.
CATALOG_COMMIT_BATCH_SIZE = 200

_SOURCE_CLASSES: dict[str, type[StandardDataSource]] = {
    StdSamrDataSource.SOURCE_NAME: StdSamrDataSource,
}


class SyncMode(str, enum.Enum):
    AUTO = "auto"
    FULL = "full"
    INCREMENTAL = "incremental"


class SyncAlreadyRunning(Exception):
    pass


class SyncInitializationRequired(Exception):
    pass


class SyncConfigurationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class SyncStartResult:
    task_id: int
    source: str
    status: SyncTaskStatus
    mode: SyncMode


@dataclass(frozen=True, slots=True)
class _RelationSpec:
    source_standard_id: int
    target_standard_no: str
    target_standard_name: str | None
    target_source_id: str | None
    target_source_url: str | None
    relation_type: StandardRelationType


def source_name_for(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if settings.sync_source not in _SOURCE_CLASSES:
        raise SyncConfigurationError(f"未知的同步数据源: {settings.sync_source}")
    return settings.sync_source


def build_data_source(settings: Settings | None = None) -> StandardDataSource:
    settings = settings or get_settings()
    source_class = _SOURCE_CLASSES.get(settings.sync_source)
    if source_class is None:
        raise SyncConfigurationError(f"未知的同步数据源: {settings.sync_source}")
    if source_class is StdSamrDataSource:
        return StdSamrDataSource(settings)
    return source_class()


def _last_completed_task(db: Session, source: str) -> SyncTask | None:
    return db.scalar(
        select(SyncTask)
        .where(
            SyncTask.source == source,
            SyncTask.status.in_([SyncTaskStatus.SUCCESS, SyncTaskStatus.PARTIAL]),
        )
        .order_by(SyncTask.finished_at.desc(), SyncTask.id.desc())
        .limit(1)
    )


def determine_mode(db: Session, source: str, requested: SyncMode) -> SyncMode:
    if requested is SyncMode.FULL:
        return SyncMode.FULL

    last_task = _last_completed_task(db, source)
    if requested is SyncMode.INCREMENTAL:
        if last_task is None:
            raise SyncInitializationRequired("尚无成功的全量初始化，无法执行增量同步")
        return SyncMode.INCREMENTAL

    return SyncMode.INCREMENTAL if last_task is not None else SyncMode.FULL


def has_completed_sync(db: Session, source: str) -> bool:
    return _last_completed_task(db, source) is not None


def _incremental_since(db: Session, source: str, settings: Settings) -> datetime:
    last_task = _last_completed_task(db, source)
    if last_task is None:
        raise SyncInitializationRequired("尚无成功的全量初始化，无法执行增量同步")
    base = last_task.finished_at or last_task.started_at or utcnow()
    return base - timedelta(hours=max(0, settings.sync_overlap_hours))


def create_sync_task(db: Session, source: str) -> SyncTask:
    """Create a RUNNING task unless another sync for this source is active."""
    with _task_lock:
        running = db.scalar(
            select(SyncTask.id)
            .where(
                SyncTask.source == source,
                SyncTask.status == SyncTaskStatus.RUNNING,
            )
            .limit(1)
        )
        if running is not None:
            raise SyncAlreadyRunning(f"数据源 {source} 已有同步任务正在运行")

        task = SyncTask(
            source=source,
            status=SyncTaskStatus.RUNNING,
            started_at=utcnow(),
            total_count=0,
            success_count=0,
            failed_count=0,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task


def mark_stale_sync_tasks_failed(db: Session) -> int:
    """Mark tasks left RUNNING by a previous process as failed."""
    result = db.execute(
        update(SyncTask)
        .where(SyncTask.status == SyncTaskStatus.RUNNING)
        .values(
            status=SyncTaskStatus.FAILED,
            finished_at=utcnow(),
            error_message="服务重启，同步任务中断",
        )
    )
    db.commit()
    return int(result.rowcount or 0)


def _display_year(code: str, publish_date) -> int | None:
    normalizer_year = None
    try:
        normalized = StandardNoNormalizer.normalize(code)
        suffix = normalized.rsplit("-", 1)[-1]
        if suffix.isdigit() and len(suffix) == 4:
            normalizer_year = int(suffix)
    except ValueError:
        pass
    if normalizer_year is not None:
        return normalizer_year
    return publish_date.year if publish_date is not None else None


def _build_values(
    item: StandardListItem,
    detail: StandardDetailData | None,
    source: str,
) -> dict[str, object]:
    code = detail.standard_no if detail and detail.standard_no else item.standard_no
    normalized_no = StandardNoNormalizer.normalize(code)

    status = item.status
    if detail is not None and detail.status != StandardStatus.UNKNOWN:
        status = detail.status

    publish_date = (
        detail.publish_date
        if detail is not None and detail.publish_date is not None
        else item.publish_date
    )
    effective_date = (
        detail.effective_date
        if detail is not None and detail.effective_date is not None
        else item.effective_date
    )
    standard_type = (
        detail.standard_type if detail is not None and detail.standard_type else item.standard_type
    )
    standard_year = (
        detail.standard_year if detail is not None and detail.standard_year else item.standard_year
    )
    if standard_year is None:
        standard_year = _display_year(code, publish_date)

    return {
        "standard_no": code,
        "normalized_no": normalized_no,
        "standard_name": (
            detail.standard_name if detail is not None and detail.standard_name else item.standard_name
        ),
        "standard_type": standard_type,
        "status": status,
        "publish_date": publish_date,
        "effective_date": effective_date,
        "expiry_date": detail.expiry_date if detail is not None else None,
        "standard_year": standard_year,
        "scope": detail.scope if detail is not None else None,
        "source": source,
        "source_url": (
            detail.source_url if detail is not None and detail.source_url else item.source_url
        ),
    }


def _error_message(
    errors: list[str],
    *,
    extra: list[str] | None = None,
    truncated: bool = False,
) -> str | None:
    lines = list(extra or [])
    lines.extend(errors[:20])
    if len(errors) > 20:
        lines.append(f"... 另有 {len(errors) - 20} 条错误")
    if truncated:
        lines.append("已达到单次同步条数上限，剩余数据将在后续同步中处理")
    if not lines:
        return None
    return "\n".join(lines)[:4000]


def _persist_progress(
    db: Session,
    task: SyncTask,
    *,
    total: int,
    success: int,
    failed: int,
) -> None:
    task.total_count = total
    task.success_count = success
    task.failed_count = failed
    db.commit()


def execute_sync(
    db: Session,
    task: SyncTask,
    source: StandardDataSource,
    mode: SyncMode,
    *,
    settings: Settings | None = None,
    max_items: int | None = None,
    include_details: bool = True,
) -> SyncTask:
    """Execute one task synchronously and update its persistent log.

    ``include_details=False`` performs a catalog-only sync from list rows. It is
    intended for the initial bulk import of tens of thousands of standards,
    where fetching every detail page would take many hours. Existing rows keep
    their detail fields because the upsert preserves optional columns.
    """
    settings = settings or get_settings()
    limit = settings.sync_max_items_per_run if max_items is None else max_items
    limit = max(0, int(limit))
    source_name = source.source_name()

    if task.status != SyncTaskStatus.RUNNING:
        task.status = SyncTaskStatus.RUNNING
        task.started_at = utcnow()
        task.finished_at = None
        db.commit()

    logger.info("sync task %s started: source=%s mode=%s", task.id, source_name, mode.value)

    total = 0
    success = 0
    failed = 0
    truncated = False
    errors: list[str] = []
    relation_specs: list[_RelationSpec] = []
    detailed_normalized: set[str] = set()
    fatal_error: str | None = None

    try:
        if mode is SyncMode.INCREMENTAL:
            since = _incremental_since(db, source_name, settings)
            iterator = source.fetch_updates(since)
        else:
            iterator = source.fetch_list()

        for item in iterator:
            if limit and total >= limit:
                truncated = True
                break

            total += 1
            detail: StandardDetailData | None = None
            item_failed = False

            if include_details:
                try:
                    detail = source.fetch_detail(item)
                except Exception as exc:  # noqa: BLE001 - one item must not kill the run
                    item_failed = True
                    failed += 1
                    message = f"{item.standard_no}: 详情抓取失败: {exc}"
                    errors.append(message)
                    logger.warning("sync task %s %s", task.id, message)

            try:
                values = _build_values(item, detail, source_name)
                standard = upsert_standard(db, values)
                if include_details or total % CATALOG_COMMIT_BATCH_SIZE == 0:
                    db.commit()

                if detail is not None:
                    detailed_normalized.add(standard.normalized_no)
                    for relation in detail.relations:
                        relation_specs.append(
                            _RelationSpec(
                                source_standard_id=standard.id,
                                target_standard_no=relation.target_standard_no,
                                target_standard_name=relation.target_standard_name,
                                target_source_id=relation.target_source_id,
                                target_source_url=relation.target_source_url,
                                relation_type=relation.relation_type,
                            )
                        )
                if not item_failed and (detail is not None or not include_details):
                    success += 1
            except Exception as exc:  # noqa: BLE001 - isolate one bad row
                db.rollback()
                if not item_failed:
                    failed += 1
                message = f"{item.standard_no}: 写入失败: {exc}"
                errors.append(message)
                logger.warning("sync task %s %s", task.id, message)
            finally:
                if include_details or total % CATALOG_COMMIT_BATCH_SIZE == 0:
                    _persist_progress(
                        db,
                        task,
                        total=total,
                        success=success,
                        failed=failed,
                    )
    except Exception as exc:  # noqa: BLE001 - page/transport/database failure
        fatal_error = str(exc)
        logger.exception("sync task %s fatal error: %s", task.id, exc)

    if not include_details:
        _persist_progress(
            db,
            task,
            total=total,
            success=success,
            failed=failed,
        )

    relation_errors: list[str] = []
    if relation_specs:
        seen_edges: set[tuple[int, str, StandardRelationType]] = set()
        for spec in relation_specs:
            key = (spec.source_standard_id, spec.target_standard_no, spec.relation_type)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            try:
                target_normalized = StandardNoNormalizer.normalize(spec.target_standard_no)
                target = db.scalar(
                    select(Standard).where(Standard.normalized_no == target_normalized)
                )

                # A new standard often references an older version that is not
                # in the incremental update window. Refresh that target once so
                # its status/abolition date also follows the source.
                if (
                    (target is None or target.normalized_no not in detailed_normalized)
                    and (spec.target_source_url or spec.target_source_id)
                ):
                    target_item = StandardListItem(
                        source_id=spec.target_source_id or "",
                        standard_no=spec.target_standard_no,
                        standard_name=spec.target_standard_name or "",
                        status=StandardStatus.UNKNOWN,
                        publish_date=None,
                        effective_date=None,
                        standard_type=None,
                        standard_year=None,
                        source_url=spec.target_source_url or "",
                    )
                    try:
                        target_detail = source.fetch_detail(target_item)
                        target_values = _build_values(target_item, target_detail, source_name)
                        target = upsert_standard(db, target_values)
                        db.commit()
                        detailed_normalized.add(target.normalized_no)
                    except Exception as exc:  # noqa: BLE001
                        db.rollback()
                        if target is None:
                            relation_errors.append(
                                f"关系目标抓取失败 {spec.target_standard_no}: {exc}"
                            )
                            continue
                        relation_errors.append(
                            f"关系目标刷新失败 {spec.target_standard_no}: {exc}"
                        )

                if target is None:
                    relation_errors.append(f"关系目标未找到: {spec.target_standard_no}")
                    continue
                if target.id == spec.source_standard_id:
                    continue
                upsert_relation(
                    db,
                    spec.source_standard_id,
                    target.id,
                    spec.relation_type,
                )
                db.commit()
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                message = f"关系写入失败 {spec.target_standard_no}: {exc}"
                relation_errors.append(message)
                logger.warning("sync task %s %s", task.id, message)

    if fatal_error is not None:
        status = SyncTaskStatus.PARTIAL if success > 0 else SyncTaskStatus.FAILED
    elif total > 0 and success == 0 and failed > 0:
        status = SyncTaskStatus.FAILED
    elif failed > 0:
        status = SyncTaskStatus.PARTIAL
    else:
        status = SyncTaskStatus.SUCCESS

    task.total_count = total
    task.success_count = success
    task.failed_count = failed
    task.status = status
    task.finished_at = utcnow()
    task.error_message = _error_message(
        errors + relation_errors,
        extra=[f"[fatal] {fatal_error}"] if fatal_error else None,
        truncated=truncated,
    )
    db.commit()
    db.refresh(task)

    logger.info(
        "sync task %s finished: status=%s total=%d success=%d failed=%d",
        task.id,
        status.value,
        total,
        success,
        failed,
    )
    return task


def run_sync(
    db: Session,
    source: StandardDataSource,
    *,
    mode: SyncMode = SyncMode.AUTO,
    settings: Settings | None = None,
    max_items: int | None = None,
    include_details: bool = True,
) -> tuple[SyncTask, SyncMode]:
    """Synchronous entry point used by tests and command-line tooling."""
    settings = settings or get_settings()
    resolved_mode = determine_mode(db, source.source_name(), mode)
    task = create_sync_task(db, source.source_name())
    execute_sync(
        db,
        task,
        source,
        resolved_mode,
        settings=settings,
        max_items=max_items,
        include_details=include_details,
    )
    return task, resolved_mode


def start_sync(
    db: Session,
    *,
    mode: SyncMode = SyncMode.AUTO,
    settings: Settings | None = None,
) -> SyncStartResult:
    """Create a task and run it in a daemon thread (admin/scheduler entry)."""
    settings = settings or get_settings()
    source_name = source_name_for(settings)
    resolved_mode = determine_mode(db, source_name, mode)
    task = create_sync_task(db, source_name)

    thread = threading.Thread(
        target=_execute_in_background,
        args=(task.id, resolved_mode, settings),
        name=f"standard-sync-{task.id}",
        daemon=True,
    )
    try:
        thread.start()
    except Exception:
        task.status = SyncTaskStatus.FAILED
        task.finished_at = utcnow()
        task.error_message = "同步线程启动失败"
        db.commit()
        raise

    return SyncStartResult(
        task_id=task.id,
        source=source_name,
        status=task.status,
        mode=resolved_mode,
    )


def _execute_in_background(task_id: int, mode: SyncMode, settings: Settings) -> None:
    db = SessionLocal()
    source: StandardDataSource | None = None
    try:
        task = db.get(SyncTask, task_id)
        if task is None:
            logger.error("sync task %s disappeared before execution", task_id)
            return
        source = build_data_source(settings)
        execute_sync(db, task, source, mode, settings=settings)
    except Exception as exc:  # noqa: BLE001 - never lose a task in RUNNING
        logger.exception("background sync task %s failed", task_id)
        try:
            db.rollback()
            task = db.get(SyncTask, task_id)
            if task is not None and task.status == SyncTaskStatus.RUNNING:
                task.status = SyncTaskStatus.FAILED
                task.finished_at = utcnow()
                task.error_message = str(exc)[:4000]
                db.commit()
        except Exception:  # noqa: BLE001
            logger.exception("could not mark sync task %s as failed", task_id)
    finally:
        if source is not None:
            source.close()
        db.close()
