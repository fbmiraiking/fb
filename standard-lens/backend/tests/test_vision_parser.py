import json

import pytest

from app.vision.parser import VisionParseError, parse_vision_json


def payload(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "product": {
            "name": "塑料奶瓶",
            "categoryGuess": "奶瓶",
            "confidence": 0.92,
        },
        "materials": ["PP", "硅胶", "PP"],
        "usages": ["喂养"],
        "visibleText": [
            "GB 4806.7—2024",
            "食品接触用",
            "生产日期：2024-05-01",
            "某某塑料制品有限公司",
        ],
        "visibleStandardNumbers": [
            "GB 4806.7-2024",
            "GB 9999-2099",
            "not a standard",
        ],
        "productionDate": "2024-05-01",
        "manufacturer": "某某塑料制品有限公司",
    }
    values.update(overrides)
    return values


def test_parse_structured_json_and_filter_standard_numbers() -> None:
    result = parse_vision_json(json.dumps(payload(), ensure_ascii=False))

    assert result.product.name == "塑料奶瓶"
    assert result.product.category_guess == "奶瓶"
    assert result.product.confidence == pytest.approx(0.92)
    assert result.materials == ["PP", "硅胶"]
    assert result.usages == ["喂养"]
    assert result.visible_standard_numbers == ["GB 4806.7-2024"]
    assert result.production_date == "2024-05-01"
    assert result.manufacturer == "某某塑料制品有限公司"


def test_parse_accepts_code_fences_and_surrounding_text() -> None:
    text = "识别结果如下：\n```json\n" + json.dumps(payload()) + "\n```\n请核对。"

    result = parse_vision_json(text)

    assert result.product.name == "塑料奶瓶"


def test_parse_normalizes_confidence_percentage_and_lists() -> None:
    data = payload(
        product={"name": None, "categoryGuess": None, "confidence": 85},
        materials="PP",
        usages=None,
        visibleText="GB 4806.7-2024",
        visibleStandardNumbers="GB 4806.7-2024",
        productionDate="",
        manufacturer="  ",
    )

    result = parse_vision_json(json.dumps(data, ensure_ascii=False))

    assert result.product.name == ""
    assert result.product.category_guess == ""
    assert result.product.confidence == pytest.approx(0.85)
    assert result.materials == ["PP"]
    assert result.usages == []
    assert result.visible_text == ["GB 4806.7-2024"]
    assert result.production_date is None
    assert result.manufacturer is None


def test_parse_drops_standard_numbers_not_present_in_visible_text() -> None:
    data = payload(
        visibleText=["商品名称：塑料奶瓶"],
        visibleStandardNumbers=["GB 4806.7-2024"],
    )

    result = parse_vision_json(json.dumps(data, ensure_ascii=False))

    assert result.visible_standard_numbers == []


def test_parse_rejects_invalid_json() -> None:
    with pytest.raises(VisionParseError):
        parse_vision_json("not json")

    with pytest.raises(VisionParseError):
        parse_vision_json('{"product": ')


def test_serialization_uses_camel_case_and_exact_top_level_fields() -> None:
    result = parse_vision_json(json.dumps(payload(), ensure_ascii=False))
    data = result.model_dump(by_alias=True)

    assert set(data) == {
        "product",
        "materials",
        "usages",
        "visibleText",
        "visibleStandardNumbers",
        "productionDate",
        "manufacturer",
    }
    assert set(data["product"]) == {"name", "categoryGuess", "confidence"}
