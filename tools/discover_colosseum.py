"""Discover all Colosseum clinic URLs from clinic-sitemap.xml.

Each clinic uses the same central prisliste at
colosseumtannlege.no/priser-tannlegebehandling/, so manifest entries
all share that prisliste_url with prisliste_struktur=peker_på_sentral.

Usage:
    uv run python tools/discover_colosseum.py >> data/clinic_discovery.yaml
"""
from __future__ import annotations

import re
import sys

import yaml

from scraper.config import HTML_CACHE_DIR
from scraper.fetch import fetch_with_cache

SITEMAP_URL = "https://colosseumtannlege.no/clinic-sitemap.xml"
URL_RE = re.compile(r"<loc>(https://colosseumtannlege\.no/klinikker/[^<]+)</loc>")
CENTRAL_PRISLISTE = "https://colosseumtannlege.no/priser-tannlegebehandling/"


def _slug_from_url(url: str) -> str:
    # /klinikker/<region>/<city>/<clinic>/  → clinic
    parts = [p for p in url.rstrip("/").split("/") if p]
    return parts[-1].replace("-", "_")


def _navn_from_url(url: str) -> str:
    parts = [p for p in url.rstrip("/").split("/") if p]
    return "Colosseum " + parts[-1].replace("-", " ").title()


def main() -> int:
    cache = HTML_CACHE_DIR / "colosseum" / "_sitemap.xml"
    xml = fetch_with_cache(SITEMAP_URL, cache)
    urls = sorted(set(URL_RE.findall(xml)))
    print(f"# discovered {len(urls)} Colosseum clinic URLs", file=sys.stderr)

    entries: list[dict] = []
    for url in urls:
        # Strip trailing slash so URL is well-formed for our fetcher
        clean = url.rstrip("/") + "/"
        slug = _slug_from_url(url)
        entries.append({
            "klinikk_id": f"colosseum__{slug}",
            "kjede": "colosseum",
            "klinikk_navn": _navn_from_url(url),
            "klinikk_url": clean,
            "prisliste_url": CENTRAL_PRISLISTE,
            "prisliste_struktur": "peker_på_sentral",
        })

    yaml.safe_dump({"clinics": entries}, sys.stdout, allow_unicode=True, sort_keys=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
