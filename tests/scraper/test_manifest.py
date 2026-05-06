import pytest

from scraper.manifest import ManifestError, validate_manifest

_VALID_ENTRY = {
    "klinikk_id": "odontia__oslo_sentrum",
    "kjede": "odontia",
    "klinikk_navn": "Odontia Oslo Sentrum",
    "klinikk_url": "https://odontia.no/tannlege/oslo-sentrum",
    "prisliste_url": "https://odontia.no/prisliste/tannlege-oslo-sentrum/",
}


def _entry(**overrides):
    return {**_VALID_ENTRY, **overrides}


def test_validate_manifest_accepts_empty_list():
    validate_manifest([])


def test_validate_manifest_accepts_well_formed_entries():
    validate_manifest([_VALID_ENTRY])


def test_validate_manifest_rejects_duplicate_klinikk_ids():
    with pytest.raises(ManifestError, match="duplicate"):
        validate_manifest([_VALID_ENTRY, _VALID_ENTRY])


def test_validate_manifest_rejects_bad_klinikk_id_format():
    with pytest.raises(ManifestError, match="invalid"):
        validate_manifest([_entry(klinikk_id="Odontia-Oslo")])


def test_validate_manifest_rejects_unknown_kjede_token():
    with pytest.raises(ManifestError, match="invalid"):
        validate_manifest([_entry(klinikk_id="tannlegen__oslo")])


def test_validate_manifest_rejects_entry_missing_required_field():
    incomplete = {k: v for k, v in _VALID_ENTRY.items() if k != "klinikk_url"}
    with pytest.raises(ManifestError, match="missing"):
        validate_manifest([incomplete])
