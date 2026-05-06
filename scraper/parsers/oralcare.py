import re

from selectolax.parser import HTMLParser

from scraper.parsers import PriceRow
from scraper.prisformat import PrisformatError, parse_price

PRIS_KILDE = "klinikk_egen"

# Trailing footnote markers like "*", "**", "***" appended to prices, e.g.
# "Kirurgisk fjerning av tann eller rot, pris fra: 6 200 kr***".
_FOOTNOTE_TAIL_RE = re.compile(r"\s*\*+\s*$")
# OralCare bullets in `.elementor-price-list-description` are formatted as
#   "<treatment name>: <price>"
# and occasionally "<treatment name> : <price>" (note the stray space before
# the colon), and once even "<name> : : <price>" (e.g. "3-leddsbro på to
# implantat: : 53 593 kr"). We split on the LAST colon-with-whitespace so the
# treatment name keeps any internal colons it might have.
_BULLET_SEP_RE = re.compile(r"\s*:\s*")
_DIGIT_RE = re.compile(r"\d")
# A bullet name must contain at least one alphabetic word (≥3 letters) so we
# don't emit junk rows like ")" where a <br> inside parentheses fragments
# "Tannkrone MK (vanlig krone)" across lines and the trailing ")" survives.
_NAME_HAS_WORD_RE = re.compile(r"[A-Za-zÆØÅæøå]{3,}")
_ADDRESS_RE = re.compile(
    r"([^,\n]+?),\s*(\d{4})[\s\xa0]+([A-Za-zÆØÅæøå]+)"
)


def _emit(
    rows: list[PriceRow],
    name: str,
    price_text: str,
    klinikk_id: str,
    hentet_dato: str,
) -> None:
    name = name.strip()
    if not name:
        return
    price_text = _FOOTNOTE_TAIL_RE.sub("", price_text).strip()
    if not price_text:
        return
    try:
        parsed = parse_price(price_text)
    except PrisformatError:
        return
    rows.append(
        PriceRow(
            klinikk_id=klinikk_id,
            behandling_navn_raw=name,
            pris_min=parsed.pris_min,
            pris_max=parsed.pris_max,
            prisformat=parsed.prisformat,
            pris_kilde=PRIS_KILDE,
            kommentar="",
            hentet_dato=hentet_dato,
        )
    )


def _split_bullet(line: str) -> tuple[str, str] | None:
    """Split a description bullet on its LAST colon-separated price segment.

    The page uses lines like:
        "Komposittfylling, 1 flate, pris fra : 1 365 kr"
        "Tannkrone metallfri (zirkonia, monoblock): 7 300 kr"
        "3-leddsbro på to implantat: : 53 593 kr"
    The price segment is to the right of the last colon-with-whitespace; the
    name keeps any earlier colons. Lines with no price segment containing
    digits are not bullets and yield None (e.g. paragraph descriptions).
    """
    matches = list(_BULLET_SEP_RE.finditer(line))
    if not matches:
        return None
    last = matches[-1]
    name = line[: last.start()].strip()
    price = line[last.end() :].strip()
    if not name or not price:
        return None
    if not _NAME_HAS_WORD_RE.search(name):
        # Stray bracket / punctuation only: parser artefact (see _NAME_HAS_WORD_RE).
        return None
    if not _DIGIT_RE.search(price):
        # No digits in the right-hand segment: this is descriptive prose
        # (e.g. "Pris for komposittfylling inkluderer ikke ..."), not a price.
        return None
    return name, price


def parse_prisliste(
    html: str, *, klinikk_id: str = "", hentet_dato: str = ""
) -> list[PriceRow]:
    rows: list[PriceRow] = []
    h = HTMLParser(html)
    for item in h.css(".elementor-price-list-item"):
        title_el = item.css_first(".elementor-price-list-title")
        if title_el is None:
            continue
        title = title_el.text(strip=True)
        if not title:
            continue

        price_el = item.css_first(".elementor-price-list-price")
        price_text = price_el.text(strip=True) if price_el is not None else ""

        if price_text and _DIGIT_RE.search(price_text):
            # Direct-priced item: title + price live in sibling spans.
            _emit(rows, title, price_text, klinikk_id, hentet_dato)
            continue

        desc_el = item.css_first(".elementor-price-list-description")
        if desc_el is None:
            continue
        desc = desc_el.text(separator="\n", strip=True)
        for raw_line in desc.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            split = _split_bullet(line)
            if split is None:
                continue
            name, price = split
            _emit(rows, name, price, klinikk_id, hentet_dato)
    return rows


def parse_clinic(html: str) -> dict[str, str]:
    """Best-effort clinic-info extraction.

    OralCare's clinic pages don't always publish a postnummer (Linderud only
    shows "Erich Mogensøns vei 38" without postnummer/by). We return whatever
    fields the page provides; missing fields are simply absent from the dict.
    """
    h = HTMLParser(html)
    text = h.text(separator="\n", strip=True)
    m = _ADDRESS_RE.search(text)
    if m:
        return {
            "adresse": m.group(1).strip(),
            "postnummer": m.group(2),
            "by": m.group(3),
        }
    # Fallback: scan line-by-line for a line that ends with a street-name
    # keyword (vei/gate/etc.) followed by a house number. Returns just
    # `adresse` if found; postnummer/by remain unset.
    line_re = re.compile(
        r"^[A-ZÆØÅ][\w.æøåÆØÅ’'\- ]*?\s+"
        r"(?:vei|veien|veg|vegen|gate|gata|gaten|allé|alleen|plass|plassen)\s+\d+\w*$",
        re.IGNORECASE | re.UNICODE,
    )
    for line in text.splitlines():
        line = line.strip()
        if line_re.match(line):
            return {"adresse": line}
    return {}
