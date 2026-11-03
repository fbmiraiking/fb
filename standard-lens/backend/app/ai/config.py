from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from app.ai.types import AIProviderType, DEFAULT_BASE_URLS


class AIConfig(BaseModel):
    """Per-request AI configuration.

    The API key is a SecretStr so accidental repr/log output is masked. This
    object must never be persisted or attached to long-lived state.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

    provider: AIProviderType
    api_base_url: str | None = Field(
        default=None,
        alias="apiBaseUrl",
        max_length=1024,
    )
    api_key: SecretStr = Field(alias="apiKey")
    model: str = Field(min_length=1, max_length=200)

    @field_validator("api_base_url")
    @classmethod
    def _validate_base_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if any(character.isspace() for character in value):
            raise ValueError("Base URL 不能包含空白字符")

        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Base URL 必须是 http(s) 地址")
        if parsed.username or parsed.password:
            raise ValueError("Base URL 不能包含用户名或密码")
        if parsed.query or parsed.fragment:
            raise ValueError("Base URL 不能包含查询参数或片段")
        return value.rstrip("/")

    @field_validator("api_key")
    @classmethod
    def _validate_api_key(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value().strip()
        if not raw:
            raise ValueError("API Key 不能为空")
        if len(raw) > 4096:
            raise ValueError("API Key 过长")
        return SecretStr(raw)

    @model_validator(mode="after")
    def _validate_compatible_base_url(self) -> "AIConfig":
        if (
            self.provider is AIProviderType.OPENAI_COMPATIBLE
            and not self.api_base_url
        ):
            raise ValueError("OpenAI Compatible 必须填写 Base URL")
        return self

    def effective_base_url(self) -> str:
        if self.api_base_url:
            return self.api_base_url.rstrip("/")
        default = DEFAULT_BASE_URLS.get(self.provider)
        if not default:
            raise ValueError("该 Provider 必须填写 Base URL")
        return default
