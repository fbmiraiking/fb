from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin_token
from app.db.session import get_db
from app.schemas.sync import SyncStartResponse
from app.sync.service import (
    SyncAlreadyRunning,
    SyncConfigurationError,
    SyncInitializationRequired,
    SyncMode,
    start_sync,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
)


@router.post(
    "/sync/standards",
    response_model=SyncStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="手动同步标准数据（管理员）",
    description=(
        "创建同步任务并在后台执行。auto：首次全量、之后增量；full：强制全量；"
        "incremental：仅增量。需要 X-Admin-Token 请求头。"
    ),
)
def trigger_standard_sync(
    mode: SyncMode = Query(
        SyncMode.AUTO,
        description="auto（默认）/ full / incremental",
    ),
    db: Session = Depends(get_db),
) -> SyncStartResponse:
    try:
        result = start_sync(db, mode=mode)
    except SyncAlreadyRunning as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SyncInitializationRequired as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SyncConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    return SyncStartResponse(
        task_id=result.task_id,
        source=result.source,
        status=result.status,
        mode=result.mode,
        message="同步任务已启动",
    )
