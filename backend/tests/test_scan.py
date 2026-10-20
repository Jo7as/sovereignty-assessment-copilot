from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.scan import (
    InvalidDomain,
    Record,
    Strength,
    is_public_ip,
    load_rules,
    normalize_domain,
    scan,
    spf_includes,
)
from app.scan.api import get_fetcher, get_networks, get_resolver
from app.scan.website import Page
from app.seed import load_seed

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class FakeResolver:
    def __init__(self, records: dict[tuple[str, str], list[str]], broken: set[str] = frozenset()):
        self.records = records
        self.broken = broken

    def lookup(self, name: str, record: str) -> list[str]:
        if record in self.broken:
            raise TimeoutError("keine Antwort")
        return self.records.get((name, record), [])


class FakeNetworks:
    def __init__(self, table: dict[str, tuple[int, str]]):
        self.table = table
        self.asked: list[str] = []

    def network(self, ip: str):
        self.asked.append(ip)
        return self.table.get(ip)


BANK = {
    ("bank.de", "MX"): ["bank-de.mail.protection.outlook.com"],
    ("bank.de", "TXT"): [
        "v=spf1 include:spf.protection.outlook.com include:_spf.example.net -all",
        "MS=ms123",
    ],
    ("bank.de", "NS"): ["anna.ns.cloudflare.com", "bob.ns.cloudflare.com"],
    ("bank.de", "A"): ["52.1.2.3"],
    ("www.bank.de", "A"): ["52.1.2.3", "10.0.0.5"],
}
AWS = {"52.1.2.3": (16509, "AMAZON-02 - Amazon.com, Inc.")}


# ---------------------------------------------------------------- Domain


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("bank.de", "bank.de"),
        ("  https://www.Bank.DE/kontakt?x=1  ", "bank.de"),
        ("bank.de:443", "bank.de"),
        ("info@bank.de", "bank.de"),
        ("müller.de", "xn--mller-kva.de"),
        ("bank.de.", "bank.de"),
    ],
)
def test_domain_is_normalized(raw, expected):
    assert normalize_domain(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "localhost",
        "intranet",
        "server.local",
        "db.internal",
        "127.0.0.1",
        "[::1]",
        "10.0.0.1",
        "bank..de",
        "-bank.de",
        "bank.123",
        "a_b.de",
    ],
)
def test_internal_or_invalid_domains_are_rejected(raw):
    with pytest.raises(InvalidDomain):
        normalize_domain(raw)


@pytest.mark.parametrize(
    ("ip", "public"),
    [
        ("52.1.2.3", True),
        ("10.0.0.5", False),
        ("192.168.1.1", False),
        ("127.0.0.1", False),
        ("169.254.169.254", False),
        ("::1", False),
        ("kein-ip", False),
    ],
)
def test_only_public_addresses_count(ip, public):
    assert is_public_ip(ip) is public


def test_spf_includes_are_extracted_with_qualifiers():
    assert spf_includes(
        "v=spf1 include:_spf.google.com ~include:Spf.Protection.Outlook.com. ip4:1.2.3.4 -all"
    ) == [
        "_spf.google.com",
        "spf.protection.outlook.com",
    ]


# ---------------------------------------------------------------- Scan


def test_known_signatures_are_matched_with_evidence():
    result = scan("bank.de", FakeResolver(BANK), FakeNetworks(AWS))

    assert set(result.services) == {"microsoft-365", "cloudflare", "amazon-web-services"}
    microsoft = result.services["microsoft-365"]
    assert {finding.record for finding in microsoft} == {Record.MX, Record.SPF}
    assert all(finding.evidence and finding.evidence.quote for finding in microsoft)


def test_website_network_is_only_a_hint():
    result = scan("bank.de", FakeResolver(BANK), FakeNetworks(AWS))

    assert [f.strength for f in result.services["amazon-web-services"]] == [Strength.HINWEIS]


def test_unknown_findings_are_kept_raw_instead_of_guessed():
    result = scan("bank.de", FakeResolver(BANK), FakeNetworks(AWS))

    raw = [(f.record, f.value) for f in result.findings if f.service is None]
    assert raw == [(Record.SPF, "_spf.example.net")]


def test_verification_records_are_not_counted_as_spf():
    result = scan("bank.de", FakeResolver(BANK), FakeNetworks(AWS))

    assert not any("ms123" in f.value.lower() for f in result.findings)


def test_private_addresses_are_never_sent_to_the_network_lookup():
    networks = FakeNetworks(AWS)

    result = scan("bank.de", FakeResolver(BANK), networks)

    assert networks.asked == ["52.1.2.3"]
    assert any("10.0.0.5" in problem for problem in result.problems)


def test_same_network_is_reported_once():
    records = {**BANK, ("www.bank.de", "A"): ["52.1.2.4"]}
    table = {**AWS, "52.1.2.4": AWS["52.1.2.3"]}

    result = scan("bank.de", FakeResolver(records), FakeNetworks(table))

    assert len([f for f in result.findings if f.record is Record.ASN]) == 1


def test_lookalike_hosts_do_not_match():
    """„outlook.com.fake.example“ endet nicht auf dem Merkmal und darf nicht zählen."""
    records = {("x.de", "MX"): ["mail.protection.outlook.com.fake.example", "notsmtp.google.com"]}

    result = scan("x.de", FakeResolver(records), FakeNetworks({}))

    assert result.services == {}


def test_failing_lookup_is_reported_and_the_scan_continues():
    result = scan("bank.de", FakeResolver(BANK, broken={"MX"}), FakeNetworks(AWS))

    assert "cloudflare" in result.services
    assert any("MX" in problem for problem in result.problems)


# ---------------------------------------------------------------- Merkmale


def test_every_signature_points_to_a_service_in_the_database():
    services = {path.stem for path in (DATA_DIR / "services").glob("*.yaml")}
    rules = load_rules()

    assert {rule.service for rule in [*rules.dns, *rules.asn, *rules.web]} <= services


def test_every_signature_has_a_quote():
    rules = load_rules()
    every_rule = [*rules.dns, *rules.asn, *rules.web]

    assert all(rule.quote and rule.source.startswith("https://") for rule in every_rule)


# ---------------------------------------------------------------- API


client = TestClient(app)


@pytest.fixture
def api(session):
    load_seed(session, DATA_DIR)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_resolver] = lambda: FakeResolver(BANK)
    app.dependency_overrides[get_networks] = lambda: FakeNetworks(AWS)
    app.dependency_overrides[get_fetcher] = lambda: type(
        "F", (), {"fetch": lambda self, url: Page(url, 200, "<title>Bank</title>")}
    )()
    yield
    app.dependency_overrides.clear()


def test_scan_endpoint_lists_services_with_evidence(api):
    body = client.post("/scan", json={"domain": "https://www.bank.de"}).json()

    assert body["domain"] == "bank.de"
    assert [s["service"] for s in body["services"]] == [
        "cloudflare",
        "microsoft-365",
        "amazon-web-services",
    ]
    assert body["services"][0]["strength"] == "NUTZUNG"
    assert body["services"][2]["strength"] == "HINWEIS"
    assert body["services"][1]["findings"][0]["evidence"]["retrieved"] == "2026-10-21"
    assert [f["value"] for f in body["other_findings"]] == ["_spf.example.net"]
    assert body["other_findings"][0]["category"] == "EMAIL"
    assert {s["group"] for s in body["services"]} == {"UNTERNEHMEN"}
    assert body["title"] == "Bank"
    assert len(body["steps"]) == 4


def test_scan_endpoint_rejects_internal_domains(api):
    response = client.post("/scan", json={"domain": "localhost"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_DOMAIN"


@pytest.mark.parametrize("raw", ["127.0.0.1", "[::1]", "https://10.0.0.1/admin"])
def test_ip_addresses_get_a_clear_message(raw):
    with pytest.raises(InvalidDomain, match="keine IP-Adresse"):
        normalize_domain(raw)


def test_include_outside_an_spf_record_does_not_count():
    records = {("x.de", "TXT"): ["verification-token include:spf.protection.outlook.com"]}

    result = scan("x.de", FakeResolver(records), FakeNetworks({}))

    assert result.findings == []
