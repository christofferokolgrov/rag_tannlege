import argparse
import sys

from scraper.config import (
    CLINIC_MANIFEST_PATH,
    CLINICS_CSV,
    PRICES_RAW_CSV,
    SCRAPE_LOG_CSV,
)
from scraper.log import ScrapeLog
from scraper.manifest import ManifestError, load_clinic_manifest, validate_manifest
from scraper.output import write_clinics, write_prices_raw


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        entries = load_clinic_manifest(CLINIC_MANIFEST_PATH)
        validate_manifest(entries)
    except ManifestError as exc:
        print(f"manifest error: {exc}", file=sys.stderr)
        return 2

    write_clinics(entries, CLINICS_CSV)
    write_prices_raw([], PRICES_RAW_CSV)
    with ScrapeLog(SCRAPE_LOG_CSV):
        pass

    print(
        f"wrote {CLINICS_CSV.name}, {PRICES_RAW_CSV.name}, {SCRAPE_LOG_CSV.name} "
        f"({len(entries)} clinic(s) in manifest)"
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
