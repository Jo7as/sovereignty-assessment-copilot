"""Zuordnung von Freitext aus dem IT-Bestand zu Diensten der Datenbank."""

from app.matching import CatalogService, Method, match_entry, normalize
from app.matching.ai import AiChoice

CATALOG = [
    CatalogService(
        "microsoft-365",
        "Microsoft 365",
        ("O365", "Office 365", "Teams"),
        "Microsoft Ireland Operations Limited",
    ),
    CatalogService(
        "microsoft-azure", "Microsoft Azure", ("Azure",), "Microsoft Ireland Operations Limited"
    ),
    CatalogService(
        "google-workspace", "Google Workspace", ("G Suite", "Gmail"), "Google Cloud EMEA Limited"
    ),
    CatalogService("avaloq", "Avaloq", (), "Avaloq Group AG"),
    CatalogService("google-cloud", "Google Cloud", ("GCP",), "Google Cloud EMEA Limited"),
    CatalogService("ionos-cloud", "IONOS Cloud", ("IONOS",), "IONOS SE"),
    CatalogService("sap-s4hana-cloud", "SAP S/4HANA Cloud", ("S/4HANA",), "SAP SE"),
    CatalogService("sap-concur", "SAP Concur", ("Concur Expense",), "Concur Technologies, Inc."),
    CatalogService("vodafone-wan", "Vodafone Unternehmensnetz (WAN)", (), "Vodafone Group Plc"),
]


class FakeClassifier:
    def __init__(self, slug, confidence=0.8):
        self.slug, self.confidence, self.calls = slug, confidence, 0

    def choose(self, entry, catalog):
        self.calls += 1
        return AiChoice(self.slug, self.confidence, "Begründung der KI")


def test_normalize_removes_case_punctuation_and_accents():
    assert normalize("  SAP S/4-HANA (Cloud) für Ümläute ") == "sap s 4 hana cloud fur umlaute"


def test_exact_alias_is_matched_by_text():
    result = match_entry({"service": "O365"}, CATALOG)

    assert (result.slug, result.method) == ("microsoft-365", Method.TEXT)
    assert not result.needs_review


def test_alias_inside_a_longer_entry_is_matched():
    result = match_entry({"service": "Online-Banking Plattform (auf Azure)"}, CATALOG)

    assert result.slug == "microsoft-azure"


def test_typo_is_tolerated():
    result = match_entry({"service": "Ofice 365 Lizenzen Vertrieb"}, CATALOG)

    assert result.slug == "microsoft-365"


def test_word_parts_do_not_match_across_words():
    """„G Suite“ darf nicht in „Banking Suite“ gefunden werden."""
    result = match_entry({"service": "Avaloq Banking Suite"}, CATALOG)

    assert result.slug == "avaloq"


def test_generic_words_are_kept_so_names_stay_distinct():
    """„Google Cloud“ darf nicht zu „Google“ schrumpfen und jeden Google-Eintrag mitnehmen."""
    result = match_entry({"service": "Google Workspace (Marketing)"}, CATALOG)

    assert result.slug == "google-workspace"


def test_generic_word_alone_is_not_a_brand():
    classifier = FakeClassifier(None)

    match_entry({"service": "Cloud Backup"}, CATALOG, classifier)

    assert classifier.calls == 1


def test_brand_name_unique_to_one_service_is_enough():
    result = match_entry({"service": "Concur Reisekosten"}, CATALOG)

    assert (result.slug, result.method) == ("sap-concur", Method.TEXT)


def test_legal_form_in_a_company_name_does_not_hide_a_brand():
    """„SAS“ ist bei Mistral AI SAS eine Rechtsform, bei SAS Viya eine Marke."""
    catalog = [
        CatalogService("sas", "SAS Viya", (), "SAS Institute Inc."),
        CatalogService("mistral-vibe", "Mistral Vibe", (), "Mistral AI SAS"),
        CatalogService("yousign", "Yousign", (), "Yousign SAS"),
    ]

    result = match_entry({"service": "SAS Risk"}, catalog)

    assert result.slug == "sas"


def test_brand_name_shared_by_several_services_is_not_enough():
    classifier = FakeClassifier(None)

    result = match_entry({"service": "Microsoft Defender"}, CATALOG, classifier)

    assert classifier.calls == 1
    assert result.method is Method.AI


def test_ai_is_asked_only_when_text_comparison_fails():
    classifier = FakeClassifier("microsoft-365")

    match_entry({"service": "O365"}, CATALOG, classifier)

    assert classifier.calls == 0


def test_ai_choice_is_marked_for_review():
    result = match_entry({"service": "Outlook"}, CATALOG, FakeClassifier("microsoft-365", 0.9))

    assert (result.slug, result.method, result.needs_review) == ("microsoft-365", Method.AI, True)
    assert result.reason == "Begründung der KI"


def test_ai_answer_outside_the_catalog_is_discarded():
    result = match_entry({"service": "Outlook"}, CATALOG, FakeClassifier("erfunden"))

    assert result.slug is None
    assert result.needs_review


def test_without_ai_an_unknown_entry_stays_unmatched_for_review():
    result = match_entry({"service": "EBICS-Server"}, CATALOG)

    assert (result.slug, result.method, result.needs_review) == (None, Method.NONE, True)


def test_provider_column_helps_when_service_name_is_generic():
    result = match_entry({"service": "WAN", "provider": "Vodafone"}, CATALOG)

    assert result.slug == "vodafone-wan"


def test_ai_answer_is_parsed_even_with_text_around_it():
    from app.matching.ai import parse_answer

    choice = parse_answer('Gern: {"slug": "okta", "confidence": 0.7, "reason": "Anmeldedienst"}')

    assert choice == AiChoice("okta", 0.7, "Anmeldedienst")


def test_broken_ai_answer_becomes_no_choice():
    from app.matching.ai import parse_answer

    assert parse_answer("Ich weiß es nicht").slug is None
    assert parse_answer('{"slug": "okta", "confidence": "hoch"}').confidence == 0
    assert parse_answer('{"slug": null, "confidence": 3}').confidence == 1


def test_openrouter_classifier_sends_entry_and_catalog(monkeypatch):
    from app.matching import ai

    sent = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            content = (
                '{"slug": "microsoft-365", "confidence": 0.9, "reason": "Outlook gehört zu M365"}'
            )
            return {"choices": [{"message": {"content": content}}]}

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, headers=headers, body=json)
        return Response()

    monkeypatch.setattr(ai.httpx2, "post", fake_post)
    classifier = ai.OpenRouterClassifier("geheim", "anthropic/claude-sonnet-5.5")

    choice = classifier.choose({"service": "Outlook", "purpose": "E-Mail"}, CATALOG)

    prompt = sent["body"]["messages"][0]["content"]
    assert choice.slug == "microsoft-365"
    assert sent["headers"]["Authorization"] == "Bearer geheim"
    assert sent["body"]["model"] == "anthropic/claude-sonnet-5.5"
    assert sent["body"]["provider"] == {"data_collection": "deny"}
    assert "Outlook" in prompt and "microsoft-365 | Microsoft 365" in prompt
