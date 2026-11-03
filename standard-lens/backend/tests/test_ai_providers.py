import asyncio
import base64
import json
import logging

import httpx
import pytest

from app.ai.anthropic import AnthropicProvider
from app.ai.base import AIProviderError, detect_image_mime
from app.ai.config import AIConfig
from app.ai.gemini import GeminiProvider
from app.ai.openai import OpenAICompatibleProvider, OpenAIProvider
from app.ai.types import AIProviderType

SECRET = "sk-super-secret-key"
PNG = b"\x89PNG\r\n\x1a\n" + b"fake-image-data"


def make_config(
    provider: AIProviderType,
    *,
    base_url: str | None = None,
    model: str = "test-model",
) -> AIConfig:
    return AIConfig(
        provider=provider,
        api_base_url=base_url,
        api_key=SECRET,
        model=model,
    )


def run(coro):
    return asyncio.run(coro)


def test_openai_test_connection_uses_bearer_header() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": []})

    provider = OpenAIProvider(
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    result = run(
        provider.test_connection(
            make_config(AIProviderType.OPENAI, base_url="https://api.example.test/v1")
        )
    )

    assert result.ok is True
    assert result.message == "连接成功"
    assert len(requests) == 1
    assert str(requests[0].url) == "https://api.example.test/v1/models"
    assert requests[0].headers["authorization"] == f"Bearer {SECRET}"
    assert SECRET not in str(requests[0].url)


def test_openai_default_base_url_is_used_when_omitted() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    provider = OpenAIProvider(
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    result = run(provider.test_connection(make_config(AIProviderType.OPENAI)))

    assert result.ok is True
    assert str(requests[0].url) == "https://api.openai.com/v1/models"


def test_openai_compatible_uses_custom_base_url() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    provider = OpenAICompatibleProvider(
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    result = run(
        provider.test_connection(
            make_config(
                AIProviderType.OPENAI_COMPATIBLE,
                base_url="http://localhost:11434/v1",
            )
        )
    )

    assert result.ok is True
    assert str(requests[0].url) == "http://localhost:11434/v1/models"
    assert requests[0].headers["authorization"] == f"Bearer {SECRET}"


def test_gemini_test_connection_uses_header_not_url() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={})

    provider = GeminiProvider(
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    result = run(
        provider.test_connection(
            make_config(AIProviderType.GEMINI, base_url="https://gemini.example/v1beta")
        )
    )

    assert result.ok is True
    assert str(requests[0].url) == "https://gemini.example/v1beta/models"
    assert requests[0].headers["x-goog-api-key"] == SECRET
    assert SECRET not in str(requests[0].url)


def test_anthropic_test_connection_headers_and_versioned_base() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"content": []})

    provider = AnthropicProvider(
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    result = run(
        provider.test_connection(
            make_config(AIProviderType.ANTHROPIC, base_url="https://anthropic.example")
        )
    )

    assert result.ok is True
    assert str(requests[0].url) == "https://anthropic.example/v1/messages"
    assert requests[0].method == "POST"
    assert requests[0].headers["x-api-key"] == SECRET
    assert requests[0].headers["authorization"] == f"Bearer {SECRET}"
    assert requests[0].headers["anthropic-version"] == "2023-06-01"
    assert SECRET not in str(requests[0].url)


def test_auth_failure_is_mapped_to_safe_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": f"invalid key {SECRET}"})

    provider = OpenAIProvider(
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    result = run(provider.test_connection(make_config(AIProviderType.OPENAI)))

    assert result.ok is False
    assert "认证失败" in result.message
    assert SECRET not in result.message


def test_timeout_is_mapped_and_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException(f"timeout {SECRET}")

    caplog.set_level(logging.DEBUG)
    provider = OpenAIProvider(
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )
    result = run(provider.test_connection(make_config(AIProviderType.OPENAI)))

    assert result.ok is False
    assert result.message == "连接超时"
    assert SECRET not in caplog.text


def test_openai_analyze_image_payload_and_result() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        captured["url"] = str(request.url)
        captured["body"] = body
        captured["authorization"] = request.headers["authorization"]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "GB 4806.7-2024"}}]},
        )

    provider = OpenAIProvider(
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    config = make_config(AIProviderType.OPENAI, base_url="https://api.example/v1")
    result = run(provider.analyze_image(PNG, config))

    assert result.text == "GB 4806.7-2024"
    assert result.provider is AIProviderType.OPENAI
    assert result.model == "test-model"
    assert captured["url"] == "https://api.example/v1/chat/completions"
    assert captured["authorization"] == f"Bearer {SECRET}"
    assert SECRET not in json.dumps(captured["body"])
    body = captured["body"]
    assert body["model"] == "test-model"
    assert "data:image/png;base64," in json.dumps(body)
    assert base64.b64encode(PNG).decode("ascii") in json.dumps(body)


def test_anthropic_analyze_image_payload_and_result() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "text", "text": "识别到 "},
                    {"type": "text", "text": "GB 4806.7-2024"},
                ]
            },
        )

    provider = AnthropicProvider(
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    config = make_config(
        AIProviderType.ANTHROPIC,
        base_url="https://anthropic.example/v1",
    )
    result = run(provider.analyze_image(PNG, config))

    assert result.text == "识别到\nGB 4806.7-2024"
    assert captured["url"] == "https://anthropic.example/v1/messages"
    body = captured["body"]
    assert body["messages"][0]["content"][0]["source"]["media_type"] == "image/png"
    assert SECRET not in json.dumps(body)


def test_gemini_analyze_image_payload_and_result() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": "GB 4806.7-2024"}]}}
                ]
            },
        )

    provider = GeminiProvider(
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    config = make_config(
        AIProviderType.GEMINI,
        base_url="https://gemini.example/v1beta",
        model="gemini-test",
    )
    result = run(provider.analyze_image(PNG, config))

    assert result.text == "GB 4806.7-2024"
    assert (
        captured["url"]
        == "https://gemini.example/v1beta/models/gemini-test:generateContent"
    )
    body = captured["body"]
    assert body["contents"][0]["parts"][1]["inline_data"]["mime_type"] == "image/png"
    assert SECRET not in json.dumps(body)


def test_provider_error_is_safe_and_unlogged(caplog: pytest.LogCaptureFixture) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, json={"error": f"server {SECRET}"})

    caplog.set_level(logging.DEBUG)
    provider = OpenAIProvider(
        timeout_seconds=5,
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(AIProviderError) as exc_info:
        run(
            provider.analyze_image(
                PNG,
                make_config(AIProviderType.OPENAI, base_url="https://api.example/v1"),
            )
        )

    assert "暂时不可用" in str(exc_info.value)
    assert SECRET not in str(exc_info.value)
    assert SECRET not in caplog.text


def test_detect_image_mime() -> None:
    assert detect_image_mime(PNG) == "image/png"
    assert detect_image_mime(b"\xff\xd8\xff\xe0") == "image/jpeg"
    assert detect_image_mime(b"RIFF\x00\x00\x00\x00WEBP") == "image/webp"
    assert detect_image_mime(b"GIF89a") == "image/gif"
