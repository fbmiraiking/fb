from typing import Any

from app.ai.base import (
    HTTPVisionProvider,
    IMAGE_ANALYSIS_PROMPT,
    AIProviderError,
    detect_image_mime,
)
from app.ai.config import AIConfig
from app.ai.types import AIProviderType, VisionAnalysisResult


def _extract_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise AIProviderError("AI 服务返回格式异常")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise AIProviderError("AI 服务返回格式异常")
    content = message.get("content")

    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                part_text = part["text"].strip()
                if part_text:
                    parts.append(part_text)
        text = "\n".join(parts)
    else:
        text = ""

    if not text.strip():
        raise AIProviderError("AI 服务未返回文本结果")
    return text.strip()


class OpenAIProvider(HTTPVisionProvider):
    provider = AIProviderType.OPENAI

    def _auth_headers(self, config: AIConfig) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {config.api_key.get_secret_value()}",
            "Accept": "application/json",
        }

    async def analyze_image(
        self,
        image: bytes,
        config: AIConfig,
    ) -> VisionAnalysisResult:
        mime_type = detect_image_mime(image)
        payload = {
            "model": config.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": IMAGE_ANALYSIS_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": self._image_data_url(image, mime_type),
                            },
                        },
                    ],
                }
            ],
        }
        data = await self._post_json(
            config,
            f"{config.effective_base_url()}/chat/completions",
            payload,
        )
        return VisionAnalysisResult(
            text=_extract_text(data),
            provider=self.provider,
            model=config.model,
        )


class OpenAICompatibleProvider(OpenAIProvider):
    provider = AIProviderType.OPENAI_COMPATIBLE
