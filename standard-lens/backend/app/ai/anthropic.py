import base64
import time
from typing import Any

import httpx

from app.ai.base import (
    HTTPVisionProvider,
    IMAGE_ANALYSIS_PROMPT,
    AIProviderError,
    detect_image_mime,
    status_message,
)
from app.ai.config import AIConfig
from app.ai.types import AIProviderType, ProviderTestResult, VisionAnalysisResult


class AnthropicProvider(HTTPVisionProvider):
    provider = AIProviderType.ANTHROPIC
    ANTHROPIC_VERSION = "2023-06-01"

    def _versioned_base(self, config: AIConfig) -> str:
        base = config.effective_base_url().rstrip("/")
        return base if base.endswith("/v1") else f"{base}/v1"

    def _messages_url(self, config: AIConfig) -> str:
        return f"{self._versioned_base(config)}/messages"

    def _models_url(self, config: AIConfig) -> str:
        return f"{self._versioned_base(config)}/models"

    def _auth_headers(self, config: AIConfig) -> dict[str, str]:
        key = config.api_key.get_secret_value()
        # Anthropic uses x-api-key; many compatible gateways use a bearer
        # auth token (ANTHROPIC_AUTH_TOKEN). Sending both supports both styles.
        return {
            "x-api-key": key,
            "Authorization": f"Bearer {key}",
            "anthropic-version": self.ANTHROPIC_VERSION,
            "Accept": "application/json",
        }

    async def test_connection(self, config: AIConfig) -> ProviderTestResult:
        # A tiny Messages request validates base URL, credential and model,
        # including gateways that do not expose a /models endpoint.
        started = time.perf_counter()
        headers = {
            **self._auth_headers(config),
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.model,
            "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
        }
        try:
            async with self._client() as client:
                response = await client.post(
                    self._messages_url(config),
                    headers=headers,
                    json=payload,
                )
            latency = round((time.perf_counter() - started) * 1000)
            if response.is_success:
                return ProviderTestResult(True, "连接成功", latency)
            return ProviderTestResult(
                False,
                status_message(response.status_code),
                latency,
            )
        except httpx.TimeoutException:
            return ProviderTestResult(False, "连接超时", None)
        except httpx.HTTPError:
            return ProviderTestResult(False, "无法连接 AI 服务", None)
        except Exception:  # noqa: BLE001
            return ProviderTestResult(False, "测试连接失败", None)

    async def analyze_image(
        self,
        image: bytes,
        config: AIConfig,
    ) -> VisionAnalysisResult:
        mime_type = detect_image_mime(image)
        payload: dict[str, Any] = {
            "model": config.model,
            "max_tokens": 1024,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": base64.b64encode(image).decode("ascii"),
                            },
                        },
                        {"type": "text", "text": IMAGE_ANALYSIS_PROMPT},
                    ],
                }
            ],
        }
        data = await self._post_json(
            config,
            self._messages_url(config),
            payload,
        )

        blocks = data.get("content")
        if not isinstance(blocks, list):
            raise AIProviderError("AI 服务返回格式异常")
        text_parts = [
            block["text"].strip()
            for block in blocks
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
            and block["text"].strip()
        ]
        text = "\n".join(text_parts).strip()
        if not text:
            raise AIProviderError("AI 服务未返回文本结果")

        return VisionAnalysisResult(
            text=text,
            provider=self.provider,
            model=config.model,
        )
