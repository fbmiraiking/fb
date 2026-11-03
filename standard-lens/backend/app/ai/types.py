import enum
from dataclasses import dataclass


class AIProviderType(str, enum.Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"


DEFAULT_BASE_URLS: dict[AIProviderType, str | None] = {
    AIProviderType.OPENAI: "https://api.openai.com/v1",
    AIProviderType.GEMINI: "https://generativelanguage.googleapis.com/v1beta",
    AIProviderType.ANTHROPIC: "https://api.anthropic.com/v1",
    AIProviderType.OPENAI_COMPATIBLE: None,
}


@dataclass(frozen=True, slots=True)
class ProviderTestResult:
    ok: bool
    message: str
    latency_ms: int | None = None


@dataclass(frozen=True, slots=True)
class VisionAnalysisResult:
    text: str
    provider: AIProviderType
    model: str
