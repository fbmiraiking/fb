from pydantic import BaseModel

from app.models.sync_task import SyncTaskStatus
from app.sync.service import SyncMode


class SyncStartResponse(BaseModel):
    task_id: int
    source: str
    status: SyncTaskStatus
    mode: SyncMode
    message: str = "同步任务已启动"
