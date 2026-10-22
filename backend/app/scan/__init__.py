"""Außenscan: Was eine Domain von außen über die genutzten Dienste verrät.

Geprüft werden Mailserver (MX), SPF-Einträge, Nameserver (NS) und der Netzbetreiber der
Website (über RIPEstat). Die Erkennungsmerkmale stehen mit Quelle in data/detection.yaml.
Funde ohne passenden Dienst in der Datenbank werden roh gemeldet, nie geraten.

Erläutert in docs/bewertungslogik.md, Abschnitt „Außenscan“.
"""

import datetime
import ipaddress
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import auto
from functools import cache
from typing import TYPE_CHECKING, Protocol

import yaml
from pydantic import BaseModel, ConfigDict

from app.config import PROJECT_ROOT
from app.models.enums import Values

if TYPE_CHECKING:
    from app.scan.website import PageFetcher

DETECTION_FILE = PROJECT_ROOT / "data" / "detection.yaml"


class Strength(Values):
    NUTZUNG = auto()  # nachweislich genutzt, etwa weil die E-Mails darüber laufen
    HINWEIS = auto()  # deutet auf den Dienst hin, belegt die Nutzung aber nicht


class Record(Values):
    MX = auto()
    SPF = auto()  # include-Angabe im SPF-Eintrag
    SPF_NET = auto()  # Netzbetreiber eines Absenders aus dem SPF-Eintrag
    NS = auto()
    CAA = auto()  # Zertifizierungsstelle, die Zertifikate für die Domain ausstellen darf
    CNAME = auto()  # Weiterleitung von www.<domain> auf einen anderen Namen
    ASN = auto()  # Netzbetreiber der Website
    WEB = auto()  # von der Website eingebundene Ressource
    TECH = auto()  # Technik der Website selbst, etwa WordPress und seine Plugins


class Category(Values):
    EMAIL = auto()
    DOMAIN = auto()
    HOSTING = auto()
    WEBSITE = auto()


CATEGORY = {
    Record.MX: Category.EMAIL,
    Record.SPF: Category.EMAIL,
    Record.SPF_NET: Category.EMAIL,
    Record.NS: Category.DOMAIN,
    Record.CAA: Category.DOMAIN,
    Record.CNAME: Category.HOSTING,
    Record.ASN: Category.HOSTING,
    Record.WEB: Category.WEBSITE,
    Record.TECH: Category.WEBSITE,
}


class Match(Values):
    SUFFIX = auto()  # Hostname endet auf den Wert
    EXACT = auto()  # Hostname ist genau der Wert
    INCLUDE = auto()  # SPF-Eintrag enthält include:<Wert>


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Evidence(Model):
    source: str
    quote: str
    retrieved: datetime.date


class DnsRule(Evidence):
    service: str
    record: Record
    match: Match
    value: str
    strength: Strength
    meaning: str

    def applies_to(self, record: Record, value: str) -> bool:
        if record is not self.record:
            return False
        if self.match is Match.SUFFIX:
            return value.endswith(self.value)
        return value == self.value  # EXACT und INCLUDE vergleichen den ganzen Wert


class AsnRule(Evidence):
    asn: int
    service: str
    meaning: str


class WebRule(Evidence):
    """Ein Host, den eine Website einbindet, etwa „www.googletagmanager.com“."""

    service: str
    host: str  # zählt für den Host selbst und alle Unterdomains
    path: str = "/"  # Anfang des Pfads, etwa „/gtm.js“
    strength: Strength
    meaning: str

    def applies_to(self, host: str, path: str = "/") -> bool:
        on_host = host == self.host or host.endswith(f".{self.host}")
        return on_host and path.startswith(self.path)


class DetectionRules(Model):
    dns: tuple[DnsRule, ...]
    asn: tuple[AsnRule, ...]
    web: tuple[WebRule, ...] = ()


@cache
def load_rules() -> DetectionRules:
    return DetectionRules.model_validate(yaml.safe_load(DETECTION_FILE.read_text("utf-8")))


# ---------------------------------------------------------------- Domain prüfen


class InvalidDomain(ValueError):
    pass


LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")
# Namen, die nie öffentlich sind. Sonst ließen sich über das Tool interne Systeme abfragen.
RESERVED_TLDS = frozenset(
    {"localhost", "local", "internal", "intranet", "lan", "home", "corp", "test", "invalid",
     "example", "onion", "arpa", "localdomain"}
)  # fmt: skip


def normalize_domain(raw: str) -> str:
    """Macht aus einer Eingabe wie „https://www.Beispiel.de/kontakt“ die Domain „beispiel.de“."""
    text = raw.strip().lower()
    text = re.sub(r"^[a-z][a-z0-9+.-]*://", "", text)  # Schema
    text = re.split(r"[/?#]", text, maxsplit=1)[0]  # Pfad, Abfrage, Anker
    text = text.rsplit("@", 1)[-1]  # Zugangsdaten oder E-Mail-Adresse
    text = re.sub(r":\d+$", "", text).rstrip(".")  # Port, abschließender Punkt
    text = text.removeprefix("www.")
    if not text:
        raise InvalidDomain("Bitte eine Domain eingeben, etwa beispiel.de.")
    try:
        ipaddress.ip_address(text.strip("[]"))
    except ValueError:
        pass
    else:
        raise InvalidDomain("Bitte eine Domain eingeben, keine IP-Adresse.")
    try:
        text = text.encode("idna").decode("ascii")  # Umlaute: müller.de → xn--mller-kva.de
    except UnicodeError as error:
        raise InvalidDomain("Die Domain enthält ungültige Zeichen.") from error
    labels = text.split(".")
    if len(labels) < 2 or len(text) > 253 or not all(LABEL.match(label) for label in labels):
        raise InvalidDomain("Das ist keine gültige Domain. Beispiel: beispiel.de")
    if labels[-1] in RESERVED_TLDS or labels[-1].isdigit():
        raise InvalidDomain("Diese Domain ist nicht öffentlich erreichbar.")
    return text


def is_public_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False


# ---------------------------------------------------------------- Abfragen


class Resolver(Protocol):
    def lookup(self, name: str, record: str) -> list[str]:
        """Werte eines DNS-Eintrags, leer wenn es ihn nicht gibt. Hostnamen ohne Punkt am Ende."""
        ...


class NetworkLookup(Protocol):
    def network(self, ip: str) -> tuple[int, str] | None:
        """Nummer und Name des Netzbetreibers (ASN) einer IP-Adresse."""
        ...


# ---------------------------------------------------------------- Ergebnis


@dataclass(frozen=True)
class Finding:
    record: Record
    value: str  # der gefundene Eintrag, wörtlich
    service: str | None  # zugeordneter Dienst, None wenn kein Merkmal passt
    strength: Strength | None
    meaning: str | None
    evidence: Evidence | None  # Beleg für das Merkmal

    @property
    def category(self) -> Category:
        return CATEGORY[self.record]


@dataclass
class ScanResult:
    domain: str
    findings: list[Finding] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    imprint_urls: list[str] = field(default_factory=list)  # Kandidaten, der beste zuerst
    title: str = ""
    home_text: str = ""  # sichtbarer Text der Startseite, für die Vorschläge der KI

    @property
    def imprint_url(self) -> str | None:
        return self.imprint_urls[0] if self.imprint_urls else None

    @property
    def services(self) -> dict[str, list[Finding]]:
        grouped: dict[str, list[Finding]] = {}
        for finding in self.findings:
            if finding.service:
                grouped.setdefault(finding.service, []).append(finding)
        return grouped


# Schritte des Scans, in dieser Reihenfolge. Die Oberfläche zeigt sie beim Warten an.
STEPS = (
    "E-Mail und Domain prüfen",
    "Absender im SPF-Eintrag auflösen",
    "Hosting der Website prüfen",
    "Website laden und eingebundene Dienste erkennen",
)
MAX_SPF_ADDRESSES = 60  # Adressen aus dem SPF-Baum, deren Netz abgefragt wird
SPF_WORKERS = 8  # gleichzeitige Abfragen bei RIPEstat
LOOKUP_FAILED = object()
MAX_SPF_LOOKUPS = 20  # DNS-Abfragen beim Durchlaufen des SPF-Baums
MAX_CNAME_HOPS = 5


def scan(
    domain: str,
    resolver: Resolver,
    networks: NetworkLookup,
    fetcher: "PageFetcher | None" = None,
    on_step: Callable[[str], None] = lambda step: None,
) -> ScanResult:
    """Prüft eine Domain von außen. Ohne `fetcher` wird die Website nicht geladen."""
    rules = load_rules()
    result = ScanResult(domain)

    def safe_lookup(name: str, record: str) -> list[str]:
        try:
            return resolver.lookup(name, record)
        except Exception:  # noqa: BLE001 - jede Störung wird gemeldet, der Scan läuft weiter
            result.problems.append(f"{record}-Einträge von {name} ließen sich nicht abfragen.")
            return []

    def add(record: Record, value: str) -> None:
        rule = next((r for r in rules.dns if r.applies_to(record, value)), None)
        if rule is None:
            result.findings.append(Finding(record, value, None, None, None, None))
        else:
            result.findings.append(
                Finding(record, value, rule.service, rule.strength, rule.meaning, _evidence(rule))
            )

    on_step(STEPS[0])
    for host in sorted(set(safe_lookup(domain, "MX"))):
        add(Record.MX, host)
    includes = []
    for text in safe_lookup(domain, "TXT"):
        if text.lower().startswith("v=spf1"):
            includes += spf_includes(text)
    for include in includes:
        add(Record.SPF, include)
    for host in sorted(set(safe_lookup(domain, "NS"))):
        add(Record.NS, host)
    for issuer in sorted({_caa_issuer(value) for value in safe_lookup(domain, "CAA")} - {None}):
        add(Record.CAA, issuer)

    on_step(STEPS[1])
    # Erkannte Absender wie Microsoft 365 brauchen keinen Umweg über ihr Netz
    known = {f.value for f in result.findings if f.record is Record.SPF and f.service}
    _spf_networks(result, rules, networks, safe_lookup, known)

    on_step(STEPS[2])
    name = f"www.{domain}"
    for _ in range(MAX_CNAME_HOPS):
        targets = safe_lookup(name, "CNAME")
        if not targets:
            break
        name = targets[0]
        add(Record.CNAME, name)
    _networks(result, rules, networks, safe_lookup)

    if fetcher is not None:
        on_step(STEPS[3])
        _website(result, rules, fetcher)
    return result


def _evidence(rule: Evidence) -> Evidence:
    return Evidence(source=rule.source, quote=rule.quote, retrieved=rule.retrieved)


def _caa_issuer(value: str) -> str | None:
    """Aus „0 issue "letsencrypt.org"“ wird „letsencrypt.org“. Nur issue und issuewild zählen."""
    parts = value.split(maxsplit=2)
    if len(parts) == 3 and parts[1].lower() in {"issue", "issuewild"}:
        issuer = parts[2].strip('"').split(";")[0].strip().lower()
        return issuer or None
    return None


def _spf_networks(result, rules: DetectionRules, networks: NetworkLookup, lookup, known) -> None:
    """Netzbetreiber aller Absender im SPF-Baum, die nicht schon erkannt sind.

    So wird etwa ein Versanddienst bei Amazon erkannt, ohne dass ein eigenes Merkmal nötig
    ist: Der Beleg ist der Eintrag des Netzes bei RIPEstat. Adressen aus demselben Netzblock
    (erste zwei Zahlen gleich) werden nur einmal abgefragt.
    """
    chosen: dict[str, tuple[str, str]] = {}  # Netzblock → (Eintrag, Adresse)
    for source, address in _spf_addresses(result.domain, lookup, known):
        block = ".".join(address.split(".")[:2])
        if block not in chosen and len(chosen) < MAX_SPF_ADDRESSES:
            chosen[block] = (source, address)

    def ask(address: str):
        try:
            return networks.network(address)
        except Exception:  # noqa: BLE001 - wird unten als Problem gemeldet
            return LOOKUP_FAILED

    # Parallel, weil jede Abfrage bei RIPEstat einige hundert Millisekunden dauert
    with ThreadPoolExecutor(max_workers=SPF_WORKERS) as pool:
        answers = list(pool.map(ask, [address for _, address in chosen.values()]))
    seen: set[int] = set()
    for (source, address), found in zip(chosen.values(), answers, strict=True):
        if found is LOOKUP_FAILED:
            result.problems.append(f"Der Netzbetreiber von {address} ließ sich nicht abfragen.")
            continue
        if found is None or found[0] in seen:
            continue
        asn, holder = found
        seen.add(asn)
        rule = next((r for r in rules.asn if r.asn == asn), None)
        value = f"{source} → AS{asn} {holder}"
        meaning = f"Ein Absender im SPF-Eintrag gehört zum Netz von {holder}"
        if rule is None:
            result.findings.append(Finding(Record.SPF_NET, value, None, None, meaning, None))
        else:
            result.findings.append(
                Finding(
                    Record.SPF_NET, value, rule.service, Strength.HINWEIS, meaning, _evidence(rule)
                )
            )


def _spf_addresses(domain: str, lookup, known: set[str]) -> list[tuple[str, str]]:
    """Alle öffentlichen IPv4-Adressen im SPF-Baum, mit dem Eintrag, in dem sie stehen.

    Folgt include und redirect, höchstens MAX_SPF_LOOKUPS Abfragen und ohne Schleifen.
    """
    found: list[tuple[str, str]] = []
    queue, visited = [domain], set()
    while queue and len(visited) < MAX_SPF_LOOKUPS:
        name = queue.pop(0)
        if name in visited or name in known:
            continue
        visited.add(name)
        for text in lookup(name, "TXT"):
            if not text.lower().startswith("v=spf1"):
                continue
            for token in text.split():
                lower = token.lower().lstrip("+~?-")
                if lower.startswith("ip4:"):
                    address = token.split(":", 1)[1].split("/")[0]
                    if is_public_ip(address):
                        found.append((name, address))
                elif lower.startswith(("include:", "redirect=")):
                    queue.append(re.split("[:=]", lower, maxsplit=1)[1].rstrip("."))
    return found


def _website(result: ScanResult, rules: DetectionRules, fetcher: "PageFetcher") -> None:
    from app.scan.website import BlockedAddress, is_third_party, parse_page, visible_text

    # Erst die Domain, dann www: Manche Seiten antworten nur unter www, etwa ing.de
    page, failure = None, "Die Website ließ sich nicht laden."
    for url in (f"https://{result.domain}", f"https://www.{result.domain}"):
        try:
            page = fetcher.fetch(url)
            break
        except BlockedAddress as problem:
            result.problems.append(str(problem))
            return
        except TimeoutError:
            failure = "Die Website hat nicht innerhalb von 8 Sekunden geantwortet."
        except Exception as problem:  # noqa: BLE001 - Zeitüberschreitung von httpx und andere
            if "timeout" in type(problem).__name__.lower():
                failure = "Die Website hat nicht innerhalb von 8 Sekunden geantwortet."
    if page is None:
        result.problems.append(failure)
        return
    if page.status >= 400 or not page.html:
        result.problems.append(
            f"Die Website hat den Abruf abgelehnt (Status {page.status}). Manche Seiten sperren "
            "automatische Abrufe. Die übrigen Prüfungen sind davon nicht betroffen."
        )
        return
    info = parse_page(page.html, page.url)
    result.imprint_urls, result.title = info.imprint_urls, info.title
    result.home_text = visible_text(page.html)
    known = {
        (host, path)
        for host, path in info.script_resources
        if any(rule.applies_to(host, path) for rule in rules.web)
    }
    found: dict[str, Finding] = {}  # je Dienst oder je unbekanntem Host ein Fund
    for host, path in sorted(info.resources | known):
        if not is_third_party(host, result.domain):
            continue
        rule = next((r for r in rules.web if r.applies_to(host, path)), None)
        if rule is None:
            found.setdefault(host, Finding(Record.WEB, host, None, None, None, None))
        else:
            found.setdefault(
                rule.service,
                Finding(
                    Record.WEB,
                    f"{host}{path}",
                    rule.service,
                    rule.strength,
                    rule.meaning,
                    _evidence(rule),
                ),
            )
    _technology(result, info.resources)
    # Ein Host, der zu einem erkannten Dienst gehört, erscheint nicht zusätzlich roh. Sonst
    # stünde neben dem Tag Manager fast immer sein ns.html-Iframe. Preis: Google Maps auf
    # www.google.com geht unter, wenn dort auch reCAPTCHA erkannt wird.
    recognized_hosts = {f.value.split("/")[0] for f in found.values() if f.service}
    result.findings.extend(
        f for key, f in found.items() if f.service or key not in recognized_hosts
    )


def spf_includes(record: str) -> list[str]:
    """Die Ziele aller include-Angaben eines SPF-Eintrags, etwa „_spf.google.com“."""
    return [
        token.split(":", 1)[1].lower().rstrip(".")
        for token in record.split()
        if token.lower().lstrip("+~?-").startswith("include:")
    ]


def _networks(result: ScanResult, rules: DetectionRules, networks: NetworkLookup, lookup) -> None:
    ips = sorted(
        {ip for name in (result.domain, f"www.{result.domain}") for ip in lookup(name, "A")}
    )
    seen: set[int] = set()
    for ip in ips:
        if not is_public_ip(ip):
            result.problems.append(f"Die Website zeigt auf eine nicht öffentliche Adresse ({ip}).")
            continue
        try:
            found = networks.network(ip)
        except Exception:  # noqa: BLE001
            result.problems.append(f"Der Netzbetreiber von {ip} ließ sich nicht abfragen.")
            continue
        if found is None or found[0] in seen:
            continue
        asn, holder = found
        seen.add(asn)
        rule = next((r for r in rules.asn if r.asn == asn), None)
        value = f"AS{asn} {holder}"
        if rule is None:
            result.findings.append(Finding(Record.ASN, value, None, None, None, None))
        else:
            evidence = Evidence(source=rule.source, quote=rule.quote, retrieved=rule.retrieved)
            result.findings.append(
                Finding(Record.ASN, value, rule.service, Strength.HINWEIS, rule.meaning, evidence)
            )


WORDPRESS_PATHS = ("/wp-content/", "/wp-includes/")
WORDPRESS_PLUGIN = re.compile(r"/wp-content/plugins/([a-z0-9][a-z0-9_-]*)/")


def _technology(result: ScanResult, resources: set[tuple[str, str]]) -> None:
    """WordPress und seine Plugins, erkennbar an den typischen Pfaden der Dateien.

    Technik, kein Anbieter: Sie wird ohne Dienst gemeldet. Plugins sind trotzdem wichtig,
    weil manche Daten an ihre Hersteller senden, etwa Formulare oder Statistik.
    """
    paths = [path for _, path in resources]
    if not any(marker in path for path in paths for marker in WORDPRESS_PATHS):
        return
    result.findings.append(Finding(Record.TECH, "WordPress", None, None, None, None))
    plugins = sorted({match.group(1) for path in paths if (match := WORDPRESS_PLUGIN.search(path))})
    for plugin in plugins:
        result.findings.append(
            Finding(Record.TECH, f"WordPress-Plugin {plugin}", None, None, None, None)
        )
