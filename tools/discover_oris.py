"""Discover all Oris clinic URLs from /klinikker.

Each clinic uses the same central prisliste at orisdental.no/prisliste,
so manifest entries all share that prisliste_url with
prisliste_struktur=peker_på_sentral.

Usage:
    uv run python tools/discover_oris.py >> data/clinic_discovery.yaml
"""
from __future__ import annotations

import re
import sys

import yaml

from scraper.config import HTML_CACHE_DIR
from scraper.fetch import fetch_with_cache

KLINIKKER_URL = "https://orisdental.no/klinikker"
URL_RE = re.compile(r'/klinikker/([a-z0-9-]+)')
CENTRAL_PRISLISTE = "https://orisdental.no/prisliste"


def main() -> int:
    cache = HTML_CACHE_DIR / "oris" / "_klinikker.html"
    html = fetch_with_cache(KLINIKKER_URL, cache)
    slugs = sorted(set(URL_RE.findall(html)))
    # Drop the "klinikker" itself if it sneaks in via /klinikker/klinikker
    slugs = [s for s in slugs if s != "klinikker"]
    print(f"# discovered {len(slugs)} Oris clinic slugs", file=sys.stderr)

    entries: list[dict] = []
    for slug in slugs:
        manifest_slug = slug.replace("-", "_")
        entries.append({
            "klinikk_id": f"oris__{manifest_slug}",
            "kjede": "oris",
            "klinikk_navn": "Oris " + slug.replace("-", " ").title(),
            "klinikk_url": f"https://orisdental.no/klinikker/{slug}",
            "prisliste_url": CENTRAL_PRISLISTE,
            "prisliste_struktur": "peker_på_sentral",
        })

    yaml.safe_dump({"clinics": entries}, sys.stdout, allow_unicode=True, sort_keys=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
