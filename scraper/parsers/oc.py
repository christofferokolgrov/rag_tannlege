import re

from selectolax.parser import HTMLParser

from scraper.parsers import PriceRow
from scraper.prisformat import PrisformatError, parse_price

PRIS_KILDE = "klinikk_egen"

_ADDRESS_RE = re.compile(
    r"([^,\n]+?),\s*(\d{4})[\s\xa0]+([A-Za-zÆØÅæøå]+)"
)
_PRICE_PREFIX_RE = re.compile(r"^\s*Pris\s*:\s*", re.IGNORECASE)
_PRICE_FRA_RE = re.compile(r"^\s*Fra\s*:\s*", re.IGNORECASE)
_TRAILING_DASH_RE = re.compile(r"[;,][-–—]\s*$")


def _clean_price(raw: str) -> str:
    s = raw.replace("\xa0", " ")
    s = _PRICE_PREFIX_RE.sub("", s)
    s = _PRICE_FRA_RE.sub("", s)
    s = _TRAILING_DASH_RE.sub("", s)
    return s.strip()


def parse_prisliste(
    html: str, *, klinikk_id: str = "", hentet_dato: str = ""
) -> list[PriceRow]:
    rows: list[PriceRow] = []
    h = HTMLParser(html)
    section = h.css_first("section.pricing")
    if section is None:
        return rows

    for pl in section.css(".pricing-list"):
        for name_node in pl.css("p.font-bold"):
            name = name_node.text(strip=True)
            if not name:
                continue
            container = name_node.parent
            if container is None:
                continue
            price_text = None
            for p in container.css("p"):
                txt = p.text(strip=True)
                if txt.lower().startswith("pris:"):
                    price_text = txt
                    break
            if price_text is None:
                continue
            try:
                parsed = parse_price(_clean_price(price_text))
            except PrisformatError:
                continue
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
    return rows


def parse_clinic(html: str) -> dict[str, str]:
    h = HTMLParser(html)
    text = h.text(separator="\n", strip=True)
    m = _ADDRESS_RE.search(text)
    if not m:
        raise ValueError("could not extract address from clinic page")
    return {
        "adresse": m.group(1).strip(),
        "postnummer": m.group(2),
        "by": m.group(3),
    }
