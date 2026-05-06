import re

from selectolax.parser import HTMLParser

from scraper.parsers import PriceRow
from scraper.prisformat import PrisformatError, parse_price

PRIS_KILDE = "helsesmart"

# HelseSmart item anchors carry text like:
#   "HELPROTESE, EN KJEVE||PRIS (10,200-15,285,-) FASTSLÅS VED KONSULTASJON|||Bestill time||"
# We split on the literal price marker "PRIS (".
_PRICE_RE = re.compile(r"PRIS\s*\(([^)]+)\)\s*(.*)", re.IGNORECASE | re.DOTALL)
_NAME_TRIM_RE = re.compile(r"\s*\|+\s*$")


def _treatment_name(text_before_price: str) -> str:
    # Strip leading/trailing pipes that text(separator='|') leaves behind.
    return _NAME_TRIM_RE.sub("", text_before_price.strip("| ").strip())


def parse_helsesmart_clinic(
    html: str, *, klinikk_id: str, hentet_dato: str = "", filter_treatments: list[str] | None = None
) -> list[PriceRow]:
    """Parse a HelseSmart `/klinikk/<slug>/priser/` page. Returns rows tagged
    pris_kilde=helsesmart.

    `filter_treatments`, when provided, is a list of treatment-name substrings;
    only rows whose behandling_navn_raw contains one of them (case-insensitive)
    are emitted. Used by helsesmart_targets.yaml to opt in selectively.
    """
    rows: list[PriceRow] = []
    h = HTMLParser(html)
    for item in h.css("a"):
        text = item.text(separator="|", strip=True)
        if "PRIS" not in text or "(" not in text:
            continue
        # Split text into name (before "PRIS (") and price descriptor (the parens).
        idx = text.upper().find("PRIS")
        name = _treatment_name(text[:idx])
        if not name:
            continue
        m = _PRICE_RE.search(text[idx:])
        if not m:
            continue
        # HelseSmart uses English-style thousands separators ("11,900-32,000").
        # Normalise to space-separated thousands so parse_price handles it.
        raw_price = m.group(1).replace(",", " ")
        try:
            parsed = parse_price(raw_price)
        except PrisformatError:
            continue

        if filter_treatments and not any(
            f.lower() in name.lower() for f in filter_treatments
        ):
            continue

        rows.append(
            PriceRow(
                klinikk_id=klinikk_id,
                behandling_navn_raw=name,
                pris_min=parsed.pris_min,
                pris_max=parsed.pris_max,
                prisformat=parsed.prisformat,
                pris_kilde=PRIS_KILDE,
                kommentar="FASTSLÅS VED KONSULTASJON" if "fastslås" in m.group(2).lower() else "",
                hentet_dato=hentet_dato,
            )
        )
    return rows


# Standard parser interface — symmetrical with parsers/odontia.py etc., so
# scraper/cli.py can register PARSERS["single"] = helsesmart and dispatch
# uniformly. Used for kjede=single (independent Oslo-area clinics) where
# HelseSmart is the primary data source.

def parse_prisliste(
    html: str, *, klinikk_id: str = "", hentet_dato: str = ""
) -> list[PriceRow]:
    """Standard-interface wrapper around parse_helsesmart_clinic that
    returns ALL priced rows (no filter_treatments). Used by kjede=single."""
    return parse_helsesmart_clinic(
        html, klinikk_id=klinikk_id, hentet_dato=hentet_dato, filter_treatments=None
    )


def parse_clinic(html: str) -> dict:
    """HelseSmart pages don't expose the same address structure the chains'
    own clinic pages have. clinics.csv ends up with empty adresse / postnummer
    / by for kjede=single rows, which is the honest scrape — design §1
    raw-scrape policy."""
    return {}
