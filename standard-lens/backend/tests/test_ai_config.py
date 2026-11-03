import pytest
from pydantic import ValidationError

from app.ai.config import AIConfig
from app.ai.types import AIProviderType


def test_official_provider_default_base_urls() -> None:
    config = AIConfig(
        provider=AIProviderType.OPENAI,
        api_key="sk-secret",
        model="test-model",
    )
    assert config.effective_base_url() == "https://api.openai.com/v1"
    assert "sk-secret" not in repr(config)


def test_custom_base_url_is_normalized() -> None:
    config = AIConfig(
        provider=AIProviderType.OPENAI,
        api_base_url="https://api.example.test/v1/",
        api_key="sk-secret",
        model="test-model",
    )
    assert config.effective_base_url() == "https://api.example.test/v1"


def test_openai_compatible_requires_base_url() -> None:
    with pytest.raises(ValidationError):
        AIConfig(
            provider=AIProviderType.OPENAI_COMPATIBLE,
            api_key="sk-secret",
            model="test-model",
        )


@pytest.mark.parametrize(
    "base_url",
    [
        "ftp://api.example.test/v1",
        "https://user:pass@api.example.test/v1",
        "https://api.example.test/v1?key=secret",
        "https://api.example.test/v1#fragment",
        "not a url",
    ],
)
def test_invalid_base_urls(base_url: str) -> None:
    with pytest.raises(ValidationError):
        AIConfig(
            provider=AIProviderType.OPENAI,
            api_base_url=base_url,
            api_key="sk-secret",
            model="test-model",
        )


def test_api_key_is_stripped_and_masked() -> None:
    config = AIConfig(
        provider=AIProviderType.OPENAI,
        api_key="  sk-secret  ",
        model="  test-model  ",
    )
    assert config.api_key.get_secret_value() == "sk-secret"
    assert config.model == "test-model"
    assert "sk-secret" not in repr(config)
