import argparse
import sys
import time
from datetime import date
from pathlib import Path

from scraper.config import (
    CLINIC_MANIFEST_PATH,
    CLINICS_CSV,
    HTML_CACHE_DIR,
    PRICES_RAW_CSV,
    SCRAPE_LOG_CSV,
)
from scraper.fetch import RobotsBlockedError, fetch_with_cache
from scraper.log import ScrapeLog
from scraper.manifest import ManifestError, load_clinic_manifest, validate_manifest
from scraper.output import write_clinics, write_prices_raw
from scraper.parsers import colosseum, oc, odontia, oris
from scraper.slug import parse_klinikk_id

PARSERS = {"odontia": odontia, "colosseum": colosseum, "oc": oc, "oris": oris}


def _cache_path(klinikk_id: str, kind: str) -> Path:
    kjede, slug = parse_klinikk_id(klinikk_id)
    return HTML_CACHE_DIR / kjede / f"{slug}_{kind}.html"


def _fetch(url: str, cache_path: Path, refetch: bool, log: ScrapeLog, klinikk_id: str) -> str | None:
    cache_hit = cache_path.exists() and not refetch
    start = time.monotonic()
    try:
        html = fetch_with_cache(url, cache_path, refetch=refetch)
    except RobotsBlockedError as exc:
        log.record(klinikk_id, url, "blocked_robots", error=str(exc))
        return None
    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        log.record(klinikk_id, url, "http_error", duration_ms=elapsed, error=str(exc))
        return None
    elapsed = int((time.monotonic() - start) * 1000)
    log.record(
        klinikk_id, url, "ok", http_code=None if cache_hit else 200, duration_ms=elapsed
    )
    return html


def _clinic_row(entry: dict, info: dict, struktur: str) -> dict:
    return {
        "klinikk_id": entry["klinikk_id"],
        "kjede": entry["kjede"],
        "klinikk_navn": entry["klinikk_navn"],
        "adresse": info.get("adresse"),
        "postnummer": info.get("postnummer"),
        "by": info.get("by"),
        "klinikk_url": entry.get("klinikk_url"),
        "prisliste_url": entry["prisliste_url"],
        "helsesmart_url": entry.get("helsesmart_url"),
        "prisliste_struktur": struktur,
        "notes": entry.get("notes"),
    }


def _scrape_entry(entry: dict, refetch: bool, log: ScrapeLog, hentet_dato: str) -> tuple[dict, list]:
    klinikk_id = entry["klinikk_id"]
    kjede = entry["kjede"]
    struktur = entry.get("prisliste_struktur", "per_klinikk")
    parser = PARSERS[kjede]

    if struktur == "sentral":
        prisliste_html = _fetch(
            entry["prisliste_url"],
            _cache_path(klinikk_id, "prisliste"),
            refetch,
            log,
            klinikk_id,
        )
        rows = (
            parser.parse_prisliste(prisliste_html, klinikk_id=klinikk_id, hentet_dato=hentet_dato)
            if prisliste_html
            else []
        )
        return _clinic_row(entry, {}, "sentral"), rows

    if struktur == "peker_på_sentral":
        klinikk_html = _fetch(
            entry["klinikk_url"], _cache_path(klinikk_id, "klinikk"), refetch, log, klinikk_id
        )
        info = parser.parse_clinic(klinikk_html) if klinikk_html else {}
        return _clinic_row(entry, info, "peker_på_sentral"), []

    klinikk_html = _fetch(
        entry["klinikk_url"], _cache_path(klinikk_id, "klinikk"), refetch, log, klinikk_id
    )
    prisliste_html = _fetch(
        entry["prisliste_url"], _cache_path(klinikk_id, "prisliste"), refetch, log, klinikk_id
    )
    info = parser.parse_clinic(klinikk_html) if klinikk_html else {}
    rows = (
        parser.parse_prisliste(prisliste_html, klinikk_id=klinikk_id, hentet_dato=hentet_dato)
        if prisliste_html
        else []
    )
    return _clinic_row(entry, info, "per_klinikk"), rows


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        entries = load_clinic_manifest(CLINIC_MANIFEST_PATH)
        validate_manifest(entries)
    except ManifestError as exc:
        print(f"manifest error: {exc}", file=sys.stderr)
        return 2

    hentet_dato = date.today().isoformat()
    clinic_rows = []
    price_rows = []
    with ScrapeLog(SCRAPE_LOG_CSV) as log:
        for entry in entries:
            clinic_row, rows = _scrape_entry(entry, args.refetch, log, hentet_dato)
            clinic_rows.append(clinic_row)
            price_rows.extend(rows)

    write_clinics(clinic_rows, CLINICS_CSV)
    write_prices_raw(
        [
            {
                "klinikk_id": r.klinikk_id,
                "behandling_navn_raw": r.behandling_navn_raw,
                "pris_min": r.pris_min,
                "pris_max": r.pris_max,
                "prisformat": r.prisformat.value,
                "pris_kilde": r.pris_kilde,
                "kommentar": r.kommentar,
                "hentet_dato": r.hentet_dato,
            }
            for r in price_rows
        ],
        PRICES_RAW_CSV,
    )

    print(
        f"wrote {len(clinic_rows)} clinic(s) and {len(price_rows)} price row(s) "
        f"to {CLINICS_CSV.name}, {PRICES_RAW_CSV.name} (log: {SCRAPE_LOG_CSV.name})"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scraper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run scrape against the clinic manifest")
    p_run.add_argument(
        "--refetch", action="store_true", help="Ignore html_cache; refetch all pages"
    )
    p_run.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
