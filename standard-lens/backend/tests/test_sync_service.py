from datetime import date, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.standard import Standard, StandardStatus
from app.models.standard_relation import StandardRelation, StandardRelationType
from app.models.sync_task import SyncTask, SyncTaskStatus, utcnow
from app.sync.base import (
    DataSourceError,
    StandardDataSource,
    StandardDetailData,
    StandardListItem,
    StandardRelationData,
)
from app.sync.service import (
    SyncAlreadyRunning,
    SyncInitializationRequired,
    SyncMode,
    mark_stale_sync_tasks_failed,
    run_sync,
)


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "sync_overlap_hours": 0,
        "sync_max_items_per_run": 0,
        "sync_request_interval_seconds": 0.0,
    }
    values.update(overrides)
    return Settings(**values)


def make_item(
    standard_no: str,
    name: str,
    status: StandardStatus = StandardStatus.ACTIVE,
) -> StandardListItem:
    return StandardListItem(
        source_id=standard_no.replace(" ", "").replace("-", ""),
        standard_no=standard_no,
        standard_name=name,
        status=status,
        publish_date=date(2024, 1, 1),
        effective_date=date(2024, 5, 1),
        standard_type="GB",
        standard_year=2024,
        source_url=f"https://std.samr.gov.cn/gb/search/gbDetailed?id={standard_no}",
    )


def make_detail(
    standard_no: str,
    name: str,
    status: StandardStatus = StandardStatus.ACTIVE,
    relations: tuple[StandardRelationData, ...] = (),
    expiry_date: date | None = None,
) -> StandardDetailData:
    return StandardDetailData(
        source_id=standard_no.replace(" ", "").replace("-", ""),
        standard_no=standard_no,
        standard_name=name,
        status=status,
        publish_date=date(2024, 1, 1),
        effective_date=date(2024, 5, 1),
        expiry_date=expiry_date,
        standard_type="GB",
        standard_year=2024,
        scope=None,
        source_url=f"https://std.samr.gov.cn/gb/search/gbDetailed?id={standard_no}",
        relations=relations,
    )


class FakeSource(StandardDataSource):
    def __init__(self, items, details) -> None:
        self.items = list(items)
        self.details = dict(details)
        self.updates: list[StandardListItem] = []
        self.list_calls = 0
        self.update_calls: list[datetime] = []
        self.fail_detail_for: set[str] = set()
        self.fail_list = False

    def source_name(self) -> str:
        return "fake"

    def fetch_list(self):
        self.list_calls += 1
        if self.fail_list:
            raise DataSourceError("list failed")
        yield from self.items

    def fetch_detail(self, item: StandardListItem) -> StandardDetailData:
        if item.standard_no in self.fail_detail_for:
            raise DataSourceError("detail failed")
        return self.details[item.standard_no]

    def fetch_updates(self, since: datetime):
        self.update_calls.append(since)
        yield from self.updates


def test_first_sync_is_full_upserts_and_writes_relations(db_session: Session) -> None:
    old = make_item("GB 1000-2018", "旧标准", StandardStatus.REPLACED)
    current = make_item("GB 1000-2024", "现行标准", StandardStatus.ACTIVE)
    relation = StandardRelationData(
        target_standard_no="GB 1000-2018",
        target_standard_name="旧标准",
        target_source_id="OLDTARGET",
        target_source_url="https://std.samr.gov.cn/gb/search/gbDetailed?id=OLDTARGET",
        relation_type=StandardRelationType.REPLACES,
    )
    source = FakeSource(
        [current, old],
        {
            current.standard_no: make_detail(
                current.standard_no,
                "现行标准（详情）",
                relations=(relation,),
            ),
            old.standard_no: make_detail(
                old.standard_no,
                "旧标准（详情）",
                status=StandardStatus.REPLACED,
                expiry_date=date(2024, 4, 30),
            ),
        },
    )

    task, mode = run_sync(db_session, source, settings=make_settings())

    assert mode is SyncMode.FULL
    assert source.list_calls == 1
    assert source.update_calls == []
    assert task.status is SyncTaskStatus.SUCCESS
    assert (task.total_count, task.success_count, task.failed_count) == (2, 2, 0)
    assert task.started_at is not None
    assert task.finished_at is not None

    assert db_session.scalar(select(func.count()).select_from(Standard)) == 2
    current_row = db_session.scalar(
        select(Standard).where(Standard.normalized_no == "GB 1000-2024")
    )
    assert current_row is not None
    assert current_row.standard_name == "现行标准（详情）"
    assert current_row.source == "fake"
    assert current_row.source_url is not None

    relations = list(db_session.scalars(select(StandardRelation)).all())
    assert len(relations) == 1
    assert relations[0].source_standard_id == current_row.id
    assert relations[0].relation_type is StandardRelationType.REPLACES


def test_second_sync_is_incremental_and_updates_existing_row(db_session: Session) -> None:
    standard_no = "GB 2000-2024"
    item = make_item(standard_no, "旧名称")
    source = FakeSource([item], {standard_no: make_detail(standard_no, "旧名称")})
    settings = make_settings()

    first_task, first_mode = run_sync(db_session, source, settings=settings)
    assert first_mode is SyncMode.FULL
    previous_finished = first_task.finished_at

    source.updates = [make_item(standard_no, "新名称")]
    source.details[standard_no] = make_detail(standard_no, "新名称（详情）")

    second_task, second_mode = run_sync(db_session, source, settings=settings)

    assert second_mode is SyncMode.INCREMENTAL
    assert source.list_calls == 1
    assert len(source.update_calls) == 1
    assert source.update_calls[0] == previous_finished
    assert second_task.status is SyncTaskStatus.SUCCESS
    assert second_task.total_count == 1

    assert db_session.scalar(select(func.count()).select_from(Standard)) == 1
    row = db_session.scalar(
        select(Standard).where(Standard.normalized_no == standard_no)
    )
    assert row is not None
    assert row.standard_name == "新名称（详情）"


def test_detail_failure_is_partial_but_keeps_list_data(db_session: Session) -> None:
    first = make_item("GB 3000-2024", "列表数据 A")
    second = make_item("GB 3001-2024", "列表数据 B")
    source = FakeSource(
        [first, second],
        {
            second.standard_no: make_detail(second.standard_no, "详情 B"),
        },
    )
    source.fail_detail_for.add(first.standard_no)

    task, _ = run_sync(db_session, source, settings=make_settings())

    assert task.status is SyncTaskStatus.PARTIAL
    assert (task.total_count, task.success_count, task.failed_count) == (2, 1, 1)
    assert task.error_message is not None
    assert "详情抓取失败" in task.error_message

    first_row = db_session.scalar(
        select(Standard).where(Standard.normalized_no == first.standard_no)
    )
    assert first_row is not None
    assert first_row.standard_name == "列表数据 A"


def test_fatal_list_error_marks_task_failed(db_session: Session) -> None:
    source = FakeSource([], {})
    source.fail_list = True

    task, _ = run_sync(db_session, source, settings=make_settings())

    assert task.status is SyncTaskStatus.FAILED
    assert task.total_count == 0
    assert task.error_message is not None
    assert "list failed" in task.error_message
    assert task.finished_at is not None


def test_incremental_requires_initialization(db_session: Session) -> None:
    source = FakeSource([], {})

    with pytest.raises(SyncInitializationRequired):
        run_sync(db_session, source, mode=SyncMode.INCREMENTAL, settings=make_settings())

    assert db_session.scalar(select(func.count()).select_from(SyncTask)) == 0


def test_max_items_caps_one_run(db_session: Session) -> None:
    items = [make_item(f"GB 400{i}-2024", f"标准 {i}") for i in range(3)]
    source = FakeSource(
        items,
        {item.standard_no: make_detail(item.standard_no, f"详情 {i}") for i, item in enumerate(items)},
    )

    task, _ = run_sync(db_session, source, settings=make_settings(), max_items=2)

    assert task.status is SyncTaskStatus.SUCCESS
    assert (task.total_count, task.success_count, task.failed_count) == (2, 2, 0)
    assert task.error_message is not None
    assert "上限" in task.error_message
    assert db_session.scalar(select(func.count()).select_from(Standard)) == 2


def test_running_task_blocks_another_sync(db_session: Session) -> None:
    db_session.add(
        SyncTask(
            source="fake",
            status=SyncTaskStatus.RUNNING,
            started_at=utcnow(),
            total_count=0,
            success_count=0,
            failed_count=0,
        )
    )
    db_session.commit()

    with pytest.raises(SyncAlreadyRunning):
        run_sync(db_session, FakeSource([], {}), settings=make_settings())


def test_missing_relation_target_is_reported(db_session: Session) -> None:
    item = make_item("GB 5000-2024", "标准 A")
    relation = StandardRelationData(
        target_standard_no="GB 9999-2099",
        target_standard_name=None,
        target_source_id=None,
        target_source_url=None,
        relation_type=StandardRelationType.REPLACES,
    )
    source = FakeSource(
        [item],
        {item.standard_no: make_detail(item.standard_no, "详情 A", relations=(relation,))},
    )

    task, _ = run_sync(db_session, source, settings=make_settings())

    assert task.status is SyncTaskStatus.SUCCESS
    assert task.error_message is not None
    assert "关系目标未找到" in task.error_message
    assert db_session.scalar(select(func.count()).select_from(StandardRelation)) == 0


def test_relation_target_outside_incremental_window_is_refreshed(
    db_session: Session,
) -> None:
    current = make_item("GB 6000-2024", "新标准", StandardStatus.ACTIVE)
    old_no = "GB 6000-2018"
    relation = StandardRelationData(
        target_standard_no=old_no,
        target_standard_name="旧标准",
        target_source_id="OLD6000",
        target_source_url="https://std.samr.gov.cn/gb/search/gbDetailed?id=OLD6000",
        relation_type=StandardRelationType.REPLACES,
    )
    source = FakeSource(
        [current],
        {
            current.standard_no: make_detail(
                current.standard_no,
                "新标准详情",
                relations=(relation,),
            ),
            old_no: make_detail(
                old_no,
                "旧标准详情",
                status=StandardStatus.REPLACED,
                expiry_date=date(2024, 4, 30),
            ),
        },
    )

    task, _ = run_sync(db_session, source, settings=make_settings())

    assert task.status is SyncTaskStatus.SUCCESS
    assert task.total_count == 1
    assert db_session.scalar(select(func.count()).select_from(Standard)) == 2

    old_row = db_session.scalar(
        select(Standard).where(Standard.normalized_no == old_no)
    )
    assert old_row is not None
    assert old_row.status is StandardStatus.REPLACED
    assert old_row.expiry_date == date(2024, 4, 30)
    assert db_session.scalar(select(func.count()).select_from(StandardRelation)) == 1


def test_mark_stale_running_tasks_failed(db_session: Session) -> None:
    task = SyncTask(
        source="fake",
        status=SyncTaskStatus.RUNNING,
        started_at=utcnow(),
        total_count=0,
        success_count=0,
        failed_count=0,
    )
    db_session.add(task)
    db_session.commit()

    assert mark_stale_sync_tasks_failed(db_session) == 1
    db_session.refresh(task)
    assert task.status is SyncTaskStatus.FAILED
    assert task.finished_at is not None
    assert task.error_message == "服务重启，同步任务中断"


def test_source_name_rejects_unknown_source() -> None:
    from app.sync.service import SyncConfigurationError, source_name_for

    assert source_name_for(make_settings(sync_source="std_samr")) == "std_samr"
    with pytest.raises(SyncConfigurationError):
        source_name_for(make_settings(sync_source="unknown"))
