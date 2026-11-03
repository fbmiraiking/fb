from pydantic import BaseModel, Field

from app.ai.types import AIProviderType


class AITestConnectionResponse(BaseModel):
    ok: bool
    provider: AIProviderType
    model: str
    message: str
    latency_ms: int = Field(serialization_alias="latencyMs")
