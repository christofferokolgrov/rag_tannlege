import re
import unicodedata

KJEDE_TOKENS = frozenset({"odontia", "oris", "colosseum", "oc", "oralcare", "single"})

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
