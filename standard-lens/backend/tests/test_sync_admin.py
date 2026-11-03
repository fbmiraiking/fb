from fastapi.testclient import TestClient

from app.api import deps
from app.api.routes import admin as admin_routes
from app.core.config import Settings
from app.models.sync_task import SyncTaskStatus
from app.sync.service import (
    SyncAlreadyRunning,
    SyncInitializationRequired,
    SyncMode,
    SyncStartResult,
)

HEADERS = {"X-Admin-Token": "test-admin-token"}


def test_admin_sync_requires_token(client: TestClient) -> None:
    response = client.post("/api/admin/sync/standards")

    assert response.status_code == 401
    assert response.json() == {"detail": "管理员令牌无效"}


def test_admin_sync_rejects_wrong_token(client: TestClient) -> None:
    response = client.post(
        "/api/admin/sync/standards",
        headers={"X-Admin-Token": "wrong"},
    )

    assert response.status_code == 401


def test_admin_sync_returns_503_when_token_not_configured(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(deps, "get_settings", lambda: Settings(admin_sync_token=""))

    response = client.post(
        "/api/admin/sync/standards",
        headers=HEADERS,
    )

    assert response.status_code == 503


def test_admin_sync_starts_task(client: TestClient, monkeypatch) -> None:
    def fake_start_sync(db, mode):
        return SyncStartResult(
            task_id=42,
            source="std_samr",
            status=SyncTaskStatus.RUNNING,
            mode=SyncMode.FULL,
        )

    monkeypatch.setattr(admin_routes, "start_sync", fake_start_sync)

    response = client.post(
        "/api/admin/sync/standards?mode=full",
        headers=HEADERS,
    )

    assert response.status_code == 202
    assert response.json() == {
        "task_id": 42,
        "source": "std_samr",
        "status": "RUNNING",
        "mode": "full",
        "message": "同步任务已启动",
    }


def test_admin_sync_returns_conflict_when_running(client: TestClient, monkeypatch) -> None:
    def fake_start_sync(db, mode):
        raise SyncAlreadyRunning("已有同步任务正在运行")

    monkeypatch.setattr(admin_routes, "start_sync", fake_start_sync)

    response = client.post("/api/admin/sync/standards", headers=HEADERS)

    assert response.status_code == 409
    assert response.json() == {"detail": "已有同步任务正在运行"}


def test_admin_sync_requires_initialization_for_incremental(
    client: TestClient,
    monkeypatch,
) -> None:
    def fake_start_sync(db, mode):
        raise SyncInitializationRequired("尚无成功的全量初始化，无法执行增量同步")

    monkeypatch.setattr(admin_routes, "start_sync", fake_start_sync)

    response = client.post(
        "/api/admin/sync/standards?mode=incremental",
        headers=HEADERS,
    )

    assert response.status_code == 400
