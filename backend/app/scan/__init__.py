"""Außenscan: Was eine Domain von außen über die genutzten Dienste verrät.

Geprüft werden Mailserver (MX), SPF-Einträge, Nameserver (NS) und der Netzbetreiber der
Website (über RIPEstat). Die Erkennungsmerkmale stehen mit Quelle in data/detection.yaml.
Funde ohne passenden Dienst in der Datenbank werden roh gemeldet, nie geraten.

Erläutert in docs/bewertungslogik.md, Abschnitt „Außenscan“.
"""

import datetime
import ipaddress
import re
from dataclasses import dataclass, field
from enum import auto
from functools import cache
from typing import Protocol

import yaml
from pydantic import BaseModel, ConfigDict

from app.config import PROJECT_ROOT
from app.models.enums import Values

DETECTION_FILE = PROJECT_ROOT / "data" / "detection.yaml"


class Strength(Values):
    NUTZUNG = auto()  # nachweislich genutzt, etwa weil die E-Mails darüber laufen
    HINWEIS = auto()  # deutet auf den Dienst hin, belegt die Nutzung aber nicht


class Record(Values):
    MX = auto()
    SPF = auto()
    NS = auto()
    ASN = auto()


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


class DetectionRules(Model):
    dns: tuple[DnsRule, ...]
    asn: tuple[AsnRule, ...]


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


@dataclass
class ScanResult:
    domain: str
    findings: list[Finding] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def services(self) -> dict[str, list[Finding]]:
        grouped: dict[str, list[Finding]] = {}
        for finding in self.findings:
            if finding.service:
                grouped.setdefault(finding.service, []).append(finding)
        return grouped


def scan(domain: str, resolver: Resolver, networks: NetworkLookup) -> ScanResult:
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
            evidence = Evidence(source=rule.source, quote=rule.quote, retrieved=rule.retrieved)
            result.findings.append(
                Finding(record, value, rule.service, rule.strength, rule.meaning, evidence)
            )

    for host in sorted(set(safe_lookup(domain, "MX"))):
        add(Record.MX, host)
    for text in safe_lookup(domain, "TXT"):
        if text.lower().startswith("v=spf1"):
            for include in spf_includes(text):
                add(Record.SPF, include)
    for host in sorted(set(safe_lookup(domain, "NS"))):
        add(Record.NS, host)
    _networks(result, rules, networks, safe_lookup)
    return result


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
