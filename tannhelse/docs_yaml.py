from pathlib import Path

import yaml

_ALLOWED_KEYS = frozenset({"title", "short_title", "url"})


def load_overrides(path: Path) -> dict[str, dict[str, str]]:
    """Load `docs.yaml` document-title overrides.

    Schema: top-level mapping of `<pdf_filename>` → `{title?, short_title?}`.

    Returns `{}` if the file does not exist (overrides are optional). Raises
    `ValueError` with a clear message if the YAML is malformed, the top level
    is not a mapping, an entry value is not a mapping, or an entry contains
    keys outside `{"title", "short_title"}`.
    """
    if not path.exists():
        return {}

    raw = path.read_text(encoding="utf-8")
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid docs.yaml: {e}") from e

    if parsed is None:
        return {}

    if not isinstance(parsed, dict):
        raise ValueError(
            f"Invalid docs.yaml: top-level must be a mapping, got {type(parsed).__name__}"
        )

    for filename, entry in parsed.items():
        if not isinstance(entry, dict):
            raise ValueError(
                f"Invalid docs.yaml: entry for {filename!r} must be a mapping, "
                f"got {type(entry).__name__}"
            )
        unknown = set(entry.keys()) - _ALLOWED_KEYS
        if unknown:
            raise ValueError(
                f"Invalid docs.yaml: entry for {filename!r} has unknown keys "
                f"{sorted(unknown)}; allowed: {sorted(_ALLOWED_KEYS)}"
            )

    return parsed
