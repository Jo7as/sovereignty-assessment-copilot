"""Ablauf der Vertragsanalyse: Einordnen, Auslesen, Belegprüfung.

Arbeitsanweisung docs/tiefenpruefung-ablauf.md, Abschnitte 5.2 bis 5.4. Die KI ist durch eine
Attrappe ersetzt, die vorgegebene Antworten liefert.
"""

from pathlib import Path

import httpx2
import pytest
import yaml

from app.contracts import DocumentType
from app.contracts import pipeline as pipeline_module
from app.contracts.fields import (
    FIELDS,
    FIELDS_BY_NAME,
    ROUTES,
    Block,
    Kind,
    allowed_values,
    fields_for,
)
from app.contracts.pipeline import (
    MAX_CHUNK,
    BlockAnswer,
    Classification,
    ElementFinding,
    ElementState,
    Evidence,
    FieldState,
    Finding,
    OpenRouterExtractor,
    Rejected,
    Rejection,
    check,
    chunks,
    classify,
    extract,
    extract_block,
    judge,
    merge,
)
from app.matching.ai import InvalidAnswer
from app.matching.text import CatalogService

GOLD_DIR = Path(__file__).resolve().parents[2] / "data" / "testdata" / "contracts" / "gold"

PAGES = [
    "Data Processing Addendum between Customer and Example Cloud GmbH for Example Storage.",
    "",
    "Customer Data will be stored exclusively in data centres within the European Union.",
    "Support may be provided from the United States and India on a follow-the-sun basis.",
]
SERVICES = [
    CatalogService("example-storage", "Example Storage", provider="Example Cloud GmbH"),
    CatalogService("salesforce", "Sales Cloud", provider="Salesforce"),
]


class FakeExtractor:
    """Liefert der Reihe nach die vorgegebenen Antworten und merkt sich die Prompts."""

    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def ask(self, prompt, answer):
        self.prompts.append(prompt)
        reply = self.answers.pop(0)
        if isinstance(reply, Exception):
            raise reply
        assert isinstance(reply, answer)
        return reply


def finding(field="data_location", value="EU_ZUGESICHERT", quote=None, page=3):
    quote = quote or "stored exclusively in data centres within the European Union"
    return Finding(field=field, value=value, quote=quote, page=page)


DATENORT = allowed_values(Block.DATENORT, DocumentType.AVV)


# ---------------------------------------------------------------- Feldkatalog und Routing


def test_every_field_has_values_and_belongs_to_a_block():
    for field in FIELDS:
        assert field.values and field.blocks and field.hint, field.name


def test_every_check_has_core_elements_with_unique_names():
    checks = [field for field in FIELDS if field.values == ("VORHANDEN", "TEILWEISE")]
    names = [item.name for field in checks for item in field.elements]

    assert all(any(e.kind == Kind.KERN for e in field.elements) for field in checks)
    assert all(
        name.startswith(field.name + ".")
        for field in checks
        for name in (item.name for item in field.elements)
    )
    assert len(names) == len(set(names))
    assert max(map(len, names)) <= 60  # Spalte contract_finding.field


def test_avv_route_reads_every_field_of_the_gold_standard():
    """Die Musterlösung labelt die Felder für AVVs. Der Ablauf muss sie alle auslesen."""
    read = {field.name for block in ROUTES[DocumentType.AVV] for field in fields_for(block, "AVV")}
    labelled = {
        name
        for path in GOLD_DIR.glob("*.yaml")
        for name in yaml.safe_load(path.read_text())["fields"]
    }

    assert labelled <= read


def test_standard_clauses_only_give_the_transfer_basis():
    route = ROUTES[DocumentType.STANDARDVERTRAGSKLAUSELN]
    fields = [
        field.name
        for block in route
        for field in fields_for(block, DocumentType.STANDARDVERTRAGSKLAUSELN)
    ]

    assert fields == ["transfer_basis"]


# ---------------------------------------------------------------- Abschnitte


def test_chunks_mark_pages_and_skip_pages_without_text():
    (section,) = chunks(PAGES)

    assert section.startswith("=== Seite 1 ===\nData Processing Addendum")
    assert "=== Seite 2 ===" not in section
    assert "=== Seite 3 ===\nCustomer Data" in section


def test_chunks_never_split_a_page():
    page = "x" * (MAX_CHUNK // 2)
    sections = chunks([page, page, page, "y" * (MAX_CHUNK + 1)])

    assert [section.count("=== Seite") for section in sections] == [1, 1, 1, 1]
    assert sections[3].startswith("=== Seite 4 ===")
    assert all(len(section) <= MAX_CHUNK for section in sections[:3])


# ---------------------------------------------------------------- Belegprüfung


def test_finding_with_quote_on_its_page_is_accepted():
    assert check(finding(), PAGES, DATENORT) == Evidence(
        "data_location",
        "EU_ZUGESICHERT",
        "stored exclusively in data centres within the European Union",
        3,
    )


def test_quote_survives_changed_line_breaks_and_hyphens():
    pages = ["", "", "Customer Data will be stored exclu-\nsively in data centres within the EU."]

    result = check(finding(quote="stored exclusively in data centres"), pages, DATENORT)

    assert isinstance(result, Evidence)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"field": "governing_law", "value": "EU_EWR"}, Rejection.FELD),
        ({"value": "UNBEKANNT"}, Rejection.WERT),
        ({"value": "eu_zugesichert"}, Rejection.WERT),
        ({"quote": "stored exclusively " + "x" * 300}, Rejection.ZITAT_LANG),
        ({"quote": "stored exclusively in data centres in Germany"}, Rejection.ZITAT),
        ({"quote": "EU"}, Rejection.ZITAT),  # zu kurz, um etwas zu belegen
        ({"page": 4}, Rejection.SEITE),
        ({"page": 99}, Rejection.SEITE),
        # Das Urteil fällt der Code, die KI darf es nicht direkt melden
        ({"field": "dora_30_2_b", "value": "VORHANDEN"}, Rejection.FELD),
        ({"field": "dora_30_2_b.orte", "value": "VORHANDEN"}, Rejection.WERT),
        ({"field": "dsgvo_28_3_h.pruefung", "value": "BELEGT"}, Rejection.FELD),
    ],
)
def test_check_rejects_with_reason(changes, reason):
    result = check(finding(**changes), PAGES, DATENORT)

    assert isinstance(result, Rejected)
    assert result.reason == reason


# ---------------------------------------------------------------- Auslesen


def test_block_collects_checked_findings_and_answers_for_the_protocol():
    answer = BlockAnswer(
        findings=[
            finding(),
            finding("operations_location", "WELTWEIT", "on a follow-the-sun basis", 4),
            finding(quote="stored in Frankfurt am Main"),  # erfunden
        ]
    )
    extractor = FakeExtractor(answer)

    result = extract_block(extractor, PAGES, chunks(PAGES), DocumentType.AVV, Block.DATENORT)

    assert [item.field for item in result.accepted] == ["data_location", "operations_location"]
    assert [item.reason for item in result.rejected] == [Rejection.ZITAT]
    assert result.answers == [answer.model_dump()]
    assert result.error is None


def test_prompt_lists_only_the_fields_of_the_block_with_their_values():
    extractor = FakeExtractor(BlockAnswer(findings=[]))

    extract_block(extractor, PAGES, chunks(PAGES), DocumentType.AVV, Block.DATENORT)

    prompt = extractor.prompts[0]
    assert "- data_location: EU_ZUGESICHERT | EU_WAEHLBAR | EU_UND_ANGEMESSEN | NICHT_EU." in prompt
    assert "Prüfpunkt dora_30_2_b: Orte der Leistung und der Datenverarbeitung" in prompt
    assert "- dora_30_2_b.aenderung_vorab: Muss der Anbieter" in prompt
    assert "governing_law" not in prompt and "UNBEKANNT" not in prompt
    assert "=== Seite 3 ===" in prompt


def test_prompt_asks_only_for_elements_of_the_block_and_marks_limits():
    extractor = FakeExtractor(BlockAnswer(findings=[]), BlockAnswer(findings=[]))

    extract_block(extractor, PAGES, chunks(PAGES), DocumentType.AVV, Block.UNTERAUFTRAGNEHMER)
    extract_block(extractor, PAGES, chunks(PAGES), DocumentType.AVV, Block.DSGVO)

    subcontracting, gdpr = extractor.prompts
    assert "dora_30_2_a.unterauftrag_zulaessig" in subcontracting
    assert "leistungsbeschreibung" not in subcontracting  # steht im Rahmenvertrag
    assert "Teil 1, Fakten (Name: erlaubte Werte. Auslegung):\n(keine)" in subcontracting
    assert "- dsgvo_28_3_h.nur_berichte (Einschränkung):" in gdpr
    assert "- dora_30_3_e.inspektion:" in gdpr  # Prüfrechte stehen meist im AVV


def test_element_findings_are_checked_like_facts():
    pages = ["", "The auditor may conduct inspections at the premises of the Processor."]
    answer = BlockAnswer(
        findings=[],
        elements=[
            ElementFinding(
                element="dsgvo_28_3_h.pruefung", quote="may conduct inspections", page=2
            ),
            ElementFinding(
                element="dsgvo_28_3_h.unbekannt", quote="may conduct inspections", page=2
            ),
        ],
    )

    result = extract_block(FakeExtractor(answer), pages, chunks(pages), "AVV", Block.DSGVO)

    assert result.accepted == [
        Evidence("dsgvo_28_3_h.pruefung", "BELEGT", "may conduct inspections", 2)
    ]
    assert [item.reason for item in result.rejected] == [Rejection.FELD]


def test_long_document_is_read_section_by_section():
    pages = ["a" * (MAX_CHUNK - 20), "Customer Data will be stored exclusively in the EU."]
    later = finding(quote="stored exclusively in the EU", page=2)
    extractor = FakeExtractor(BlockAnswer(findings=[]), BlockAnswer(findings=[later]))

    result = extract_block(extractor, pages, chunks(pages), DocumentType.AVV, Block.DATENORT)

    assert len(extractor.prompts) == 2
    assert [item.page for item in result.accepted] == [2]


def test_failed_section_is_reported_and_the_rest_is_kept():
    pages = ["a" * (MAX_CHUNK - 20), "Customer Data will be stored exclusively in the EU."]
    later = finding(quote="stored exclusively in the EU", page=2)
    extractor = FakeExtractor(
        InvalidAnswer("findings: Field required"), BlockAnswer(findings=[later])
    )

    result = extract_block(extractor, pages, chunks(pages), DocumentType.AVV, Block.DATENORT)

    assert result.error == "Abschnitt 1 von 2 nicht ausgelesen: findings: Field required"
    assert len(result.accepted) == 1


def test_document_is_read_in_the_blocks_of_its_type():
    extractor = FakeExtractor(*[BlockAnswer(findings=[]) for _ in ROUTES[DocumentType.AVV]])

    results = extract(extractor, PAGES, DocumentType.AVV)

    assert [result.block for result in results] == list(ROUTES[DocumentType.AVV])
    assert "„Datenort“" in extractor.prompts[0]


# ---------------------------------------------------------------- Einordnen


def test_classification_with_service_and_quote():
    answer = Classification(
        document_type=DocumentType.AVV,
        service="example-storage",
        quote="Example Cloud GmbH for Example Storage",
        page=1,
    )

    result = classify(FakeExtractor(answer), PAGES, SERVICES)

    assert result.document_type == DocumentType.AVV
    assert (result.service, result.page, result.note) == ("example-storage", 1, None)


def test_short_service_name_is_enough_evidence():
    pages = ["STACKIT\nCloud Services\nAuftragsverarbeitungsvertrag"]
    services = [CatalogService("stackit", "STACKIT", provider="Schwarz Gruppe")]
    answer = Classification(
        document_type=DocumentType.AVV, service="stackit", quote="STACKIT", page=1
    )

    result = classify(FakeExtractor(answer), pages, services)

    assert (result.service, result.note) == ("stackit", None)


def test_classification_sees_only_the_first_two_pages_with_text_and_the_inventory():
    answer = Classification(document_type=DocumentType.AVV, service=None, quote=None, page=None)
    extractor = FakeExtractor(answer)

    classify(extractor, PAGES, SERVICES)

    prompt = extractor.prompts[0]
    assert "=== Seite 1 ===" in prompt and "=== Seite 3 ===" in prompt
    assert "=== Seite 4 ===" not in prompt
    assert "example-storage | Example Storage | Example Cloud GmbH" in prompt


@pytest.mark.parametrize(
    ("service", "quote", "page", "note"),
    [
        ("microsoft-365", "Example Cloud GmbH", 1, "steht nicht im IT-Bestand"),
        ("salesforce", "Salesforce Sales Cloud", 1, "verworfen"),  # Zitat erfunden
        ("example-storage", "Example Cloud GmbH", 4, "verworfen"),  # Seite nicht gezeigt
        ("example-storage", "Addendum between Customer", 1, "belegt ihn nicht"),  # kein Name
        ("example-storage", "GmbH", 1, "belegt ihn nicht"),
    ],
)
def test_service_proposal_without_evidence_is_dropped(service, quote, page, note):
    answer = Classification(document_type=DocumentType.AVV, service=service, quote=quote, page=page)

    result = classify(FakeExtractor(answer), PAGES, SERVICES)

    assert result.document_type == DocumentType.AVV
    assert result.service is None
    assert note in result.note


def test_failed_classification_is_reported():
    result = classify(FakeExtractor(httpx2.ConnectError("keine Verbindung")), PAGES, SERVICES)

    assert result.document_type is None
    assert result.note == "Einordnung nicht gelaufen: keine Verbindung"


# ---------------------------------------------------------------- Anbindung


def _status_error(code):
    request = httpx2.Request("POST", "https://openrouter.ai")
    return httpx2.HTTPStatusError("", request=request, response=httpx2.Response(code))


@pytest.mark.parametrize("error", [httpx2.ReadTimeout("zu langsam"), _status_error(503)])
def test_openrouter_extractor_retries_once_on_temporary_errors(monkeypatch, error):
    replies = [error, BlockAnswer(findings=[])]

    def structured(*args):
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(pipeline_module, "structured", structured)

    assert OpenRouterExtractor("key", "model").ask("prompt", BlockAnswer).findings == []


def test_openrouter_extractor_does_not_retry_a_wrong_key(monkeypatch):
    calls = []

    def structured(*args):
        calls.append(args)
        raise _status_error(401)

    monkeypatch.setattr(pipeline_module, "structured", structured)

    with pytest.raises(httpx2.HTTPStatusError):
        OpenRouterExtractor("key", "model").ask("prompt", BlockAnswer)
    assert len(calls) == 1


def test_parallel_extraction_gives_the_same_result_in_the_same_order():
    class ByBlock:
        def ask(self, prompt, answer):
            if "„Datenort“" in prompt:
                return BlockAnswer(findings=[finding()])
            return BlockAnswer(findings=[])

    sequential = extract(ByBlock(), PAGES, DocumentType.AVV)
    parallel = extract(ByBlock(), PAGES, DocumentType.AVV, workers=4)

    assert [(r.block, r.accepted) for r in parallel] == [(r.block, r.accepted) for r in sequential]


# ---------------------------------------------------------------- Zusammenführen


def test_merge_gives_one_state_per_field():
    eu = Evidence("data_location", "EU_ZUGESICHERT", "stored exclusively", 3)
    eu_again = Evidence("data_location", "EU_ZUGESICHERT", "only in the EU", 5)
    world = Evidence("operations_location", "WELTWEIT", "follow-the-sun", 4)
    near = Evidence("operations_location", "NUR_EU", "support within the EU", 6)

    merged = {
        item.field: item
        for item in merge(
            ["data_location", "operations_location", "transfer_basis"],
            [eu, world, eu_again, near],
            [DocumentType.AVV],
        )
    }

    assert merged["data_location"].state == FieldState.GEFUNDEN
    assert merged["data_location"].value == "EU_ZUGESICHERT"
    assert merged["data_location"].findings == (eu, eu_again)  # alle Fundstellen bleiben
    assert merged["operations_location"].state == FieldState.UNKLAR
    assert merged["operations_location"].value is None
    assert merged["transfer_basis"].state == FieldState.NICHT_GEFUNDEN


# ---------------------------------------------------------------- Urteil der Prüfpunkte

GDPR_H = FIELDS_BY_NAME["dsgvo_28_3_h"].elements  # informationen, pruefung, nur_berichte


@pytest.mark.parametrize(
    ("found", "verdict"),
    [
        ({"dsgvo_28_3_h.informationen", "dsgvo_28_3_h.pruefung"}, "VORHANDEN"),
        ({"dsgvo_28_3_h.informationen"}, "TEILWEISE"),  # Kernbestandteil fehlt
        (
            {"dsgvo_28_3_h.informationen", "dsgvo_28_3_h.pruefung", "dsgvo_28_3_h.nur_berichte"},
            "TEILWEISE",  # Einschränkung belegt
        ),
        ({"dsgvo_28_3_h.nur_berichte"}, "TEILWEISE"),  # eingeschränkt geregelt ist geregelt
        (set(), None),
    ],
)
def test_judge_applies_the_rule_of_the_standard(found, verdict):
    assert judge(GDPR_H, found) == verdict


def element(name, page):
    return Evidence(name, "BELEGT", "…", page)


def test_elements_from_different_pages_complete_each_other_instead_of_contradicting():
    """Muster 2 der Basismessung: Prüfrechte auf Seite 7, Inspektionen auf Seite 8."""
    found = [element("dsgvo_28_3_h.informationen", 7), element("dsgvo_28_3_h.pruefung", 8)]

    (merged,) = merge(["dsgvo_28_3_h"], found, [DocumentType.AVV])

    assert (merged.state, merged.value) == (FieldState.GEFUNDEN, "VORHANDEN")
    assert [item.page for item in merged.findings] == [7, 8]
    assert [item.state for item in merged.elements] == [
        ElementState.BELEGT,
        ElementState.BELEGT,
        ElementState.NICHT_BELEGT,
    ]


def test_element_not_asked_for_the_document_type_does_not_count_as_missing():
    found = [
        element("dora_30_2_a.unterauftrag_zulaessig", 3),
        element("dora_30_2_a.unterauftrag_bedingungen", 3),
    ]

    (avv,) = merge(["dora_30_2_a"], found, [DocumentType.AVV])
    (with_contract,) = merge(["dora_30_2_a"], found, [DocumentType.AVV, DocumentType.RAHMENVERTRAG])

    assert avv.value == "VORHANDEN"
    assert avv.elements[0].state == ElementState.NICHT_GEPRUEFT  # Leistungsbeschreibung
    assert with_contract.value == "TEILWEISE"
    assert with_contract.elements[0].state == ElementState.NICHT_BELEGT


def test_check_without_any_element_is_not_found():
    (merged,) = merge(["dsgvo_28_3_h"], [], [DocumentType.AVV])

    assert merged.state == FieldState.NICHT_GEFUNDEN and merged.value is None


def test_verdicts_of_runs_before_version_2_are_merged_like_facts():
    old = Evidence("dsgvo_28_3_h", "VORHANDEN", "…", 5)

    (merged,) = merge(["dsgvo_28_3_h"], [old], [DocumentType.AVV])

    assert (merged.state, merged.value, merged.elements) == (FieldState.GEFUNDEN, "VORHANDEN", ())
