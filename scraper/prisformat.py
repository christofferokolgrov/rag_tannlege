import re
from dataclasses import dataclass
from enum import StrEnum

_CURRENCY_RE = re.compile(r"\b(?:kr|nok)\b", re.IGNORECASE)
_FRA_RE = re.compile(r"\bfra\b", re.IGNORECASE)
_TRAILING_DASH_RE = re.compile(r",-(?=\s|$)")
_RANGE_SEP = "–—"  # en-dash, em-dash; ASCII hyphen handled separately
_DIGIT_RE = re.compile(r"\d")
_PER_UNIT_RE = re.compile(r"\bper[ _](halvtime|dose|stk)\b", re.IGNORECASE)


class Prisformat(StrEnum):
    FAST = "fast"
    FRA = "fra"
    SPREAD = "spread"
    PER_HALVTIME = "per_halvtime"
    PER_DOSE = "per_dose"
    PER_STK = "per_stk"
    ETTER_KONSULTASJON = "etter_konsultasjon"


_PER_PRISFORMAT = {
    "halvtime": Prisformat.PER_HALVTIME,
    "dose": Prisformat.PER_DOSE,
    "stk": Prisformat.PER_STK,
}


class PrisformatError(ValueError):
    pass


@dataclass(frozen=True)
class ParsedPrice:
    pris_min: int | None
    pris_max: int | None
    prisformat: Prisformat


def _extract_int(token: str) -> int:
    digits = token.replace(".", "").replace(" ", "")
    if not digits.isdigit():
        raise PrisformatError(f"cannot parse integer from {token!r}")
    return int(digits)


def _extract_first_int(text: str) -> int:
    m = re.search(r"\d[\d. ]*", text)
    if not m:
        raise PrisformatError(f"no digits found in {text!r}")
    return _extract_int(m.group(0).strip())


def parse_price(raw: str) -> ParsedPrice:
    if not _DIGIT_RE.search(raw or ""):
        return ParsedPrice(None, None, Prisformat.ETTER_KONSULTASJON)

    per_match = _PER_UNIT_RE.search(raw)
    if per_match:
        n = _extract_first_int(_PER_UNIT_RE.sub("", raw))
        return ParsedPrice(n, n, _PER_PRISFORMAT[per_match.group(1).lower()])

    cleaned = _CURRENCY_RE.sub("", raw)
    cleaned = _TRAILING_DASH_RE.sub("", cleaned)
    for sep in _RANGE_SEP:
        cleaned = cleaned.replace(sep, "-")

    is_fra = bool(_FRA_RE.search(cleaned))
    cleaned = _FRA_RE.sub("", cleaned).strip()

    parts = [p.strip() for p in cleaned.split("-") if p.strip()]
    if len(parts) == 2:
        lo, hi = _extract_int(parts[0]), _extract_int(parts[1])
        return ParsedPrice(lo, hi, Prisformat.SPREAD)

    n = _extract_int(cleaned)
    if is_fra:
        return ParsedPrice(n, None, Prisformat.FRA)
    return ParsedPrice(n, n, Prisformat.FAST)
