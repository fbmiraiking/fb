import math

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductRecognition(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    name: str = ""
    category_guess: str = Field(default="", alias="categoryGuess")
    confidence: float = 0.0

    @field_validator("name", "category_guess", mode="before")
    @classmethod
    def _clean_text(cls, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return str(value).strip()

    @field_validator("confidence", mode="before")
    @classmethod
    def _clean_confidence(cls, value: object) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(number):
            return 0.0
        if 1.0 < number <= 100.0:
            number = number / 100.0
        return min(1.0, max(0.0, number))


class VisionAnalysisResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    product: ProductRecognition = Field(default_factory=ProductRecognition)
    materials: list[str] = Field(default_factory=list)
    usages: list[str] = Field(default_factory=list)
    visible_text: list[str] = Field(default_factory=list, alias="visibleText")
    visible_standard_numbers: list[str] = Field(
        default_factory=list,
        alias="visibleStandardNumbers",
    )
    production_date: str | None = Field(default=None, alias="productionDate")
    manufacturer: str | None = None

    @field_validator("product", mode="before")
    @classmethod
    def _coerce_product(cls, value: object) -> object:
        return {} if value is None else value

    @field_validator(
        "materials",
        "usages",
        "visible_text",
        "visible_standard_numbers",
        mode="before",
    )
    @classmethod
    def _clean_string_list(cls, value: object) -> list[str]:
        if value is None:
            return []
        items: list[object]
        if isinstance(value, str):
            items = [value]
        elif isinstance(value, (list, tuple)):
            items = list(value)
        else:
            return []

        cleaned: list[str] = []
        for item in items:
            if not isinstance(item, str):
                continue
            text = item.strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned

    @field_validator("production_date", "manufacturer", mode="before")
    @classmethod
    def _clean_optional_text(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
