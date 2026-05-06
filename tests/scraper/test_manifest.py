import pytest

from scraper.manifest import ManifestError, validate_manifest


def test_validate_manifest_accepts_empty_list():
    validate_manifest([])


def test_validate_manifest_rejects_duplicate_klinikk_ids():
    with pytest.raises(ManifestError, match="duplicate"):
        validate_manifest(
            [
                {"klinikk_id": "odontia__oslo_sentrum"},
                {"klinikk_id": "odontia__oslo_sentrum"},
            ]
        )


def test_validate_manifest_rejects_bad_klinikk_id_format():
    with pytest.raises(ManifestError, match="invalid"):
        validate_manifest([{"klinikk_id": "Odontia-Oslo"}])


def test_validate_manifest_rejects_unknown_kjede_token():
    with pytest.raises(ManifestError, match="invalid"):
        validate_manifest([{"klinikk_id": "tannlegen__oslo"}])


def test_validate_manifest_accepts_well_formed_entries():
    validate_manifest(
        [
            {"klinikk_id": "odontia__oslo_sentrum"},
            {"klinikk_id": "oc__taasen"},
            {"klinikk_id": "oris__central"},
        ]
    )
