from pathlib import Path

import pytest
import yaml
from sqlalchemy import func, select

from app.models import (
    DataLocation,
    Evidence,
    KeyManagement,
    Organization,
    ReviewStatus,
    Service,
    ServiceVariant,
)
from app.seed import SeedError, load_seed

REAL_DATA_DIR = Path(__file__).resolve().parents[2] / "data"

EVIDENCE = {"source": "https://beispiel.example/quelle", "retrieved": "2026-10-13"}


def valid_seed() -> dict:
    """Kleinster vollständiger Datensatz: zwei Dienste, einer mit US-Konzernmutter."""
    return {
        "countries.yaml": [
            {"code": "DE", "name": "Deutschland", "jurisdiction": "EU_EWR"},
            {"code": "US", "name": "USA", "jurisdiction": "USA"},
        ],
        "organizations.yaml": [
            {"slug": "holding", "name": "Holding Inc.", "country": "US"},
            {
                "slug": "anbieter",
                "name": "Anbieter GmbH",
                "country": "DE",
                "parent": {"value": "holding", **EVIDENCE},
            },
            {"slug": "eu-anbieter", "name": "EU-Anbieter GmbH", "country": "DE"},
        ],
        "categories.yaml": [{"slug": "office", "name": "Büro"}],
        "certificates.yaml": [{"slug": "bsi-c5", "name": "BSI C5", "issuer": "BSI"}],
        "services/office.yaml": {
            "slug": "office",
            "name": "Office",
            "provider": "anbieter",
            "category": "office",
            "typical_criticality": "HOCH",
            "aliases": ["O365"],
            "variants": [
                {
                    "slug": "standard",
                    "name": "Standard",
                    "default": True,
                    "data_location": {"value": "EU_WAEHLBAR", "quote": "Zitat", **EVIDENCE},
                    "openness": "PROPRIETAER",
                    "governing_law": "DE",
                    "certificates": [{"certificate": "bsi-c5", **EVIDENCE}],
                    "dependencies": [
                        {"supplier": "holding", "kind": "HOSTING", "critical": True, **EVIDENCE}
                    ],
                    "review": {"status": "KI_NACHGEPRUEFT", "date": "2026-10-13"},
                }
            ],
            "alternatives": [{"service": "eu-office", "effort": "HOCH", "note": "Hinweis"}],
        },
        "services/eu-office.yaml": {
            "slug": "eu-office",
            "name": "EU Office",
            "provider": "eu-anbieter",
            "category": "office",
            "typical_criticality": "MITTEL",
            "variants": [
                {
                    "slug": "standard",
                    "name": "Standard",
                    "default": True,
                    "review": {"status": "KI_VORSCHLAG"},
                }
            ],
        },
    }


def write_seed(directory: Path, seed: dict) -> Path:
    for name, content in seed.items():
        file = directory / name
        file.parent.mkdir(parents=True, exist_ok=True)
        text = content if isinstance(content, str) else yaml.safe_dump(content, allow_unicode=True)
        file.write_text(text, encoding="utf-8")
    return directory


def count(session, model) -> int:
    return session.scalar(select(func.count()).select_from(model))


def errors_for(tmp_path, session, seed) -> str:
    with pytest.raises(SeedError) as raised:
        load_seed(session, write_seed(tmp_path, seed))
    return "\n".join(raised.value.errors)


def test_valid_seed_is_loaded(session, tmp_path):
    report = load_seed(session, write_seed(tmp_path, valid_seed()))
    session.expire_all()

    assert (report.services, report.variants, report.organizations) == (2, 2, 3)
    office = session.scalars(select(Service).where(Service.slug == "office")).one()
    variant = office.variants[0]
    assert office.provider.ultimate_parent.slug == "holding"
    assert [alias.alias for alias in office.aliases] == ["O365"]
    assert variant.data_location is DataLocation.EU_WAEHLBAR
    assert variant.key_management is KeyManagement.UNBEKANNT
    assert variant.governing_law_country.name == "Deutschland"
    assert variant.review_status is ReviewStatus.KI_NACHGEPRUEFT
    assert variant.certificates[0].certificate.slug == "bsi-c5"
    assert variant.dependencies[0].supplier.slug == "holding"
    assert office.alternatives[0].alternative.slug == "eu-office"


def test_evidence_is_stored_for_each_sourced_fact(session, tmp_path):
    load_seed(session, write_seed(tmp_path, valid_seed()))

    evidence = session.scalars(select(Evidence)).all()
    assert sorted(item.attribute for item in evidence) == [
        "certificate:bsi-c5",
        "data_location",
        "dependency:holding:HOSTING",
        "ultimate_parent",
    ]
    by_attribute = {item.attribute: item for item in evidence}
    assert by_attribute["data_location"].quote == "Zitat"
    assert by_attribute["ultimate_parent"].organization.slug == "anbieter"


def test_loading_twice_changes_nothing(session, tmp_path):
    directory = write_seed(tmp_path, valid_seed())
    load_seed(session, directory)
    ids_before = dict(session.execute(select(ServiceVariant.slug, ServiceVariant.id)).all())
    evidence_before = count(session, Evidence)

    load_seed(session, directory)

    assert dict(session.execute(select(ServiceVariant.slug, ServiceVariant.id)).all()) == ids_before
    assert count(session, Evidence) == evidence_before
    assert count(session, Service) == 2


def test_database_follows_changed_and_removed_files(session, tmp_path):
    seed = valid_seed()
    directory = write_seed(tmp_path, seed)
    load_seed(session, directory)
    office_id = session.scalar(select(Service.id).where(Service.slug == "office"))

    seed["services/office.yaml"]["name"] = "Office Neu"
    del seed["services/office.yaml"]["alternatives"]
    del seed["services/office.yaml"]["variants"][0]["data_location"]
    write_seed(directory, seed)
    (directory / "services/eu-office.yaml").unlink()
    load_seed(session, directory)
    session.expire_all()

    office = session.scalars(select(Service)).one()
    assert (office.id, office.name) == (office_id, "Office Neu")
    assert office.variants[0].data_location is DataLocation.UNBEKANNT
    assert office.alternatives == []


def test_files_starting_with_underscore_are_skipped(session, tmp_path):
    seed = valid_seed()
    seed["services/_vorlage.yaml"] = {"slug": "vorlage", "unsinn": True}

    report = load_seed(session, write_seed(tmp_path, seed))

    assert report.services == 2


def test_unknown_reference_is_reported_with_file(session, tmp_path):
    seed = valid_seed()
    seed["services/office.yaml"]["provider"] = "gibt-es-nicht"

    errors = errors_for(tmp_path, session, seed)

    assert "services/office.yaml" in errors
    assert "gibt-es-nicht" in errors


def test_misspelled_value_is_reported(session, tmp_path):
    seed = valid_seed()
    seed["services/office.yaml"]["variants"][0]["openness"] = "PROPRIETÄR"

    assert "openness" in errors_for(tmp_path, session, seed)


def test_unknown_field_is_reported(session, tmp_path):
    seed = valid_seed()
    seed["services/office.yaml"]["variants"][0]["data_lokation"] = "NICHT_EU"

    assert "data_lokation" in errors_for(tmp_path, session, seed)


def test_unquoted_country_code_no_is_reported(session, tmp_path):
    seed = valid_seed()
    seed["countries.yaml"] = "- code: NO\n  name: Norwegen\n  jurisdiction: EU_EWR\n"

    assert "countries.yaml" in errors_for(tmp_path, session, seed)


@pytest.mark.parametrize("defaults", [(False,), (True, True)])
def test_service_needs_exactly_one_default_variant(session, tmp_path, defaults):
    seed = valid_seed()
    template = seed["services/eu-office.yaml"]["variants"][0]
    seed["services/eu-office.yaml"]["variants"] = [
        {**template, "slug": f"v{index}", "default": is_default}
        for index, is_default in enumerate(defaults)
    ]

    assert "Standardvariante" in errors_for(tmp_path, session, seed)


def test_level_defining_fact_requires_evidence(session, tmp_path):
    seed = valid_seed()
    seed["services/office.yaml"]["variants"][0]["data_location"] = "EU_WAEHLBAR"

    errors = errors_for(tmp_path, session, seed)

    assert "data_location" in errors
    assert "Nachweis" in errors


def test_parent_requires_evidence(session, tmp_path):
    seed = valid_seed()
    seed["organizations.yaml"][1]["parent"] = "holding"

    assert "Nachweis" in errors_for(tmp_path, session, seed)


def test_alias_must_be_unique_across_services(session, tmp_path):
    seed = valid_seed()
    seed["services/eu-office.yaml"]["aliases"] = ["o365"]

    assert "o365" in errors_for(tmp_path, session, seed).lower()


def test_file_name_must_match_slug(session, tmp_path):
    seed = valid_seed()
    seed["services/falscher-name.yaml"] = seed.pop("services/eu-office.yaml")
    del seed["services/office.yaml"]["alternatives"]

    assert "falscher-name.yaml" in errors_for(tmp_path, session, seed)


def test_reviewed_status_requires_date(session, tmp_path):
    seed = valid_seed()
    seed["services/office.yaml"]["variants"][0]["review"] = {"status": "GEPRUEFT"}

    assert "review" in errors_for(tmp_path, session, seed)


def test_all_errors_are_reported_and_nothing_is_written(session, tmp_path):
    seed = valid_seed()
    seed["services/office.yaml"]["provider"] = "gibt-es-nicht"
    seed["services/eu-office.yaml"]["category"] = "auch-nicht"

    with pytest.raises(SeedError) as raised:
        load_seed(session, write_seed(tmp_path, seed))

    assert len(raised.value.errors) == 2
    assert count(session, Organization) == 0


def test_real_data_loads(session):
    report = load_seed(session, REAL_DATA_DIR)

    assert report.services >= 20
    assert report.variants >= 23
    assert count(session, Evidence) >= 70
