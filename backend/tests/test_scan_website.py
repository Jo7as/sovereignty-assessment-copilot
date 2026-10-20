import datetime

import httpx2
import pytest

import app.scan as scan_module
from app.scan import DetectionRules, Record, Strength, WebRule, load_rules, scan
from app.scan.fetch import SafeFetcher, check_url
from app.scan.website import BlockedAddress, Page, is_third_party, parse_page


class FakeResolver:
    def __init__(self, records):
        self.records = records

    def lookup(self, name, record):
        return self.records.get((name, record), [])


class FakeNetworks:
    def __init__(self, table):
        self.table = table

    def network(self, ip):
        return self.table.get(ip)


class FakeFetcher:
    def __init__(self, page=None, error=None):
        self.page, self.error = page, error

    def fetch(self, url):
        if self.error:
            raise self.error
        return self.page


HTML = """
<html><head><title>Musterbank AG</title>
<script src="https://www.googletagmanager.com/gtm.js?id=GTM-1"></script>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter">
<link rel="preconnect" href="https://cdn.cookie-anbieter.example">
<link rel="canonical" href="https://www.andere-seite.example/">
<link rel="alternate" hreflang="en" href="https://en.uebersetzung.example/">
<script>window.data = {"social": "https://www.instagram.com/musterbank", "tag": "https://connect.facebook.net/en_US/fbevents.js"};</script>
<script type="application/json">{"x": "https://apps.apple.com/app"}</script>
</head><body>
<img src="/logo.png"><img src="https://pixel.tracker.example/p.gif">
<iframe src="https://www.youtube-nocookie.com/embed/abc"></iframe>
<a href="https://www.linkedin.com/company/musterbank">LinkedIn</a>
<a href="javascript:openImprint()">Impressum</a>
<a href="/rechtliches/impressum/">Impressum</a>
</body></html>
"""


# ---------------------------------------------------------------- Seite auswerten


def test_only_loaded_resources_count_as_hosts():
    info = parse_page(HTML, "https://www.musterbank.de/")

    assert info.hosts == {
        "www.googletagmanager.com",
        "fonts.googleapis.com",
        "cdn.cookie-anbieter.example",
        "www.musterbank.de",
        "pixel.tracker.example",
        "www.youtube-nocookie.com",
    }


def test_hosts_in_inline_scripts_are_kept_apart():
    info = parse_page(HTML, "https://www.musterbank.de/")

    assert {"www.instagram.com", "connect.facebook.net"} <= info.script_hosts
    assert "www.linkedin.com" not in info.hosts | info.script_hosts


def test_imprint_link_is_found_and_javascript_links_are_skipped():
    info = parse_page(HTML, "https://www.musterbank.de/")

    assert info.imprint_url == "https://www.musterbank.de/rechtliches/impressum/"
    assert info.title == "Musterbank AG"


@pytest.mark.parametrize(
    ("host", "third_party"),
    [("bank.de", False), ("cdn.bank.de", False), ("cdn.example.net", True), ("evilbank.de", True)],
)
def test_third_party_hosts(host, third_party):
    assert is_third_party(host, "bank.de") is third_party


# ---------------------------------------------------------------- Sicher laden

PUBLIC = FakeResolver(
    {
        ("www.bank.de", "A"): ["52.1.2.3"],
        ("intern.bank.de", "A"): ["10.0.0.7"],
        ("halb.bank.de", "A"): ["52.1.2.3", "192.168.0.2"],
        ("meta.bank.de", "A"): ["169.254.169.254"],
    }
)


@pytest.mark.parametrize(
    "url",
    [
        "ftp://www.bank.de/",
        "https://www.bank.de:8443/",
        "https://52.1.2.3/",
        "http://10.0.0.1/",
        "http://[::1]/",
        "https://intern.bank.de/",
        "https://halb.bank.de/",
        "https://meta.bank.de/latest/meta-data",
        "https://unbekannt.bank.de/",
    ],
)
def test_unsafe_addresses_are_blocked(url):
    with pytest.raises(BlockedAddress):
        check_url(url, PUBLIC)


def test_public_address_is_allowed():
    check_url("https://www.bank.de/start", PUBLIC)


def fetcher_with(handler) -> SafeFetcher:
    fetcher = SafeFetcher(PUBLIC)
    fetcher._client = httpx2.Client(transport=httpx2.MockTransport(handler), follow_redirects=False)
    return fetcher


def test_redirect_to_an_internal_address_is_blocked():
    def handler(request):
        if request.url.host == "www.bank.de":
            return httpx2.Response(302, headers={"location": "https://intern.bank.de/admin"})
        return httpx2.Response(200, html="<p>geheim</p>")

    with pytest.raises(BlockedAddress):
        fetcher_with(handler).fetch("https://www.bank.de/")


def test_too_many_redirects_are_stopped():
    calls = []

    def handler(request):
        calls.append(request.url)
        return httpx2.Response(302, headers={"location": "https://www.bank.de/weiter"})

    with pytest.raises(BlockedAddress, match="Weiterleitungen"):
        fetcher_with(handler).fetch("https://www.bank.de/")
    assert len(calls) == 5  # die erste Anfrage und vier Weiterleitungen


def test_page_is_loaded_and_large_pages_are_cut():
    def handler(request):
        return httpx2.Response(200, headers={"content-type": "text/html"}, content=b"x" * 3_500_000)

    page = fetcher_with(handler).fetch("https://www.bank.de/")

    assert page.status == 200
    assert len(page.html) == 3_000_000


def test_non_html_content_is_ignored():
    def handler(request):
        return httpx2.Response(200, headers={"content-type": "application/pdf"}, content=b"%PDF")

    assert fetcher_with(handler).fetch("https://www.bank.de/").html == ""


# ---------------------------------------------------------------- Scan mit Website

EVIDENCE = {
    "source": "https://beispiel.example/doku",
    "quote": "Beleg",
    "retrieved": datetime.date(2026, 10, 21),
}


@pytest.fixture
def web_rules(monkeypatch):
    rules = load_rules()
    extended = DetectionRules(
        dns=rules.dns,
        asn=rules.asn,
        web=(
            WebRule(
                service="google-tag-manager",
                host="googletagmanager.com",
                strength=Strength.NUTZUNG,
                meaning="Tag Manager",
                **EVIDENCE,
            ),
            WebRule(
                service="meta-pixel",
                host="connect.facebook.net",
                strength=Strength.NUTZUNG,
                meaning="Pixel",
                **EVIDENCE,
            ),
        ),
    )
    monkeypatch.setattr(scan_module, "load_rules", lambda: extended)


def test_website_services_are_recognized(web_rules):
    page = Page("https://www.musterbank.de/", 200, HTML)

    result = scan("musterbank.de", FakeResolver({}), FakeNetworks({}), FakeFetcher(page))

    assert set(result.services) == {"google-tag-manager", "meta-pixel"}
    raw = {f.value for f in result.findings if f.record is Record.WEB and f.service is None}
    assert raw == {
        "fonts.googleapis.com",
        "cdn.cookie-anbieter.example",
        "pixel.tracker.example",
        "www.youtube-nocookie.com",
    }
    assert "www.instagram.com" not in raw  # nur in einem Skript erwähnt, kein bekannter Dienst
    assert result.imprint_url == "https://www.musterbank.de/rechtliches/impressum/"


def test_blocked_website_is_reported_and_the_rest_still_runs():
    resolver = FakeResolver({("bank.de", "MX"): ["bank-de.mail.protection.outlook.com"]})

    result = scan(
        "bank.de", resolver, FakeNetworks({}), FakeFetcher(Page("https://bank.de/", 503, ""))
    )

    assert "microsoft-365" in result.services
    assert any("Status 503" in problem for problem in result.problems)


def test_internal_website_is_reported():
    result = scan(
        "bank.de",
        FakeResolver({}),
        FakeNetworks({}),
        FakeFetcher(error=BlockedAddress("zeigt intern")),
    )

    assert result.problems == ["zeigt intern"]


def test_spf_senders_are_traced_to_their_network():
    resolver = FakeResolver({
        ("bank.de", "TXT"): ["v=spf1 include:_spf.versand.example -all"],
        ("_spf.versand.example", "TXT"): ["v=spf1 include:_netz.versand.example -all"],
        ("_netz.versand.example", "TXT"): ["v=spf1 ip4:10.0.0.0/8 ip4:54.240.0.0/18 -all"],
    })  # fmt: skip
    networks = FakeNetworks({"54.240.0.0": (14618, "AMAZON-AES - Amazon.com, Inc.")})

    result = scan("bank.de", resolver, networks)

    traced = [f for f in result.findings if f.record is Record.SPF_NET]
    assert [(f.value, f.service, f.strength) for f in traced] == [
        (
            "_spf.versand.example → AS14618 AMAZON-AES - Amazon.com, Inc.",
            "amazon-web-services",
            Strength.HINWEIS,
        )
    ]


def test_cname_chain_is_followed_and_limited():
    records = {
        ("www.bank.de", "CNAME"): ["a.cdn.example"],
        ("a.cdn.example", "CNAME"): ["b.cdn.example"],
    }
    loop = {("www.loop.de", "CNAME"): ["x.loop.de"], ("x.loop.de", "CNAME"): ["www.loop.de"]}

    chain = scan("bank.de", FakeResolver(records), FakeNetworks({}))
    looping = scan("loop.de", FakeResolver(loop), FakeNetworks({}))

    assert [f.value for f in chain.findings if f.record is Record.CNAME] == [
        "a.cdn.example",
        "b.cdn.example",
    ]
    assert len([f for f in looping.findings if f.record is Record.CNAME]) == 5


def test_steps_are_reported_in_order():
    steps = []

    scan(
        "bank.de",
        FakeResolver({}),
        FakeNetworks({}),
        FakeFetcher(Page("https://bank.de/", 200, "<p></p>")),
        on_step=steps.append,
    )

    assert steps == list(scan_module.STEPS)


GOOGLE_PAGE = """
<script async src="https://www.googletagmanager.com/gtag/js?id=G-123"></script>
<script>(function(w,d,s,l,i){j.src='https://www.googletagmanager.com/gtm.js?id='+i;})()</script>
<script src="https://www.google.com/recaptcha/api.js"></script>
<iframe src="https://www.google.com/maps/embed?pb=1"></iframe>
<iframe src="https://www.googletagmanager.com/ns.html?id=GTM-1"></iframe>
"""


def test_services_on_the_same_host_are_told_apart_by_path():
    page = Page("https://bank.de/", 200, GOOGLE_PAGE)

    result = scan("bank.de", FakeResolver({}), FakeNetworks({}), FakeFetcher(page))

    assert set(result.services) == {"google-analytics", "google-tag-manager", "recaptcha"}
    raw = [f.value for f in result.findings if f.record is Record.WEB and f.service is None]
    # Weitere Pfade auf Hosts mit erkanntem Dienst erscheinen nicht zusätzlich roh: ns.html
    # neben dem Tag Manager, aber dadurch auch Google Maps neben reCAPTCHA. Bewusst so, sonst
    # stünde bei fast jeder Website mit Tag Manager ein zusätzlicher roher Eintrag.
    assert raw == []


def test_unknown_path_on_an_unrecognized_host_stays_raw():
    page = Page(
        "https://bank.de/", 200, '<iframe src="https://www.google.com/maps/embed"></iframe>'
    )

    result = scan("bank.de", FakeResolver({}), FakeNetworks({}), FakeFetcher(page))

    assert [(f.value, f.service) for f in result.findings] == [("www.google.com", None)]
