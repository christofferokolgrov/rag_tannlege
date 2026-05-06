import re
import unicodedata
from collections import defaultdict

KJEDE_TOKENS = frozenset({"odontia", "oris", "colosseum", "oc", "oralcare", "single"})

KLINIKK_ID_PATTERN = re.compile(
    r"^(odontia|oris|colosseum|oc|oralcare|single)__([a-z0-9_]+)$"
)

_NORWEGIAN_TRANSLIT = {
    "æ": "ae",
    "ø": "oe",
    "å": "aa",
}


def to_slug(name: str) -> str:
    s = name.lower()
    for src, dst in _NORWEGIAN_TRANSLIT.items():
        s = s.replace(src, dst)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def make_klinikk_id(kjede: str, name: str) -> str:
    if kjede not in KJEDE_TOKENS:
        raise ValueError(
            f"unknown kjede {kjede!r}; expected one of {sorted(KJEDE_TOKENS)}"
        )
    return f"{kjede}__{to_slug(name)}"


def parse_klinikk_id(klinikk_id: str) -> tuple[str, str]:
    m = KLINIKK_ID_PATTERN.match(klinikk_id)
    if not m:
        raise ValueError(f"invalid klinikk_id format: {klinikk_id!r}")
    return m.group(1), m.group(2)


def find_id_collisions(names_by_kjede: dict[str, list[str]]) -> dict[str, list[str]]:
    by_id: dict[str, list[str]] = defaultdict(list)
    for kjede, names in names_by_kjede.items():
        for name in names:
            by_id[make_klinikk_id(kjede, name)].append(name)
    return {kid: ns for kid, ns in by_id.items() if len(ns) > 1}
