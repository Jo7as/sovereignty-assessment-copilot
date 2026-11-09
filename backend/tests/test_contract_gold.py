"""Die Musterlösung für die Vertragsanalyse ist vollständig und ihre Zitate stimmen.

Die Zitate werden nur geprüft, wenn die PDFs geladen sind (scripts/fetch_contracts.py).
"""

from pathlib import Path

import pytest
import yaml

from app.matching.quotes import is_quoted
from app.models.enums import (
    AiTraining,
    DataExport,
    DataLocation,
    KeyManagement,
    OperationsLocation,
    TransferBasis,
)

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "data" / "testdata" / "contracts"
SOURCES = {
    source["id"]: source
    for source in yaml.safe_load((CONTRACTS_DIR / "sources.yaml").read_text())["contracts"]
}
GOLD = {
    path.stem: yaml.safe_load(path.read_text()) for path in (CONTRACTS_DIR / "gold").glob("*.yaml")
}

NOT_FOUND = "NICHT_GEFUNDEN"
CHECK = {"VORHANDEN", "TEILWEISE"}
# Felder der Themenblöcke für den Dokumenttyp AVV, mit erlaubten Werten (ohne UNBEKANNT)
FIELDS = {
    "data_location": {value for value in DataLocation if value != DataLocation.UNBEKANNT},
    "operations_location": {v for v in OperationsLocation if v != OperationsLocation.UNBEKANNT},
    "transfer_basis": {value for value in TransferBasis if value != TransferBasis.UNBEKANNT},
    "key_management": {value for value in KeyManagement if value != KeyManagement.UNBEKANNT},
    "data_export": {value for value in DataExport if value != DataExport.UNBEKANNT},
    "ai_training_on_customer_data": {v for v in AiTraining if v != AiTraining.UNBEKANNT},
    **{f"dora_30_{item}": CHECK for item in ("2_a", "2_b", "2_d", "3_e")},
    **{f"dsgvo_28_3_{letter}": CHECK for letter in "abcdefgh"},
}


def test_every_source_has_a_gold_file_and_vice_versa():
    assert set(GOLD) == set(SOURCES)


@pytest.mark.parametrize("contract", sorted(GOLD))
def test_gold_labels_every_field_with_an_allowed_value(contract):
    fields = GOLD[contract]["fields"]

    assert set(fields) == set(FIELDS)
    for name, label in fields.items():
        allowed = FIELDS[name] | {NOT_FOUND}
        assert label["value"] in allowed, name
        assert set(label.get("also_correct", [])) <= allowed, name


@pytest.mark.parametrize("contract", sorted(GOLD))
def test_found_values_have_evidence_on_an_existing_page(contract):
    pages = SOURCES[contract]["pages"]

    for name, label in GOLD[contract]["fields"].items():
        evidence = label.get("evidence", [])
        if label["value"] == NOT_FOUND:
            assert not evidence, name
            continue
        assert evidence, name
        assert all(1 <= item["page"] <= pages for item in evidence), name


@pytest.mark.parametrize("contract", sorted(GOLD))
def test_gold_quotes_stand_on_the_given_page(contract):
    pdf = CONTRACTS_DIR / "pdf" / f"{contract}.pdf"
    if not pdf.exists():
        pytest.skip("PDF nicht geladen: uv run python scripts/fetch_contracts.py")
    from pypdf import PdfReader

    pages = [page.extract_text() or "" for page in PdfReader(pdf).pages]

    missing = [
        (name, item["page"], item["quote"][:60])
        for name, label in GOLD[contract]["fields"].items()
        for item in label.get("evidence", [])
        if not is_quoted(item["quote"], pages[item["page"] - 1])
    ]
    assert missing == []
