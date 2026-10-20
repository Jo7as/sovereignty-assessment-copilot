"""Website eines Unternehmens laden und auswerten: eingebundene Dienste und Impressum.

Gezählt wird nur, was die Seite tatsächlich lädt (Skripte, Iframes, Stylesheets,
Vorverbindungen, Bilder und Adressen in eingebetteten Skripten). Ein Link zu LinkedIn im
Fußbereich ist kein eingebundener Dienst.
"""

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import urljoin, urlsplit

MAX_BYTES = 3_000_000  # größere Seiten werden abgeschnitten
URL_IN_SCRIPT = re.compile(
    r"(?:https?:)?//([a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+)"
    r"(/[^\s'\"<>?#]*)?",
    re.I,
)
IMPRINT_WORDS = ("impressum", "imprint", "legal notice", "legal-notice", "anbieterkennzeichnung")
LOADING_RELS = {"stylesheet", "preconnect", "dns-prefetch", "preload", "modulepreload", "icon"}


@dataclass(frozen=True)
class Page:
    url: str  # Adresse nach allen Weiterleitungen
    status: int
    html: str


class PageFetcher(Protocol):
    def fetch(self, url: str) -> Page:
        """Lädt eine Seite. Wirft BlockedAddress, wenn sie auf eine interne Adresse zeigt."""
        ...


class BlockedAddress(Exception):
    pass


@dataclass
class PageInfo:
    # Host und Pfad aller Ressourcen, die die Seite tatsächlich lädt. Der Pfad unterscheidet
    # Dienste vom selben Host, etwa /gtm.js (Tag Manager) und /gtag/js (Analytics).
    resources: set[tuple[str, str]] = field(default_factory=set)
    # Adressen, die nur in eingebetteten Skripten vorkommen. Dort stehen oft auch bloße Links
    # als Daten, sie zählen deshalb nur, wenn sie zu einem bekannten Dienst gehören.
    script_resources: set[tuple[str, str]] = field(default_factory=set)

    @property
    def hosts(self) -> set[str]:
        return {host for host, _ in self.resources}

    @property
    def script_hosts(self) -> set[str]:
        return {host for host, _ in self.script_resources}

    imprint_url: str | None = None
    title: str = ""


class _Parser(HTMLParser):
    def __init__(self, base: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base
        self.info = PageInfo()
        self._in_script = False
        self._in_title = False
        self._link: tuple[str, list[str]] | None = None  # href und gesammelter Text eines Links

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        if tag in {"script", "iframe", "img", "embed", "source"} and values.get("src"):
            self._add(values["src"])
        if tag == "link" and LOADING_RELS & set(values.get("rel", "").lower().split()):
            self._add(values.get("href", ""))
        if tag == "script":
            self._in_script = not values.get("src")
        if tag == "title":
            self._in_title = True
        if tag == "a":
            self._link = (values.get("href", ""), [])

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._in_script = False
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._link:
            href, texts = self._link
            label = " ".join(texts).lower()
            if self.info.imprint_url is None and _looks_like_imprint(href, label):
                self.info.imprint_url = urljoin(self.base, href)
            self._link = None

    def handle_data(self, data: str) -> None:
        if self._in_script:
            for host, path in URL_IN_SCRIPT.findall(data):
                self.info.script_resources.add((host.lower(), path or "/"))
        if self._in_title:
            self.info.title += data.strip()
        if self._link:
            self._link[1].append(data.strip())

    def _add(self, url: str) -> None:
        parts = urlsplit(urljoin(self.base, url))
        if parts.hostname:
            self.info.resources.add((parts.hostname.lower(), parts.path or "/"))


def _looks_like_imprint(href: str, label: str) -> bool:
    if href.lower().startswith(("javascript:", "mailto:", "#")):
        return False
    return any(word in label or word in href.lower() for word in IMPRINT_WORDS)


def parse_page(html: str, base_url: str) -> PageInfo:
    parser = _Parser(base_url)
    parser.feed(html)
    parser.close()
    return parser.info


def is_third_party(host: str, domain: str) -> bool:
    """Gehört der Host nicht zur Domain selbst? „cdn.bank.de“ ist eigen, „cdn.example.net“ fremd."""
    return not (host == domain or host.endswith(f".{domain}"))
