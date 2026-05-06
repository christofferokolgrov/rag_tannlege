import csv
from pathlib import Path
from typing import Optional

from scraper.config import SCRAPE_LOG_COLUMNS


class ScrapeLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("w", encoding="utf-8", newline="")
        self._writer = csv.DictWriter(self._fh, fieldnames=SCRAPE_LOG_COLUMNS)
        self._writer.writeheader()

    def record(
        self,
        klinikk_id: str,
        url: str,
        status: str,
        http_code: Optional[int] = None,
        duration_ms: Optional[int] = None,
        error: str = "",
    ) -> None:
        self._writer.writerow(
            {
                "klinikk_id": klinikk_id,
                "url": url,
                "status": status,
                "http_code": "" if http_code is None else http_code,
                "duration_ms": "" if duration_ms is None else duration_ms,
                "error": error,
            }
        )

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "ScrapeLog":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
