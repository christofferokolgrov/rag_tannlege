import csv
from pathlib import Path
from typing import Iterable, Mapping

from scraper.config import CLINICS_COLUMNS, PRICES_RAW_COLUMNS


def _write_csv(path: Path, columns: list[str], rows: Iterable[Mapping]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=columns, quoting=csv.QUOTE_MINIMAL, extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({c: _cell(row.get(c)) for c in columns})


def _cell(value):
    if value is None:
        return ""
    return value


def write_clinics(entries: Iterable[Mapping], path: Path) -> None:
    _write_csv(path, CLINICS_COLUMNS, entries)


def write_prices_raw(rows: Iterable[Mapping], path: Path) -> None:
    _write_csv(path, PRICES_RAW_COLUMNS, rows)
