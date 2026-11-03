import re
import unicodedata


class StandardNoNormalizer:
    """Normalize Chinese standard numbers into a canonical, comparable form.

    Canonical form is ``PREFIX NUMBER-YEAR``, for example:

    - ``gb4806.11-2023`` -> ``GB 4806.11-2023``
    - ``GB 4806.11—2023`` -> ``GB 4806.11-2023``
    - ``GB/T 1.1－2020`` -> ``GB/T 1.1-2020``

    Full-width characters are folded with Unicode NFKC, whitespace is removed
    and all dash variants (including em/en dashes) become ``-``. A colon year
    separator (used by ISO-style numbers) is also normalized to ``-`` because
    the canonical form is an internal key. The display value stays in
    ``standard_no``.
    """

    _WHITESPACE = re.compile(r"\s+")
    _DASHES = str.maketrans(
        {
            "‐": "-",  # hyphen
            "‑": "-",  # non-breaking hyphen
            "‒": "-",  # figure dash
            "–": "-",  # en dash
            "—": "-",  # em dash
            "―": "-",  # horizontal bar
            "⁃": "-",  # hyphen bullet
            "−": "-",  # minus sign
            "﹘": "-",  # small em dash
            "﹣": "-",  # small hyphen-minus
            "－": "-",  # full-width hyphen-minus
        }
    )
    # Prefixes cover GB, GB/T, GBZ, DB11/T, T/CECS, JJF, ISO, ...
    # Digits are only allowed in a prefix when followed by "/" (e.g. DB11/T),
    # otherwise the greedy prefix would swallow the beginning of the number.
    _PREFIX = (
        r"(?:[A-Z]{1,10}/[A-Z]{1,6}"
        r"|[A-Z]{1,10}[0-9]{1,8}/[A-Z]{1,6}"
        r"|[A-Z]{1,10})"
    )
    _STANDARD_NO = re.compile(
        rf"^(?P<prefix>{_PREFIX})"
        r"(?P<number>[0-9]+(?:\.[0-9]+)*)"
        r"(?:(?P<separator>[-:])(?P<year>[0-9]{4}))?$"
    )

    @classmethod
    def normalize(cls, raw: str) -> str:
        """Return the canonical form, raising ``ValueError`` when unrecognized."""
        if not isinstance(raw, str):
            raise TypeError("standard number must be a string")

        value = unicodedata.normalize("NFKC", raw).strip()
        if not value:
            raise ValueError("标准号不能为空")

        value = value.translate(cls._DASHES)
        value = cls._WHITESPACE.sub("", value).upper()

        match = cls._STANDARD_NO.fullmatch(value)
        if match is None:
            raise ValueError(f"无法识别的标准号: {raw!r}")

        canonical = f"{match.group('prefix')} {match.group('number')}"
        year = match.group("year")
        if year is not None:
            canonical = f"{canonical}-{year}"
        return canonical

    @classmethod
    def try_normalize(cls, raw: str | None) -> str | None:
        """Return the canonical form, or ``None`` when the input is not a standard number."""
        if not raw:
            return None
        try:
            return cls.normalize(raw)
        except (TypeError, ValueError):
            return None

    @classmethod
    def is_valid(cls, raw: str | None) -> bool:
        return cls.try_normalize(raw) is not None
