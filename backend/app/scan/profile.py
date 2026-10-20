"""Unternehmensprofil aus der Website: Impressum auslesen und mit GLEIF abgleichen.

Jede Angabe kommt mit Fundstelle. Was nicht sicher zuzuordnen ist, bleibt offen: Eine
Registernummer allein ist nicht eindeutig (jedes Amtsgericht vergibt eigene Nummern), ein
Name allein auch nicht. Bei GLEIF gilt ein Eintrag deshalb nur, wenn Name und Nummer passen.
"""

import re
from dataclasses import dataclass, field
from typing import Protocol

GLEIF_RECORD = "https://api.gleif.org/api/v1/lei-records/{lei}"

REGISTER = re.compile(r"\b(HRB|HRA|GnR|PR|VR)\s*(\d+(?:\s?[A-Z]{1,2}\b)?)")
COURT = re.compile(
    r"Amtsgerichts?\s+([A-ZÄÖÜ][\wäöüß.-]*(?:\s+(?:am|an der|in der|im)\s+[A-ZÄÖÜ][\wäöüß.-]*)?)"
)
SUPERVISION = re.compile(r"Bundesanstalt für Finanzdienstleistungsaufsicht|\bBaFin\b")
VAT_ID = re.compile(r"\bDE\s?\d{9}\b")
LEGAL_FORM = re.compile(
    r"\b(GmbH & Co\. KGaA|GmbH & Co\. KG|SE & Co\. KG|AG & Co\. KG|GmbH|AG|SE|KGaA|eG|e\.G\.|"
    r"KG|OHG|mbH|Aktiengesellschaft)\b"
)
# Überschriften, die oft ohne Trennung vor dem Firmennamen stehen
HEADING = re.compile(
    r"^(?:Impressum|Imprint|Anbieter|Angaben gemäß § ?5 (?:TMG|DDG))\s*:?\s*", re.I
)
CONTEXT = 140  # Zeichen um einen Fund, die als Fundstelle gezeigt werden


@dataclass(frozen=True)
class Sourced:
    value: str
    quote: str  # wörtlicher Ausschnitt aus der Quelle
    source: str  # Adresse der Quelle


@dataclass(frozen=True)
class Register:
    kind: str  # HRB, HRA, GnR, PR oder VR
    number: str
    court: str | None
    quote: str
    source: str

    @property
    def label(self) -> str:
        return f"{self.kind} {self.number}"


@dataclass(frozen=True)
class LeiRecord:
    lei: str
    name: str
    city: str
    country: str
    registered_as: str | None

    @property
    def source(self) -> str:
        return GLEIF_RECORD.format(lei=self.lei)


@dataclass
class ImprintFacts:
    legal_name: Sourced | None = None
    register: Register | None = None
    supervision: Sourced | None = None  # Hinweis auf die Aufsicht durch die BaFin
    vat_id: Sourced | None = None


@dataclass
class CompanyProfile:
    imprint_url: str | None = None
    imprint: ImprintFacts = field(default_factory=ImprintFacts)
    entity: LeiRecord | None = None  # Eintrag bei GLEIF
    parent: LeiRecord | None = None  # oberste Konzernmutter laut GLEIF
    notes: list[str] = field(default_factory=list)


class Gleif(Protocol):
    def by_register(self, register: str) -> list[LeiRecord]: ...

    def by_name(self, name: str) -> list[LeiRecord]: ...

    def ultimate_parent(self, lei: str) -> LeiRecord | None: ...


def _excerpt(text: str, start: int, end: int) -> str:
    left = max(0, start - CONTEXT // 2)
    return text[left : end + CONTEXT // 2].strip()


def looks_like_imprint(text: str) -> bool:
    """Ein Impressum nennt Registernummer, USt-ID oder § 5 DDG/TMG. Eine Produktseite, die das
    Wort „Impressum“ nur erwähnt, tut das meist nicht."""
    return bool(REGISTER.search(text) or VAT_ID.search(text) or re.search(r"§\s?5\b", text))


def extract_imprint(text: str, source: str) -> ImprintFacts:
    """Liest Firmenname, Registereintrag, Aufsicht und Umsatzsteuer-ID aus dem Impressum."""
    facts = ImprintFacts()
    if match := REGISTER.search(text):
        window = text[max(0, match.start() - 160) : match.end() + 80]
        court = COURT.search(window)
        facts.register = Register(
            kind=match.group(1),
            number=re.sub(r"\s+", " ", match.group(2)).strip(),
            court=court.group(1) if court else None,
            quote=_excerpt(text, match.start(), match.end()),
            source=source,
        )
    if match := SUPERVISION.search(text):
        facts.supervision = Sourced("BaFin", _excerpt(text, match.start(), match.end()), source)
    if match := VAT_ID.search(text):
        facts.vat_id = Sourced(
            match.group(0).replace(" ", ""), _excerpt(text, match.start(), match.end()), source
        )
    facts.legal_name = _legal_name(text, source)
    return facts


def _legal_name(text: str, source: str) -> Sourced | None:
    """Erster kurzer Abschnitt mit einer Rechtsform, etwa „ING-DiBa AG“."""
    for segment in re.split(r"\s*\|\s*|\n", text):
        segment = segment.strip()
        match = LEGAL_FORM.search(segment)
        if match and 3 <= len(segment) <= 80 and segment[0].isupper():
            name = HEADING.sub("", segment[: match.end()]).strip(" ,;:")
            if len(name) > len(match.group(0)) + 1:
                return Sourced(name, segment, source)
    return None


def _normalized(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.casefold().replace("aktiengesellschaft", "ag"))


def find_entity(imprint: ImprintFacts, gleif: Gleif) -> tuple[LeiRecord | None, str]:
    """Sucht den GLEIF-Eintrag. Gilt nur, wenn Name und Registernummer zusammenpassen."""
    register, name = imprint.register, imprint.legal_name
    if register is None or name is None:
        return None, "Für den Abgleich mit GLEIF fehlen Name oder Registernummer im Impressum."
    wanted = _normalized(name.value)
    candidates = [
        record
        for record in gleif.by_register(register.label)
        # Gleich oder vollständig enthalten, falls im Impressum noch Text am Namen hängt
        if _normalized(record.name) == wanted
        or (len(_normalized(record.name)) >= 4 and _normalized(record.name) in wanted)
    ]
    if len(candidates) == 1:
        return candidates[0], "Name und Registernummer stimmen mit dem Eintrag bei GLEIF überein."
    if not candidates:
        return (
            None,
            f"Bei GLEIF gibt es keinen Eintrag mit Name „{name.value}“ und {register.label}.",
        )
    return None, f"Bei GLEIF passen mehrere Einträge zu „{name.value}“ und {register.label}."


def build_profile(
    imprint_text: str | None, imprint_url: str | None, gleif: Gleif
) -> CompanyProfile:
    profile = CompanyProfile(imprint_url=imprint_url)
    if not imprint_text or not imprint_url:
        profile.notes.append("Kein Impressum gefunden oder es ließ sich nicht laden.")
        return profile
    profile.imprint = extract_imprint(imprint_text, imprint_url)
    try:
        profile.entity, note = find_entity(profile.imprint, gleif)
        profile.notes.append(note)
        if profile.entity:
            profile.parent = gleif.ultimate_parent(profile.entity.lei)
            if profile.parent is None:
                profile.notes.append("GLEIF nennt keine Konzernmutter.")
    except Exception:  # noqa: BLE001 - GLEIF nicht erreichbar, das Profil bleibt ohne Abgleich
        profile.notes.append("GLEIF ließ sich nicht abfragen.")
    return profile
