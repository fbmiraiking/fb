import json
import re
import unicodedata

from pydantic import ValidationError

from app.schemas.vision import VisionAnalysisResponse
from app.utils.standard_no import StandardNoNormalizer


class VisionParseError(Exception):
    """The model output was not a valid structured recognition result."""


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_DASHES = str.maketrans(
    {
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "―": "-",
        "⁃": "-",
        "−": "-",
        "﹘": "-",
        "﹣": "-",
        "－": "-",
    }
)


def _compact(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).upper().translate(_DASHES)
    return re.sub(r"\s+", "", text)


def _extract_json(text: str) -> dict[str, object]:
    cleaned = text.strip()
    fenced = _FENCE_RE.search(cleaned)
    if fenced is not None:
        cleaned = fenced.group(1).strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise VisionParseError("AI 返回内容不是 JSON 对象")

    try:
        data = json.loads(cleaned[start : end + 1])
    except (json.JSONDecodeError, TypeError) as exc:
        raise VisionParseError("AI 返回内容不是合法 JSON") from exc
    if not isinstance(data, dict):
        raise VisionParseError("AI 返回内容不是 JSON 对象")
    return data


def _filter_visible_standard_numbers(
    model: VisionAnalysisResponse,
) -> VisionAnalysisResponse:
    # Only keep numbers that are both valid standard numbers and present in the
    # model's visible text. This is a conservative guard against the model
    # inferring a standard number from product knowledge.
    visible_text = _compact(" ".join(model.visible_text))
    numbers: list[str] = []
    for raw in model.visible_standard_numbers:
        canonical = StandardNoNormalizer.try_normalize(raw)
        if canonical is None:
            continue
        if _compact(canonical) not in visible_text:
            continue
        if canonical not in numbers:
            numbers.append(canonical)
    return model.model_copy(update={"visible_standard_numbers": numbers})


def parse_vision_json(text: str) -> VisionAnalysisResponse:
    data = _extract_json(text)
    try:
        model = VisionAnalysisResponse.model_validate(data)
    except ValidationError as exc:
        raise VisionParseError("AI 返回结构不符合要求") from exc
    return _filter_visible_standard_numbers(model)
