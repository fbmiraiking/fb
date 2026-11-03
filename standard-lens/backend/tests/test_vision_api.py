import json
import logging
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.ai.base import AIProviderError
from app.ai.types import VisionAnalysisResult
from app.vision import service as vision_service
from app.vision.image import MAX_IMAGE_BYTES

SECRET = "sk-vision-super-secret-789"

PAYLOAD = {
    "product": {
        "name": "塑料奶瓶",
        "categoryGuess": "奶瓶",
        "confidence": 0.9,
    },
    "materials": ["PP", "硅胶"],
    "usages": ["喂养"],
    "visibleText": [
        "GB 4806.7-2024",
        "食品接触用",
        "生产日期 2024-05-01",
        "某某塑料制品有限公司",
        "净含量 250mL",
    ],
    "visibleStandardNumbers": ["GB 4806.7-2024", "GB 9999-2099"],
    "productionDate": "2024-05-01",
    "manufacturer": "某某塑料制品有限公司",
}


class FakeProvider:
    def __init__(
        self,
        text: str = "",
        error: Exception | None = None,
    ) -> None:
        self.text = text
        self.error = error
        self.image: bytes | None = None
        self.config = None

    async def analyze_image(self, image: bytes, config):
        self.image = image
        self.config = config
        if self.error is not None:
            raise self.error
        return VisionAnalysisResult(
            text=self.text,
            provider=config.provider,
            model=config.model,
        )


def png_bytes(size: tuple[int, int] = (3000, 1000)) -> bytes:
    image = Image.new("RGB", size, (220, 230, 240))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def gif_bytes() -> bytes:
    image = Image.new("RGB", (100, 100), (255, 0, 0))
    buffer = BytesIO()
    image.save(buffer, format="GIF")
    return buffer.getvalue()


def form_data(**overrides: str) -> dict[str, str]:
    values = {
        "provider": "openai",
        "apiBaseUrl": "https://api.example.test/v1",
        "apiKey": SECRET,
        "model": "gpt-test",
    }
    values.update(overrides)
    return values


def upload(client: TestClient, data: dict[str, str], image: bytes, content_type: str = "image/png"):
    return client.post(
        "/api/v1/vision/analyze",
        data=data,
        files={"image": ("label.png", image, content_type)},
    )


def test_vision_analyze_returns_structured_json_and_compresses_image(
    client: TestClient,
    monkeypatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeProvider(text=json.dumps(PAYLOAD, ensure_ascii=False))
    monkeypatch.setattr(
        vision_service,
        "get_vision_provider",
        lambda provider: fake,
    )
    caplog.set_level(logging.DEBUG)

    response = upload(client, form_data(), png_bytes())

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "product",
        "materials",
        "usages",
        "visibleText",
        "visibleStandardNumbers",
        "productionDate",
        "manufacturer",
    }
    assert set(body["product"]) == {"name", "categoryGuess", "confidence"}
    assert body["product"]["name"] == "塑料奶瓶"
    assert body["product"]["categoryGuess"] == "奶瓶"
    assert body["product"]["confidence"] == pytest.approx(0.9)
    assert body["materials"] == ["PP", "硅胶"]
    assert body["usages"] == ["喂养"]
    assert body["visibleStandardNumbers"] == ["GB 4806.7-2024"]
    assert body["productionDate"] == "2024-05-01"
    assert body["manufacturer"] == "某某塑料制品有限公司"
    assert SECRET not in response.text
    assert SECRET not in caplog.text

    assert fake.image is not None
    with Image.open(BytesIO(fake.image)) as processed:
        assert processed.format == "JPEG"
        assert max(processed.size) == 2048
    assert fake.config is not None
    assert fake.config.api_key.get_secret_value() == SECRET


def test_vision_analyze_rejects_oversized_image(
    client: TestClient,
    monkeypatch,
) -> None:
    fake = FakeProvider(text=json.dumps(PAYLOAD))
    monkeypatch.setattr(
        vision_service,
        "get_vision_provider",
        lambda provider: fake,
    )

    response = upload(
        client,
        form_data(),
        b"x" * (MAX_IMAGE_BYTES + 1),
    )

    assert response.status_code == 413
    assert "10MB" in response.json()["detail"]
    assert fake.image is None


def test_vision_analyze_rejects_unsupported_format(
    client: TestClient,
    monkeypatch,
) -> None:
    fake = FakeProvider(text=json.dumps(PAYLOAD))
    monkeypatch.setattr(
        vision_service,
        "get_vision_provider",
        lambda provider: fake,
    )

    response = upload(client, form_data(), gif_bytes(), content_type="image/gif")

    assert response.status_code == 415
    assert "JPEG、PNG、WebP" in response.json()["detail"]
    assert fake.image is None


def test_vision_analyze_validation_error_does_not_echo_key(
    client: TestClient,
) -> None:
    response = upload(
        client,
        form_data(provider="openai_compatible", apiBaseUrl=""),
        png_bytes((64, 64)),
    )

    assert response.status_code == 422
    assert SECRET not in response.text


def test_vision_analyze_provider_error_is_redacted(
    client: TestClient,
    monkeypatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeProvider(error=AIProviderError(f"boom {SECRET}"))
    monkeypatch.setattr(
        vision_service,
        "get_vision_provider",
        lambda provider: fake,
    )
    caplog.set_level(logging.DEBUG)

    response = upload(client, form_data(), png_bytes((64, 64)))

    assert response.status_code == 502
    assert "***" in response.json()["detail"]
    assert SECRET not in response.text
    assert SECRET not in caplog.text


def test_vision_analyze_invalid_model_json_returns_502(
    client: TestClient,
    monkeypatch,
) -> None:
    fake = FakeProvider(text="not a json object")
    monkeypatch.setattr(
        vision_service,
        "get_vision_provider",
        lambda provider: fake,
    )

    response = upload(client, form_data(), png_bytes((64, 64)))

    assert response.status_code == 502
    assert response.json() == {"detail": "AI 返回格式异常"}
