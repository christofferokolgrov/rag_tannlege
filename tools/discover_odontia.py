"""Discover all Odontia clinic + prisliste URLs from /klinikker.

Fetches each /tannlege/<slug> page, extracts the linked /prisliste/<...>
URL, and writes manifest entries to stdout in YAML form. Skips clinics
without a prisliste link (specialty pages like /tannlege/oslo-endodonti).

Usage:
    uv run python tools/discover_odontia.py >> data/clinic_discovery.yaml
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from scraper.config import HTML_CACHE_DIR
from scraper.fetch import fetch_with_cache
from scraper.slug import to_slug

KLINIKKER_URL = "https://odontia.no/klinikker"
TANNLEGE_RE = re.compile(r'href="https://odontia\.no/tannlege/([a-z0-9-]+)"')
PRISLISTE_RE = re.compile(r'href="(https://odontia\.no/prisliste/[^"]+)"')


def _discover() -> list[dict]:
    cache = HTML_CACHE_DIR / "odontia" / "_klinikker.html"
    klinikker_html = fetch_with_cache(KLINIKKER_URL, cache)
    slugs = sorted(set(TANNLEGE_RE.findall(klinikker_html)))
    print(f"# discovered {len(slugs)} Odontia /tannlege/ slugs", file=sys.stderr)

    entries: list[dict] = []
    for slug in slugs:
        klinikk_url = f"https://odontia.no/tannlege/{slug}"
        klinikk_id_slug = to_slug(slug.replace("-", "_"))
        cache_path = HTML_CACHE_DIR / "odontia" / f"{klinikk_id_slug}_klinikk.html"
        try:
            html = fetch_with_cache(klinikk_url, cache_path)
        except Exception as exc:
            print(f"# {slug}: fetch error: {exc}", file=sys.stderr)
            continue

        m = PRISLISTE_RE.search(html)
        if not m:
            print(f"# {slug}: no prisliste link found, skipping", file=sys.stderr)
            continue

        prisliste_url = m.group(1)
        klinikk_navn = "Odontia " + slug.replace("-", " ").title()
        entries.append({
            "klinikk_id": f"odontia__{klinikk_id_slug}",
            "kjede": "odontia",
            "klinikk_navn": klinikk_navn,
            "klinikk_url": klinikk_url,
            "prisliste_url": prisliste_url,
            "prisliste_struktur": "per_klinikk",
        })
    return entries


def main() -> int:
    entries = _discover()
    import yaml
    yaml.safe_dump({"clinics": entries}, sys.stdout, allow_unicode=True, sort_keys=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
