import base64
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.ai.config import AIConfig
from app.ai.types import AIProviderType, ProviderTestResult, VisionAnalysisResult

IMAGE_ANALYSIS_PROMPT = (
    "你是商品标签视觉识别助手。只根据图片中实际可见的信息，输出一个 JSON 对象。"
    "不要输出 Markdown 代码块、解释或 JSON 之外的任何文字。\n"
    "JSON 结构必须严格为：\n"
    '{"product":{"name":"","categoryGuess":"","confidence":0},'
    '"materials":[],"usages":[],"visibleText":[],"visibleStandardNumbers":[],'
    '"productionDate":null,"manufacturer":null}\n'
    "规则：\n"
    "1. product.name、product.categoryGuess、materials、usages 可以基于图片做视觉判断；"
    "不确定时留空或返回空数组。\n"
    "2. confidence 为 0 到 1 的数字。\n"
    "3. visibleText 逐条列出图片中清晰可见的文字，尽量保留原文；"
    "生产日期、厂家、成分、净含量、警示语等其他标签信息都放入 visibleText。\n"
    "4. visibleStandardNumbers 只能包含图片中明确可见的标准编号（如 GB 4806.7-2024）。"
    "禁止根据商品类型、常识、上下文或标准知识推测；看不清或没有就返回空数组。\n"
    "5. productionDate、manufacturer 只填写图片中明确可见的内容，否则为 null。\n"
    "6. 不要添加上述结构之外的字段。\n"
)


class AIProviderError(Exception):
    """A provider failure with a user-safe message (never contains the API key)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def redact_secret(message: str, config: AIConfig) -> str:
    """Defensive final scrub before a message leaves the request."""
    key = config.api_key.get_secret_value()
    return message.replace(key, "***") if key else message


def status_message(status_code: int) -> str:
    if status_code in (401, 403):
        return "认证失败，请检查 API Key"
    if status_code == 404:
        return "接口不存在，请检查 Base URL"
    if status_code == 400:
        return "请求被 AI 服务拒绝，请检查模型或 Base URL"
    if status_code == 429:
        return "AI 服务请求频率或额度受限"
    if status_code >= 500:
        return "AI 服务暂时不可用"
    return f"AI 服务返回 HTTP {status_code}"


def detect_image_mime(image: bytes) -> str:
    if image.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if image[:4] == b"RIFF" and image[8:12] == b"WEBP":
        return "image/webp"
    if image.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    return "image/jpeg"


class VisionProvider(ABC):
    """Unified provider interface for image analysis and connectivity tests."""

    provider: AIProviderType

    @abstractmethod
    async def analyze_image(self, image: bytes, config: AIConfig) -> VisionAnalysisResult:
        """Analyze one image using the caller-supplied configuration."""

    @abstractmethod
    async def test_connection(self, config: AIConfig) -> ProviderTestResult:
        """Check connectivity/credentials without a costly completion."""


class HTTPVisionProvider(VisionProvider):
    """Shared HTTP behaviour; configuration is only used inside the call."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout_seconds),
            follow_redirects=False,
            transport=self._transport,
        )

    @abstractmethod
    def _auth_headers(self, config: AIConfig) -> dict[str, str]:
        """Provider-specific authentication headers."""

    def _models_url(self, config: AIConfig) -> str:
        return f"{config.effective_base_url()}/models"

    async def test_connection(self, config: AIConfig) -> ProviderTestResult:
        started = time.perf_counter()
        try:
            async with self._client() as client:
                response = await client.get(
                    self._models_url(config),
                    headers=self._auth_headers(config),
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
        except Exception:  # noqa: BLE001 - never propagate provider internals
            return ProviderTestResult(False, "测试连接失败", None)

    async def _post_json(
        self,
        config: AIConfig,
        url: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        headers = {
            **self._auth_headers(config),
            "Content-Type": "application/json",
        }
        try:
            async with self._client() as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise AIProviderError("连接超时") from exc
        except httpx.HTTPError as exc:
            raise AIProviderError("无法连接 AI 服务") from exc

        if not response.is_success:
            raise AIProviderError(status_message(response.status_code))

        try:
            data = response.json()
        except ValueError as exc:
            raise AIProviderError("AI 服务返回格式异常") from exc
        if not isinstance(data, dict):
            raise AIProviderError("AI 服务返回格式异常")
        return data

    @staticmethod
    def _image_data_url(image: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(image).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
