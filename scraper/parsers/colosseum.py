import re

from selectolax.parser import HTMLParser

from scraper.parsers import PriceRow
from scraper.prisformat import PrisformatError, parse_price

PRIS_KILDE = "sentral"

_LEADING_SEP_RE = re.compile(r"^[-–—]\s*")
# Some Colosseum rows put a clarifier in parens between the treatment name
# and the price, e.g. "Bedøvelse (enkel injeksjon) - fra kr. 205". The
# parens content is metadata, not part of the price; strip it before
# parse_price.
_LEADING_PARENS_RE = re.compile(r"^\s*\([^)]*\)\s*")
_ADDRESS_RE = re.compile(
    r"([^,\n]+?),\s*(\d{4})[\s\xa0]+([A-Za-zÆØÅæøå]+)"
)


def parse_prisliste(
    html: str, *, klinikk_id: str = "colosseum__central", hentet_dato: str = ""
) -> list[PriceRow]:
    rows: list[PriceRow] = []
    h = HTMLParser(html)
    for p in h.css("p"):
        strong = p.css_first("strong")
        if not strong:
            continue
        name = strong.text(strip=True)
        if not name:
            continue
        # The treatment name is in <strong>; the price is a text node that
        # follows it. text(separator='|') splits at every element boundary —
        # for rows like "<strong><a>Fyllinger</a>, én tannflate</strong> -
        # fra kr. 990", parts[1] is the strong's continuation (", én
        # tannflate") rather than the price. Try each part in turn and accept
        # the first that parses; strip leading parens/separators each time.
        full_text = p.text(separator="|", strip=True)
        parts = [p_.strip() for p_ in full_text.split("|") if p_.strip()]
        if len(parts) < 2:
            continue
        # parse_price returns etter_konsultasjon (no exception) for any
        # digit-less input — including the strong's continuation text in
        # multi-strong rows. Restrict to parts that actually contain digits;
        # take the first such part that parses to something other than
        # etter_konsultasjon.
        parsed = None
        for part in parts[1:]:
            if not any(ch.isdigit() for ch in part):
                continue
            candidate = _LEADING_PARENS_RE.sub("", part)
            candidate = _LEADING_SEP_RE.sub("", candidate)
            try:
                parsed = parse_price(candidate)
                break
            except PrisformatError:
                continue
        if parsed is None:
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
        return {}
    return {
        "adresse": m.group(1).strip(),
        "postnummer": m.group(2),
        "by": m.group(3),
    }
