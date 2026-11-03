import pytest

from app.utils.standard_no import StandardNoNormalizer


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("gb4806.11-2023", "GB 4806.11-2023"),
        ("GB4806.11-2023", "GB 4806.11-2023"),
        ("GB 4806.11—2023", "GB 4806.11-2023"),
        ("  GB 4806.11 – 2023  ", "GB 4806.11-2023"),
        ("GB 4806.11－2023", "GB 4806.11-2023"),
        ("ＧＢ４８０６．１１－２０２３", "GB 4806.11-2023"),
        ("GB/T 1.1-2020", "GB/T 1.1-2020"),
        ("gb/t1.1—2020", "GB/T 1.1-2020"),
        ("DB11/T 1234-2020", "DB11/T 1234-2020"),
        ("T/CECS 1000-2023", "T/CECS 1000-2023"),
        ("ISO 9001:2015", "ISO 9001-2015"),
        ("GB 4806.11", "GB 4806.11"),
    ],
)
def test_normalize_variants(raw: str, expected: str) -> None:
    assert StandardNoNormalizer.normalize(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "食品安全国家标准 食品接触用橡胶材料及制品",
        "GB",
        "GB/T",
        "GB 4806.11-23",
        "GB 4806.11-2023 第1号修改单",
    ],
)
def test_invalid_standard_numbers(raw: str) -> None:
    with pytest.raises(ValueError):
        StandardNoNormalizer.normalize(raw)

    assert StandardNoNormalizer.try_normalize(raw) is None
    assert StandardNoNormalizer.is_valid(raw) is False


def test_try_normalize_handles_none_and_valid_input() -> None:
    assert StandardNoNormalizer.try_normalize(None) is None
    assert StandardNoNormalizer.try_normalize("gb 4806.11-2023") == "GB 4806.11-2023"
    assert StandardNoNormalizer.is_valid("GB 4806.11-2023") is True
