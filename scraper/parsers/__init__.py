from dataclasses import dataclass, field

from scraper.prisformat import Prisformat


@dataclass(frozen=True)
class PriceRow:
    klinikk_id: str
    behandling_navn_raw: str
    pris_min: int | None
    pris_max: int | None
    prisformat: Prisformat
    pris_kilde: str
    kommentar: str
    hentet_dato: str
    inkluderer_raw: str = ""
    ekskluderer_raw: str = ""
