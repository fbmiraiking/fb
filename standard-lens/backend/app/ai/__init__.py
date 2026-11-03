from app.ai.anthropic import AnthropicProvider
from app.ai.base import AIProviderError, VisionProvider
from app.ai.config import AIConfig
from app.ai.gemini import GeminiProvider
from app.ai.openai import OpenAICompatibleProvider, OpenAIProvider
from app.ai.types import AIProviderType


def get_vision_provider(
    provider: AIProviderType,
    *,
    timeout_seconds: float | None = None,
) -> VisionProvider:
    """Build a stateless provider for one request.

    No configuration is stored on the instance; the provider only receives it
    per method call.
    """
    from app.core.config import get_settings

    timeout = (
        timeout_seconds
        if timeout_seconds is not None
        else get_settings().ai_request_timeout_seconds
    )

    if provider is AIProviderType.OPENAI:
        return OpenAIProvider(timeout_seconds=timeout)
    if provider is AIProviderType.OPENAI_COMPATIBLE:
        return OpenAICompatibleProvider(timeout_seconds=timeout)
    if provider is AIProviderType.ANTHROPIC:
        return AnthropicProvider(timeout_seconds=timeout)
    if provider is AIProviderType.GEMINI:
        return GeminiProvider(timeout_seconds=timeout)
    raise AIProviderError("不支持的 AI Provider")


__all__ = [
    "AIConfig",
    "AIProviderError",
    "AIProviderType",
    "AnthropicProvider",
    "GeminiProvider",
    "OpenAICompatibleProvider",
    "OpenAIProvider",
    "VisionProvider",
    "get_vision_provider",
]
