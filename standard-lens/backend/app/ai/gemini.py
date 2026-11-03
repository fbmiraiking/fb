import base64
from typing import Any
from urllib.parse import quote

from app.ai.base import (
    HTTPVisionProvider,
    IMAGE_ANALYSIS_PROMPT,
    AIProviderError,
    detect_image_mime,
)
from app.ai.config import AIConfig
from app.ai.types import AIProviderType, VisionAnalysisResult


class GeminiProvider(HTTPVisionProvider):
    provider = AIProviderType.GEMINI

    def _auth_headers(self, config: AIConfig) -> dict[str, str]:
        return {
            "x-goog-api-key": config.api_key.get_secret_value(),
            "Accept": "application/json",
        }

    async def analyze_image(
        self,
        image: bytes,
        config: AIConfig,
    ) -> VisionAnalysisResult:
        mime_type = detect_image_mime(image)
        model = config.model.strip()
        if model.startswith("models/"):
            model = model[len("models/") :]

        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": IMAGE_ANALYSIS_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(image).decode("ascii"),
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {"maxOutputTokens": 1024},
        }
        data = await self._post_json(
            config,
            (
                f"{config.effective_base_url()}"
                f"/models/{quote(model, safe='')}:generateContent"
            ),
            payload,
        )

        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise AIProviderError("AI 服务返回格式异常")
        first_candidate = candidates[0]
        if not isinstance(first_candidate, dict):
            raise AIProviderError("AI 服务返回格式异常")
        content = first_candidate.get("content")
        if not isinstance(content, dict):
            raise AIProviderError("AI 服务返回格式异常")
        parts = content.get("parts")
        if not isinstance(parts, list):
            raise AIProviderError("AI 服务返回格式异常")

        text_parts = [
            part["text"].strip()
            for part in parts
            if isinstance(part, dict)
            and isinstance(part.get("text"), str)
            and part["text"].strip()
        ]
        text = "\n".join(text_parts).strip()
        if not text:
            raise AIProviderError("AI 服务未返回文本结果")

        return VisionAnalysisResult(
            text=text,
            provider=self.provider,
            model=config.model,
        )
