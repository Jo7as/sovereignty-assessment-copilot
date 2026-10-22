import json

import pytest

from app.scan import scan
from app.scan.profile import (
    LeiRecord,
    build_profile,
    extract_imprint,
    find_entity,
    looks_like_imprint,
)
from app.scan.quick import profile_check, run_quick_check, suggestions_for
from app.scan.suggest import suggest
from app.scan.website import Page, parse_page

SOURCE = "https://www.bank.de/impressum/"
IMPRINT = (
    "Impressum | ING-DiBa AG | Theodor-Heuss-Allee 2 | 60486 Frankfurt am Main | Eingetragen im "
    "Handelsregister des Amtsgerichts Frankfurt am Main unter der Registernummer HRB 7727. | "
    "Umsatzsteuer-ID: DE 114103475 | Zuständige Aufsichtsbehörde: Bundesanstalt für "
    "Finanzdienstleistungsaufsicht (BaFin), Graurheindorfer Straße 108, 53117 Bonn"
)


# ---------------------------------------------------------------- Impressum


def test_imprint_facts_are_extracted_with_quotes():
    facts = extract_imprint(IMPRINT, SOURCE)

    assert facts.legal_name.value == "ING-DiBa AG"
    assert (facts.register.label, facts.register.court) == ("HRB 7727", "Frankfurt am Main")
    assert "HRB 7727" in facts.register.quote
    assert facts.vat_id.value == "DE114103475"
    assert "Bundesanstalt für Finanzdienstleistungsaufsicht" in facts.supervision.quote
    assert facts.register.source == SOURCE


def test_heading_in_front_of_the_name_is_removed():
    facts = extract_imprint("Impressum IONOS SE | Amtsgericht Montabaur / HRB 24498", SOURCE)

    assert facts.legal_name.value == "IONOS SE"
    assert facts.register.court == "Montabaur"


def test_partnership_and_court_after_number():
    facts = extract_imprint(
        "Personio SE & Co. KG | Sitz: München | Amtsgericht München; Registernummer: HRA 115934",
        SOURCE,
    )

    assert facts.legal_name.value == "Personio SE & Co. KG"
    assert (facts.register.label, facts.register.court) == ("HRA 115934", "München")


def test_without_bafin_there_is_no_supervision():
    assert extract_imprint("Beispiel GmbH | HRB 1 | Amtsgericht Köln", SOURCE).supervision is None


@pytest.mark.parametrize(
    ("text", "imprint"),
    [
        (IMPRINT, True),
        ("Angaben gemäß § 5 DDG | Beispiel GmbH", True),
        ("Impressum-Generator: Erstellen Sie Ihr Impressum in 2 Minuten", False),
    ],
)
def test_product_pages_are_not_mistaken_for_an_imprint(text, imprint):
    assert looks_like_imprint(text) is imprint


def test_imprint_links_are_ranked():
    html = """
    <a href="/tools/impressum-generator">Impressum-Generator</a>
    <a href="/rechtliches/impressum/">Rechtliches</a>
    <a href="/kontakt">Impressum</a>
    """

    info = parse_page(html, "https://www.bank.de/")

    assert info.imprint_urls == [
        "https://www.bank.de/kontakt",
        "https://www.bank.de/rechtliches/impressum/",
        "https://www.bank.de/tools/impressum-generator",
    ]


# ---------------------------------------------------------------- GLEIF


class FakeGleif:
    def __init__(self, records, parent=None):
        self.records, self.parent, self.asked = records, parent, []

    def by_register(self, register):
        self.asked.append(register)
        return [r for r in self.records if r.registered_as == register]

    def by_name(self, name):
        return [r for r in self.records if r.name == name]

    def ultimate_parent(self, lei):
        return self.parent


ING = LeiRecord("3KXUNHVVQFIJN6RHLO76", "ING-DIBA AG", "FRANKFURT AM MAIN", "DE", "HRB 7727")
OTHER = LeiRecord("529900AAAAAAAAAAAA00", "Nähr-Engel GmbH", "Goch", "DE", "HRB 7727")
PARENT = LeiRecord("549300NYKK9MWM7GGW15", "ING GROEP N.V.", "Amsterdam", "NL", None)


def test_entity_is_found_only_when_name_and_number_match():
    facts = extract_imprint(IMPRINT, SOURCE)

    entity, note = find_entity(facts, FakeGleif([OTHER, ING]))

    assert entity == ING
    assert "Name und Registernummer" in note


def test_same_number_at_another_court_is_not_taken():
    facts = extract_imprint(IMPRINT, SOURCE)

    entity, note = find_entity(facts, FakeGleif([OTHER]))

    assert entity is None
    assert "keinen Eintrag" in note


def test_two_matching_entries_are_left_open():
    facts = extract_imprint(IMPRINT, SOURCE)
    twin = LeiRecord("529900BBBBBBBBBBBB00", "ING-DiBa AG", "Frankfurt", "DE", "HRB 7727")

    entity, note = find_entity(facts, FakeGleif([ING, twin]))

    assert entity is None
    assert "mehrere" in note


def test_profile_contains_the_ultimate_parent():
    profile = build_profile(IMPRINT, SOURCE, FakeGleif([ING], parent=PARENT))

    assert (profile.entity.lei, profile.parent.name, profile.parent.country) == (
        ING.lei,
        "ING GROEP N.V.",
        "NL",
    )
    assert profile.entity.source.endswith(ING.lei)


def test_gleif_outage_keeps_the_imprint_facts():
    class Broken(FakeGleif):
        def by_register(self, register):
            raise TimeoutError

    profile = build_profile(IMPRINT, SOURCE, Broken([]))

    assert profile.imprint.register.label == "HRB 7727"
    assert profile.notes == ["GLEIF ließ sich nicht abfragen."]


# ---------------------------------------------------------------- Vorschläge der KI

SECTORS = {"KREDITINSTITUT": "Kreditinstitut", "BERATUNG": "Beratung", "ANDERER": "Anderer Sektor"}
HOME = (
    "Willkommen bei der Musterbank | Wir sind die Direktbank für 9.500.000 Kunden | "
    "Rund 6.000 Mitarbeitende arbeiten für Sie"
)


class FakeSuggester:
    def __init__(self, answer):
        self.answer, self.prompts = answer, []

    def ask(self, prompt):
        self.prompts.append(prompt)
        return self.answer


def test_suggestions_with_verbatim_quotes_are_kept():
    answer = json.dumps(
        {
            "sector": "KREDITINSTITUT",
            "sector_quote": "Wir sind die Direktbank für 9.500.000 Kunden",
            "employees": 6000,
            "employees_quote": "Rund 6.000 Mitarbeitende arbeiten für Sie",
        }
    )

    result = suggest(HOME, SECTORS, FakeSuggester(answer))

    assert (result.sector.value, result.employees.value) == ("KREDITINSTITUT", 6000)
    assert result.employees.label == "6.000"


def test_invented_quote_is_rejected():
    answer = json.dumps(
        {
            "sector": "KREDITINSTITUT",
            "sector_quote": "Wir sind eine Bank mit Vollbanklizenz",
            "employees": 6000,
            "employees_quote": "Wir beschäftigen 6.000 Menschen",
        }
    )

    result = suggest(HOME, SECTORS, FakeSuggester(answer))

    assert (result.sector, result.employees) == (None, None)


def test_number_must_appear_in_the_quote():
    """Im Zitat steht 9.500.000 als Kundenzahl, 6.000 Beschäftigte belegt es nicht."""
    answer = json.dumps(
        {
            "sector": None,
            "employees": 6000,
            "employees_quote": "Wir sind die Direktbank für 9.500.000 Kunden",
        }
    )

    assert suggest(HOME, SECTORS, FakeSuggester(answer)).employees is None


@pytest.mark.parametrize("sector", ["VERSICHERUNG", "kreditinstitut", 3, None])
def test_sector_outside_the_list_is_rejected(sector):
    answer = json.dumps(
        {"sector": sector, "sector_quote": "Wir sind die Direktbank für 9.500.000 Kunden"}
    )

    assert suggest(HOME, SECTORS, FakeSuggester(answer)).sector is None


def test_broken_answer_and_outage_give_no_suggestions():
    class Down:
        def ask(self, prompt):
            raise TimeoutError

    assert suggest(HOME, SECTORS, FakeSuggester("kein JSON")).sector is None
    assert "nicht erreichbar" in suggest(HOME, SECTORS, Down()).note


def test_prompt_lists_only_allowed_sectors_and_is_limited():
    suggester = FakeSuggester("{}")

    suggest("x" * 50_000, SECTORS, suggester)

    assert "KREDITINSTITUT: Kreditinstitut" in suggester.prompts[0]
    assert len(suggester.prompts[0]) < 14_000


# ---------------------------------------------------------------- Schnellcheck


class Resolver:
    def lookup(self, name, record):
        return []


class Networks:
    def network(self, ip):
        return None


class SiteFetcher:
    """Startseite nur unter www erreichbar, Impressum über den Link der Startseite."""

    def __init__(self):
        self.urls = []

    def fetch(self, url, kinds=("html",)):
        self.urls.append(url)
        if url == "https://bank.de":
            raise TimeoutError
        if url.endswith("/impressum/"):
            return Page(url, 200, f"<p>{IMPRINT}</p>")
        return Page(
            url, 200, '<title>Bank</title><p>Startseite</p><a href="/impressum/">Impressum</a>'
        )


def test_homepage_falls_back_to_www():
    fetcher = SiteFetcher()

    result = scan("bank.de", Resolver(), Networks(), fetcher)

    assert fetcher.urls[:2] == ["https://bank.de", "https://www.bank.de"]
    assert result.title == "Bank"
    assert result.problems == []


def test_quick_check_combines_scan_profile_and_suggestions():
    steps = []
    answer = json.dumps(
        {
            "sector": "KREDITINSTITUT",
            "sector_quote": "Aufsichtsbehörde: Bundesanstalt für Finanzdienstleistungsaufsicht",
        }
    )

    check = run_quick_check(
        "bank.de", Resolver(), Networks(), SiteFetcher(), FakeGleif([ING], PARENT),
        FakeSuggester(answer), SECTORS, steps.append,
    )  # fmt: skip

    assert check.profile.imprint_url == "https://www.bank.de/impressum/"
    assert check.profile.parent.name == "ING GROEP N.V."
    assert check.suggestions.sector.value == "KREDITINSTITUT"
    assert check.suggestions.pending is False
    assert len(steps) == 5  # die Vorschläge sind kein Schritt mehr, sie folgen dem Ergebnis


def test_profile_check_leaves_suggestions_pending_until_asked():
    answer = json.dumps(
        {
            "sector": "KREDITINSTITUT",
            "sector_quote": "Aufsichtsbehörde: Bundesanstalt für Finanzdienstleistungsaufsicht",
        }
    )
    check = profile_check(
        "bank.de", Resolver(), Networks(), SiteFetcher(), FakeGleif([ING], PARENT)
    )

    assert check.suggestions.pending is True
    assert check.profile.imprint_url == "https://www.bank.de/impressum/"

    suggestions = suggestions_for(check, FakeSuggester(answer), SECTORS)

    assert suggestions.sector.value == "KREDITINSTITUT"  # Zitat stammt aus dem Impressum
    assert suggestions.pending is False


def test_quick_check_without_ai_key_says_so():
    check = run_quick_check(
        "bank.de", Resolver(), Networks(), SiteFetcher(), FakeGleif([]), None, SECTORS
    )

    assert "KI-Schlüssel" in check.suggestions.note


def test_suggester_asks_for_short_reasoning(monkeypatch):
    import app.matching.ai as ai
    from app.scan.suggest import OpenRouterSuggester

    sent = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "{}"}}]}

    def fake_post(url, headers, json, timeout):
        sent.update(body=json)
        return Response()

    monkeypatch.setattr(ai.httpx2, "post", fake_post)

    OpenRouterSuggester("geheim", "deepseek/deepseek-v4.1-flash").ask("Text")

    assert sent["body"]["reasoning"] == {"effort": "low"}
    assert sent["body"]["provider"] == {"data_collection": "deny"}


def test_suggester_gives_up_after_its_deadline(monkeypatch):
    import time

    import app.scan.suggest as suggest_module

    def slow_chat(*args, **kwargs):
        time.sleep(2)
        return "{}"

    monkeypatch.setattr(suggest_module, "chat", slow_chat)
    monkeypatch.setattr(suggest_module, "DEADLINE", 0.1)
    started = time.monotonic()

    result = suggest_module.suggest(
        "Ein Text über eine Bank.", SECTORS, suggest_module.OpenRouterSuggester("k", "m")
    )

    assert time.monotonic() - started < 1
    assert "zu lange" in result.note
