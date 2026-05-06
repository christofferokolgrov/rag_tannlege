import argparse
import sys
import time
from datetime import date
from pathlib import Path

import yaml

from collections import Counter, defaultdict

from scraper.config import (
    CLINIC_MANIFEST_PATH,
    CLINICS_CSV,
    HELSESMART_TARGETS_PATH,
    HTML_CACHE_DIR,
    PRICES_RAW_CSV,
    SCRAPE_LOG_CSV,
    TREATMENTS_OBSERVED_PATH,
)
from scraper.fetch import RobotsBlockedError, fetch_with_cache
from scraper.log import ScrapeLog
from scraper.manifest import ManifestError, load_clinic_manifest, validate_manifest
from scraper.output import write_clinics, write_prices_raw
from scraper.parsers import colosseum, helsesmart, oc, odontia, oris, single_json
from scraper.slug import parse_klinikk_id

PARSERS = {
    "odontia": odontia,
    "colosseum": colosseum,
    "oc": oc,
    "oris": oris,
    # Independent Oslo-area clinics — prices pre-extracted via DeepSeek
    # over each clinic's own website HTML; parser reads from
    # data/single_clinics_extracted/<slug>.json. See PRD #31 + tools/extract_single_clinics.py.
    "single": single_json,
}


def _cache_path(klinikk_id: str, kind: str) -> Path:
    kjede, slug = parse_klinikk_id(klinikk_id)
    return HTML_CACHE_DIR / kjede / f"{slug}_{kind}.html"


def _helsesmart_cache_path(klinikk_id: str) -> Path:
    _, slug = parse_klinikk_id(klinikk_id)
    return HTML_CACHE_DIR / "helsesmart" / f"{slug}.html"


def _emit_treatments_observed(price_rows) -> None:
    """Group emitted PriceRows by kjede + behandling_navn_raw, count clinics
    that publish each name. Idempotent: same input always produces the same
    YAML.
    """
    # kjede → name → set of klinikk_ids
    by_kjede: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in price_rows:
        kjede = row.klinikk_id.split("__", 1)[0]
        by_kjede[kjede][row.behandling_navn_raw].add(row.klinikk_id)

    output: dict = {}
    for kjede in sorted(by_kjede):
        names = by_kjede[kjede]
        output[kjede] = [
            {"name": name, "forekomst_klinikker": len(names[name])}
            for name in sorted(names)
        ]

    TREATMENTS_OBSERVED_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TREATMENTS_OBSERVED_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(output, f, allow_unicode=True, sort_keys=False)


def _load_helsesmart_targets() -> list[dict]:
    if not HELSESMART_TARGETS_PATH.exists():
        return []
    with HELSESMART_TARGETS_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return list(data.get("targets") or [])


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

    # kjede=single uses HelseSmart as the only data source; klinikk_url and
    # prisliste_url point at the same HelseSmart page, so we fetch once and
    # use the result for both parse_clinic (returns {}) and parse_prisliste.
    if kjede == "single":
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
        return _clinic_row(entry, {}, "per_klinikk"), rows

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
    clinics_by_id = {e["klinikk_id"]: e for e in entries}
    helsesmart_url_by_klinikk: dict[str, str] = {}

    with ScrapeLog(SCRAPE_LOG_CSV) as log:
        for entry in entries:
            clinic_row, rows = _scrape_entry(entry, args.refetch, log, hentet_dato)
            clinic_rows.append(clinic_row)
            price_rows.extend(rows)

        for target in _load_helsesmart_targets():
            klinikk_id = target["klinikk_id"]
            if klinikk_id not in clinics_by_id:
                log.record(
                    klinikk_id,
                    target["helsesmart_url"],
                    "http_error",
                    error="helsesmart target references unknown klinikk_id",
                )
                continue
            html = _fetch(
                target["helsesmart_url"],
                _helsesmart_cache_path(klinikk_id),
                args.refetch,
                log,
                klinikk_id,
            )
            if html is None:
                continue
            rows = helsesmart.parse_helsesmart_clinic(
                html,
                klinikk_id=klinikk_id,
                hentet_dato=hentet_dato,
                filter_treatments=target.get("treatments"),
            )
            price_rows.extend(rows)
            helsesmart_url_by_klinikk[klinikk_id] = target["helsesmart_url"]

    # Populate helsesmart_url on clinics where HelseSmart was actually used.
    for row in clinic_rows:
        if row["klinikk_id"] in helsesmart_url_by_klinikk:
            row["helsesmart_url"] = helsesmart_url_by_klinikk[row["klinikk_id"]]

    _emit_treatments_observed(price_rows)

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
                "inkluderer_raw": r.inkluderer_raw,
                "ekskluderer_raw": r.ekskluderer_raw,
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
