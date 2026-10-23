from app.scan import Record, scan
from app.scan.signatures import Signature, Tool, identify, load_signatures
from app.scan.website import Page


class FakeResolver:
    def lookup(self, name, record):
        return []


class FakeNetworks:
    def network(self, ip):
        return None


class FakeFetcher:
    def __init__(self, page):
        self.page = page

    def fetch(self, url, kinds=("html",)):
        return self.page


def test_real_list_names_hotjar_with_german_category():
    tools = identify({("static.hotjar.com", "/c/hotjar-123.js")}, load_signatures())

    assert tools["static.hotjar.com"] == Tool("Hotjar", "https://www.hotjar.com", "Webanalyse")


def test_version_suffix_of_a_pattern_is_ignored():
    signature = Signature.build("Beispiel", [r"cdn\.beispiel\.io/v(\d+)/\;version:\1"], None, [])

    assert signature.matches("https://cdn.beispiel.io/v2/app.js")


def test_broken_pattern_is_skipped_instead_of_crashing():
    signature = Signature.build("Kaputt", ["(?<name>x)", r"ok\.example/"], None, ["Analytics"])

    assert signature.matches("https://ok.example/a.js")
    assert not signature.matches("https://x.example/")


def test_host_without_signature_stays_unknown():
    assert identify({("cdn.tool.example", "/t.js")}, load_signatures()) == {}


def test_raw_findings_get_a_name_but_no_service():
    html = """<html><head>
    <script src="https://static.hotjar.com/c/hotjar-123.js?sv=6"></script>
    <script src="https://cdn.tool.example/t.js"></script>
    <script src="https://www.googletagmanager.com/gtm.js?id=GTM-1"></script>
    </head></html>"""
    page = Page("https://www.musterbank.de/", 200, html)

    result = scan("musterbank.de", FakeResolver(), FakeNetworks(), FakeFetcher(page))

    raw = {f.value: f for f in result.findings if f.record is Record.WEB and f.service is None}
    assert raw["static.hotjar.com"].tool.name == "Hotjar"
    assert raw["cdn.tool.example"].tool is None
    assert "google-tag-manager" in result.services  # bewertete Dienste bleiben unberührt
    assert all(f.tool is None for f in result.findings if f.service)
