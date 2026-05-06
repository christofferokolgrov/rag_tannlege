from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
HTML_CACHE_DIR = DATA_DIR / "html_cache"

CLINIC_MANIFEST_PATH = DATA_DIR / "clinic_discovery.yaml"
HELSESMART_TARGETS_PATH = DATA_DIR / "helsesmart_targets.yaml"
CLINICS_CSV = DATA_DIR / "clinics.csv"
PRICES_RAW_CSV = DATA_DIR / "prices_raw.csv"
SCRAPE_LOG_CSV = DATA_DIR / "scrape_log.csv"

RATE_LIMIT_SECONDS = 1.0
USER_AGENT = (
    "tannhelse-research-bot/0.1 "
    "(+https://github.com/christofferokolgrov/rag_tannlege; ck@drivkapital.no)"
)
FROM_HEADER = "ck@drivkapital.no"

CLINICS_COLUMNS = [
    "klinikk_id",
    "kjede",
    "klinikk_navn",
    "adresse",
    "postnummer",
    "by",
    "klinikk_url",
    "prisliste_url",
    "helsesmart_url",
    "prisliste_struktur",
    "notes",
]

PRICES_RAW_COLUMNS = [
    "klinikk_id",
    "behandling_navn_raw",
    "pris_min",
    "pris_max",
    "prisformat",
    "pris_kilde",
    "kommentar",
    "hentet_dato",
    "inkluderer_raw",
    "ekskluderer_raw",
]

SCRAPE_LOG_COLUMNS = [
    "klinikk_id",
    "url",
    "status",
    "http_code",
    "duration_ms",
    "error",
]
