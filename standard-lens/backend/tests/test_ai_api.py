import logging

import pytest
from fastapi.testclient import TestClient

from app.api.routes import ai as ai_routes
from app.ai.types import ProviderTestResult
from app.main import app

SECRET = "sk-super-secret-key"
PAYLOAD = {
    "provider": "openai",
    "apiBaseUrl": "https://api.example.test/v1",
    "apiKey": SECRET,
    "model": "gpt-test",
}


class FakeProvider:
    def __init__(
        self,
        *,
        result: ProviderTestResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result or ProviderTestResult(True, "连接成功")
        self.error = error

    async def test_connection(self, config):
        if self.error is not None:
            raise self.error
        return self.result


def test_ai_test_connection_success(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(
        ai_routes,
        "get_vision_provider",
        lambda provider: FakeProvider(),
    )

    response = client.post("/api/v1/ai/test-connection", json=PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["provider"] == "openai"
    assert body["model"] == "gpt-test"
    assert body["message"] == "连接成功"
    assert isinstance(body["latencyMs"], int)
    assert "latency_ms" not in body
    assert SECRET not in response.text


def test_ai_test_connection_provider_error_is_safe(
    client: TestClient,
    monkeypatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(
        ai_routes,
        "get_vision_provider",
        lambda provider: FakeProvider(error=RuntimeError(f"boom {SECRET}")),
    )
    caplog.set_level(logging.DEBUG)

    response = client.post("/api/v1/ai/test-connection", json=PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["message"] == "测试连接失败"
    assert SECRET not in response.text
    assert SECRET not in caplog.text


@pytest.mark.parametrize(
    "payload",
    [
        {
            "provider": "openai",
            "apiBaseUrl": "https://api.example.test/v1",
            "apiKey": SECRET,
        },
        {
            "provider": "not-a-provider",
            "apiKey": SECRET,
            "model": "gpt-test",
        },
        {
            "provider": "openai_compatible",
            "apiKey": SECRET,
            "model": "local-model",
        },
        {
            "provider": "openai",
            "apiBaseUrl": "ftp://api.example.test/v1",
            "apiKey": SECRET,
            "model": "gpt-test",
        },
    ],
)
def test_ai_validation_errors_do_not_echo_key(
    client: TestClient,
    payload: dict,
) -> None:
    response = client.post("/api/v1/ai/test-connection", json=payload)

    assert response.status_code == 422
    assert SECRET not in response.text
    detail = response.json()["detail"]
    assert all("input" not in item for item in detail)

    def walk(value):
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        else:
            assert SECRET not in str(value)

    walk(detail)


def test_ai_key_schema_is_write_only_password() -> None:
    schema = app.openapi()
    config_schema = schema["components"]["schemas"]["AIConfig"]
    api_key = config_schema["properties"]["apiKey"]

    assert api_key.get("format") == "password"
    assert "apiKey" in config_schema["required"]
