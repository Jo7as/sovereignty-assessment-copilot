"""Was aus Verträgen ausgelesen wird: Themenblöcke, Felder, erlaubte Werte, Routing.

Abschnitte 5.2, 6.1, 6.3 und 6.4 der Arbeitsanweisung als Daten, die Prüfpunkte zerlegt in
Bestandteile nach dem Prüfmaßstab (docs/pruefmassstab-vertraege.md). Prompt, Wertprüfung,
Urteil und Messung lesen alle aus dieser einen Liste, damit sie nicht auseinanderlaufen.

Noch nicht enthalten: die Registerfelder (6.2, Daten und Fristen) und die Liste der
Unterauftragnehmer. Beide haben keine feste Werteliste und folgen mit dem DORA-Register.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.contracts import DocumentType
from app.models.enums import (
    AiTraining,
    DataExport,
    DataLocation,
    Jurisdiction,
    KeyManagement,
    OperationsLocation,
    TransferBasis,
)

NOT_FOUND = "NICHT_GEFUNDEN"
# Urteile der Prüfpunkte. Die KI fällt sie nicht selbst, der Code leitet sie aus den
# belegten Bestandteilen ab (pipeline.judge).
CHECK = ("VORHANDEN", "TEILWEISE")
# Wert einer Angabe zu einem Bestandteil: Der Vertrag regelt ihn, belegt mit Zitat
ELEMENT_FOUND = "BELEGT"


class Block(StrEnum):
    """Themenblöcke, je Block eine Anfrage an die KI (Arbeitsanweisung 5.3)."""

    DATENORT = "Datenort"
    UNTERAUFTRAGNEHMER = "Unterauftragnehmer"
    DATEN_UND_EXIT = "Daten und Exit"
    DSGVO = "DSGVO-Prüfliste"
    RECHT_UND_LAUFZEIT = "Recht und Laufzeit"
    BETRIEB_UND_AUFSICHT = "Betrieb und Aufsicht"


class Kind(StrEnum):
    KERN = "Kernbestandteil"  # muss geregelt sein, sonst nur TEILWEISE
    EINSCHRAENKUNG = "Einschränkung"  # typische Einschränkung, macht den Punkt TEILWEISE


@dataclass(frozen=True)
class Element:
    """Ein Bestandteil eines Prüfpunkts, als Sachfrage an den Vertrag."""

    name: str  # Prüfpunkt und Kurzname, etwa dsgvo_28_3_h.inspektion
    question: str  # geht wörtlich in den Prompt
    kind: Kind
    blocks: tuple[Block, ...]  # Blöcke, in denen danach gefragt wird


@dataclass(frozen=True)
class ContractField:
    name: str
    values: tuple[str, ...]
    hint: str  # Auslegung, geht wörtlich in den Prompt
    blocks: tuple[Block, ...]
    elements: tuple[Element, ...] = ()  # nur bei Prüfpunkten

    @property
    def is_check(self) -> bool:
        return bool(self.elements)


def _known(values) -> tuple[str, ...]:
    """Werte einer Werteliste ohne UNBEKANNT: Unbekannt heißt im Vertrag NICHT_GEFUNDEN."""
    return tuple(str(value) for value in values if value != "UNBEKANNT")


FACTS = (
    ContractField(
        "data_location",
        _known(DataLocation),
        "Ort der Datenspeicherung. EU_ZUGESICHERT nur, wenn der Vertrag Speicherung "
        "ausschließlich in EU/EWR zusagt; eine Verarbeitung außerhalb nur mit ausdrücklicher "
        "Zustimmung oder Vereinbarung des Kunden ändert daran nichts. Eine Region, die der Kunde "
        "wählen kann, ohne Zusage im Vertrag, ist EU_WAEHLBAR. EU_UND_ANGEMESSEN: EU und Länder "
        "mit Angemessenheitsbeschluss, etwa die Schweiz.",
        (Block.DATENORT,),
    ),
    ContractField(
        "operations_location",
        _known(OperationsLocation),
        "Ort von Betrieb und Support. Fernzugriff oder Support aus Drittstaaten "
        "(„follow the sun“) ist WELTWEIT.",
        (Block.DATENORT,),
    ),
    ContractField(
        "transfer_basis",
        _known(TransferBasis),
        "Grundlage für Übermittlungen in Drittländer. NICHT_NOETIG, wenn der Vertrag "
        "Übermittlungen ausschließt oder nur mit Zustimmung des Kunden erlaubt.",
        (Block.DATENORT,),
    ),
    ContractField(
        "governing_law",
        _known(Jurisdiction),
        "Recht, das für den Vertrag gilt. ANGEMESSEN: Land mit Angemessenheitsbeschluss, "
        "etwa die Schweiz oder Großbritannien.",
        (Block.RECHT_UND_LAUFZEIT,),
    ),
    ContractField(
        "key_management",
        _known(KeyManagement),
        "Wer die Schlüssel für die Verschlüsselung verwaltet. Kann der Kunde eigene Schlüssel "
        "im Schlüsseldienst des Anbieters nutzen (BYOK), ist das KUNDE_BEIM_ANBIETER.",
        (Block.DATEN_UND_EXIT,),
    ),
    ContractField(
        "data_export",
        _known(DataExport),
        "Format, in dem der Kunde seine Daten bei Vertragsende erhält. OFFENE_FORMATE oder "
        "PROPRIETAER nur, wenn der Vertrag das Format nennt. KEIN_EXPORT nur, wenn der Vertrag "
        "Rückgabe und Export ausdrücklich ausschließt. Regelt er nur Löschung oder Rückgabe, "
        "ohne Format und ohne Ausschluss, melde nichts.",
        (Block.DATEN_UND_EXIT,),
    ),
    ContractField(
        "ai_training_on_customer_data",
        _known(AiTraining),
        "Nutzt der Anbieter Kundendaten zum Training von KI-Modellen? Nur melden, wenn der "
        "Vertrag Training oder maschinelles Lernen ausdrücklich nennt.",
        (Block.DATEN_UND_EXIT,),
    ),
)


# ---------------------------------------------------------------- Prüfpunkte

type Spec = tuple[str, str, Kind, tuple[Block, ...]]


def core(key: str, question: str, *blocks: Block) -> Spec:
    """Kernbestandteil. Ohne Blöcke gelten die des Prüfpunkts."""
    return key, question, Kind.KERN, blocks


def limit(key: str, question: str, *blocks: Block) -> Spec:
    """Typische Einschränkung. Nur was der Vertrag ausdrücklich einschränkt, nicht was fehlt:
    Fehlendes zeigt sich am fehlenden Kernbestandteil."""
    return key, question, Kind.EINSCHRAENKUNG, blocks


def _check(name: str, title: str, blocks: tuple[Block, ...], *specs: Spec) -> ContractField:
    elements = tuple(
        Element(f"{name}.{key}", question, kind, own or blocks)
        for key, question, kind, own in specs
    )
    used = tuple(dict.fromkeys(block for item in elements for block in item.blocks))
    return ContractField(name, CHECK, title, used, elements)


BETRIEB, EXIT, RECHT = Block.BETRIEB_UND_AUFSICHT, Block.DATEN_UND_EXIT, Block.RECHT_UND_LAUFZEIT

# DORA Art. 30 und 28 Abs. 7, Bestandteile nach dem Wortlaut der amtlichen deutschen Fassung
DORA = (
    _check(
        "dora_30_2_a",
        "Beschreibung der Leistungen und Unterauftragsvergabe",
        (Block.UNTERAUFTRAGNEHMER,),
        # Die Leistungsbeschreibung steht im Rahmenvertrag, nicht im AVV: Sie wird nur dort
        # gefragt und zählt bei einem AVV allein als „nicht geprüft“, nicht als „fehlt“
        core(
            "leistungsbeschreibung",
            "Beschreibt der Vertrag die Leistungen des Anbieters vollständig und klar?",
            BETRIEB,
        ),
        core(
            "unterauftrag_zulaessig",
            "Legt der Vertrag fest, ob der Anbieter Unterauftragnehmer einsetzen darf?",
        ),
        core(
            "unterauftrag_bedingungen",
            "Nennt der Vertrag Bedingungen für den Einsatz von Unterauftragnehmern, etwa "
            "Genehmigung, Information vorab oder Pflichten, die an sie weitergegeben werden?",
        ),
    ),
    _check(
        "dora_30_2_b",
        "Orte der Leistung und der Datenverarbeitung",
        (Block.DATENORT,),
        core(
            "orte",
            "Nennt der Vertrag die Regionen oder Länder, in denen die Leistung erbracht und die "
            "Daten verarbeitet oder gespeichert werden (auch: die der Kunde auswählt)?",
        ),
        core(
            "aenderung_vorab",
            "Muss der Anbieter den Kunden vorab informieren, bevor er diese Orte ändert, oder "
            "braucht er dafür die Zustimmung des Kunden?",
        ),
    ),
    _check(
        "dora_30_2_c",
        "Schutz der Daten",
        (BETRIEB,),
        core("verfuegbarkeit", "Regelt der Vertrag die Verfügbarkeit der Daten?"),
        core("integritaet", "Regelt der Vertrag Integrität und Authentizität der Daten?"),
        core("vertraulichkeit", "Regelt der Vertrag die Vertraulichkeit der Daten?"),
    ),
    _check(
        "dora_30_2_d",
        "Zugang, Wiederherstellung und Rückgabe der Daten",
        (EXIT,),
        core(
            "rueckgabe",
            "Muss der Anbieter dem Kunden die Daten bei Vertragsende zurückgeben oder Zugang zu "
            "ihnen gewähren, damit der Kunde sie erhält (Löschung allein genügt nicht)?",
        ),
        core(
            "format",
            "Nennt der Vertrag ein leicht zugängliches Format für die Rückgabe?",
        ),
        core(
            "insolvenz",
            "Regelt der Vertrag Zugang oder Rückgabe der Daten auch bei Insolvenz, Abwicklung "
            "oder Einstellung der Geschäftstätigkeit des Anbieters?",
        ),
    ),
    _check(
        "dora_30_2_e",
        "Dienstleistungsgüte",
        (BETRIEB,),
        core("guete", "Beschreibt der Vertrag die Dienstleistungsgüte (Service-Level)?"),
    ),
    _check(
        "dora_30_2_f",
        "Unterstützung bei IKT-Vorfällen",
        (BETRIEB,),
        core("unterstuetzung", "Muss der Anbieter den Kunden bei IKT-Vorfällen unterstützen?"),
        core(
            "kosten",
            "Ist diese Unterstützung kostenlos oder zu vorab festgelegten Kosten zugesagt?",
        ),
    ),
    _check(
        "dora_30_2_g",
        "Zusammenarbeit mit Behörden",
        (BETRIEB,),
        core(
            "zusammenarbeit",
            "Muss der Anbieter mit den zuständigen Aufsichtsbehörden des Kunden zusammenarbeiten?",
        ),
        limit(
            "eingeschraenkt",
            "Schränkt der Vertrag diese Zusammenarbeit ein, etwa auf gesetzliche Pflichten oder "
            "auf Kosten des Kunden?",
        ),
    ),
    _check(
        "dora_30_2_h",
        "Kündigungsrechte und Mindestkündigungsfristen",
        (RECHT,),
        core("kuendigungsrechte", "Regelt der Vertrag Kündigungsrechte des Kunden?"),
        core("mindestfristen", "Nennt der Vertrag Mindestkündigungsfristen?"),
    ),
    _check(
        "dora_30_2_i",
        "Schulungen zur IKT-Sicherheit",
        (BETRIEB,),
        core(
            "schulungen",
            "Regelt der Vertrag, dass der Anbieter an Schulungen oder Programmen des Kunden zur "
            "IKT-Sicherheit und digitalen Resilienz teilnimmt?",
        ),
    ),
    _check(
        "dora_30_3_a",
        "Präzise Leistungsziele",
        (BETRIEB,),
        core("quantitativ", "Nennt der Vertrag messbare Leistungsziele, etwa Verfügbarkeit in %?"),
        core("qualitativ", "Nennt der Vertrag qualitative Leistungsziele?"),
        core(
            "korrektur",
            "Regelt der Vertrag Folgen oder Korrekturmaßnahmen, wenn Ziele verfehlt werden?",
        ),
    ),
    _check(
        "dora_30_3_b",
        "Kündigungsfristen und Berichtspflichten des Anbieters",
        (RECHT,),
        core("kuendigungsfristen", "Nennt der Vertrag Kündigungsfristen für den Anbieter?"),
        core(
            "berichtspflichten",
            "Muss der Anbieter dem Kunden Entwicklungen melden, die seine Leistung wesentlich "
            "beeinträchtigen könnten?",
        ),
    ),
    _check(
        "dora_30_3_c",
        "Notfallpläne und Sicherheitsmaßnahmen",
        (BETRIEB,),
        core("notfallplaene", "Muss der Anbieter Notfallpläne umsetzen?"),
        core("tests", "Muss der Anbieter seine Notfallpläne testen?"),
        core(
            "sicherheit",
            "Muss der Anbieter Maßnahmen für ein angemessenes Niveau der IKT-Sicherheit haben?",
        ),
    ),
    _check(
        "dora_30_3_d",
        "Bedrohungsorientierte Penetrationstests (TLPT)",
        (BETRIEB,),
        core(
            "tlpt",
            "Muss der Anbieter an bedrohungsorientierten Penetrationstests (TLPT) des Kunden "
            "teilnehmen und mitwirken?",
        ),
        limit("eingeschraenkt", "Schränkt der Vertrag diese Mitwirkung ein?"),
    ),
    _check(
        "dora_30_3_e",
        "Zugangs-, Inspektions- und Auditrechte",
        # Prüfrechte stehen meist im AVV, deshalb auch im Block der DSGVO-Prüfliste
        (BETRIEB, Block.DSGVO),
        core(
            "inspektion",
            "Darf der Kunde selbst prüfen, einschließlich Zugang und Inspektion vor Ort beim "
            "Anbieter?",
        ),
        core(
            "dritter",
            "Darf der Kunde einen Prüfer seiner Wahl mit der Prüfung beauftragen?",
        ),
        core(
            "aufsicht",
            "Haben die Aufsichtsbehörden des Kunden Zugangs-, Inspektions- oder Prüfrechte?",
        ),
        limit(
            "haeufigkeit",
            "Begrenzt der Vertrag die Häufigkeit der Prüfungen, etwa auf einmal im Jahr?",
        ),
        limit(
            "berichte",
            "Darf der Anbieter Prüfungen durch eigene Berichte, Zertifikate oder Prüfungen "
            "seiner Prüfer ersetzen oder darauf beschränken?",
        ),
        limit("kosten", "Muss der Kunde dem Anbieter Prüfungen vergüten?"),
    ),
    _check(
        "dora_30_3_f",
        "Ausstiegsstrategie",
        (EXIT,),
        core("strategie", "Regelt der Vertrag eine Ausstiegsstrategie oder Exit-Unterstützung?"),
        core(
            "uebergang",
            "Sagt der Vertrag einen Übergangszeitraum zu, in dem der Anbieter die Leistung "
            "weiter erbringt, damit der Kunde wechseln kann (nicht nur eine Frist zum Abholen "
            "der Daten)?",
        ),
    ),
    _check(
        "dora_28_7",
        "Kündigungsrechte nach Art. 28 Abs. 7",
        (RECHT,),
        core(
            "verstoss",
            "Darf der Kunde kündigen, wenn der Anbieter erheblich gegen Gesetze oder den Vertrag "
            "verstößt?",
        ),
        core(
            "beeintraechtigung",
            "Darf der Kunde kündigen, wenn Umstände die Leistung beeinträchtigen können, etwa "
            "wesentliche Änderungen beim Anbieter?",
        ),
        core(
            "risikomanagement",
            "Darf der Kunde kündigen bei nachgewiesenen Schwächen im IKT-Risikomanagement des "
            "Anbieters?",
        ),
        core(
            "aufsicht",
            "Darf der Kunde kündigen, wenn eine wirksame Beaufsichtigung nicht mehr möglich ist?",
        ),
    ),
)

# DSGVO Art. 28 Abs. 3, Bestandteile nach SCC 2021/915 Klauseln 7 bis 10 und EDPB 07/2020.
# Einschränkungen, die das Gesetz selbst vorsieht (etwa „soweit möglich“ bei e), sind keine.
DSGVO = tuple(
    _check(f"dsgvo_28_3_{letter}", title, (Block.DSGVO,), *specs)
    for letter, title, specs in (
        (
            "a",
            "Verarbeitung nur auf dokumentierte Weisung",
            (
                core(
                    "weisung",
                    "Verarbeitet der Anbieter die Daten nur auf dokumentierte Weisung des Kunden?",
                ),
                core(
                    "drittland",
                    "Gilt die Bindung an Weisungen oder die Zustimmung des Kunden auch für "
                    "Übermittlungen in Drittländer?",
                ),
                core(
                    "rechtspflicht",
                    "Muss der Anbieter den Kunden informieren, wenn ihn eine Rechtspflicht zu "
                    "einer anderen Verarbeitung zwingt?",
                ),
                limit(
                    "eigene_zwecke",
                    "Darf der Anbieter personenbezogene Kundendaten für eigene Zwecke nutzen, "
                    "die über die Leistung hinausgehen (nicht: anonymisierte oder aggregierte "
                    "Nutzungsdaten)?",
                ),
            ),
        ),
        (
            "b",
            "Vertraulichkeit der befugten Personen",
            (
                core(
                    "vertraulichkeit",
                    "Sind die Personen, die die Daten verarbeiten, zur Vertraulichkeit "
                    "verpflichtet oder einer gesetzlichen Verschwiegenheit unterworfen?",
                ),
            ),
        ),
        (
            "c",
            "Sicherheit der Verarbeitung nach Art. 32",
            (
                core(
                    "pflicht",
                    "Verpflichtet sich der Anbieter zu technischen und organisatorischen "
                    "Maßnahmen für die Sicherheit der Verarbeitung?",
                ),
                core(
                    "massnahmen",
                    "Beschreibt der Vertrag oder eine Anlage diese Maßnahmen konkret, oder "
                    "nennt er eine bestimmte Beschreibung, auf die er sich bezieht?",
                ),
                limit(
                    "einseitig",
                    "Darf der Anbieter die Maßnahmen ändern, ohne dass das Schutzniveau "
                    "erhalten bleiben muss?",
                ),
            ),
        ),
        (
            "d",
            "Weitere Auftragsverarbeiter",
            (
                core(
                    "genehmigung",
                    "Braucht der Anbieter für weitere Auftragsverarbeiter eine vorherige "
                    "gesonderte oder allgemeine Genehmigung des Kunden?",
                ),
                core(
                    "information",
                    "Muss der Anbieter den Kunden vorab über neue oder geänderte weitere "
                    "Auftragsverarbeiter informieren?",
                ),
                core(
                    "widerspruch",
                    "Kann der Kunde neuen Auftragsverarbeitern widersprechen, auch durch "
                    "Kündigung?",
                ),
                core(
                    "pflichten",
                    "Muss der Anbieter den weiteren Auftragsverarbeitern dieselben "
                    "Datenschutzpflichten auferlegen?",
                ),
            ),
        ),
        (
            "e",
            "Unterstützung bei Anträgen betroffener Personen",
            (
                core(
                    "betroffene",
                    "Unterstützt der Anbieter den Kunden bei Anträgen betroffener Personen, "
                    "auch durch technische Funktionen?",
                ),
            ),
        ),
        (
            "f",
            "Unterstützung bei den Pflichten nach Art. 32 bis 36",
            # Die Sicherheit nach Art. 32 deckt c ab: die Maßnahmen des Anbieters selbst
            (
                core(
                    "meldung",
                    "Muss der Anbieter den Kunden über Verletzungen des Schutzes "
                    "personenbezogener Daten informieren?",
                ),
                core(
                    "folgenabschaetzung",
                    "Unterstützt der Anbieter den Kunden bei Datenschutz-Folgenabschätzungen "
                    "oder der vorherigen Konsultation der Aufsichtsbehörde?",
                ),
            ),
        ),
        (
            "g",
            "Löschung oder Rückgabe nach Ende der Leistung",
            (
                core(
                    "rueckgabe",
                    "Kann der Kunde nach Ende der Leistung die Rückgabe seiner Daten verlangen "
                    "oder sie selbst abrufen?",
                ),
                core(
                    "loeschung",
                    "Muss der Anbieter die Daten nach Ende der Leistung löschen?",
                ),
            ),
        ),
        (
            "h",
            "Nachweise und Überprüfungen",
            (
                core(
                    "informationen",
                    "Stellt der Anbieter dem Kunden die Informationen zum Nachweis seiner "
                    "Pflichten zur Verfügung?",
                ),
                core(
                    "pruefung",
                    "Darf der Kunde oder ein von ihm beauftragter Prüfer Überprüfungen "
                    "einschließlich Inspektionen durchführen?",
                ),
                # Begrenzte Häufigkeit ist bei der DSGVO keine Einschränkung: SCC 7.6(d)
                # verlangt Prüfungen nur „in angemessenen Abständen“. Anders DORA 30(3)(e).
                limit(
                    "nur_berichte",
                    "Beschränkt der Vertrag Prüfungen auf Berichte, Zertifikate oder Prüfer des "
                    "Anbieters, sodass der Kunde keine eigene Prüfung verlangen kann?",
                ),
            ),
        ),
    )
)

FIELDS: tuple[ContractField, ...] = (*FACTS, *DORA, *DSGVO)
FIELDS_BY_NAME = {field.name: field for field in FIELDS}

ALL_BLOCKS = tuple(Block)
# Routing nach Dokumenttyp (Arbeitsanweisung 5.2)
ROUTES: dict[DocumentType, tuple[Block, ...]] = {
    DocumentType.AVV: (Block.DATENORT, Block.UNTERAUFTRAGNEHMER, Block.DATEN_UND_EXIT, Block.DSGVO),
    DocumentType.RAHMENVERTRAG: (
        Block.RECHT_UND_LAUFZEIT,
        Block.DATEN_UND_EXIT,
        Block.BETRIEB_UND_AUFSICHT,
    ),
    DocumentType.LEISTUNGSBESCHREIBUNG: (Block.BETRIEB_UND_AUFSICHT, Block.DATENORT),
    DocumentType.STANDARDVERTRAGSKLAUSELN: (Block.DATENORT,),
    DocumentType.UNTERAUFTRAGNEHMER: (Block.UNTERAUFTRAGNEHMER,),
    DocumentType.SONSTIGES: ALL_BLOCKS,
}
# Standardvertragsklauseln liefern nur die Übermittlungsgrundlage, nicht den ganzen Datenort
ONLY_FIELDS: dict[DocumentType, frozenset[str]] = {
    DocumentType.STANDARDVERTRAGSKLAUSELN: frozenset({"transfer_basis"}),
}


def fields_for(block: Block, document_type: DocumentType) -> tuple[ContractField, ...]:
    """Felder, die für diesen Dokumenttyp in diesem Block ausgelesen werden."""
    only = ONLY_FIELDS.get(document_type)
    return tuple(
        field for field in FIELDS if block in field.blocks and (only is None or field.name in only)
    )


def elements_for(field: ContractField, blocks: tuple[Block, ...]) -> tuple[Element, ...]:
    """Bestandteile eines Prüfpunkts, nach denen in diesen Blöcken gefragt wird."""
    return tuple(item for item in field.elements if set(item.blocks) & set(blocks))


def allowed_values(block: Block, document_type: DocumentType) -> dict[str, tuple[str, ...]]:
    """Namen, die die KI in diesem Block melden darf, mit ihren erlaubten Werten."""
    allowed = {}
    for field in fields_for(block, document_type):
        if field.is_check:
            allowed |= {item.name: (ELEMENT_FOUND,) for item in elements_for(field, (block,))}
        else:
            allowed[field.name] = field.values
    return allowed


def asked_elements(field: ContractField, document_types) -> tuple[Element, ...]:
    """Bestandteile, nach denen bei Dokumenten dieser Typen gefragt wurde."""
    asked = {
        item.name
        for document_type in document_types
        if field in fields_for_type(document_type)
        for item in elements_for(field, ROUTES[document_type])
    }
    return tuple(item for item in field.elements if item.name in asked)


def fields_for_type(document_type: DocumentType) -> tuple[ContractField, ...]:
    """Alle Felder, die für diesen Dokumenttyp ausgelesen werden, in der Reihenfolge von FIELDS."""
    read = {
        item.name for block in ROUTES[document_type] for item in fields_for(block, document_type)
    }
    return tuple(field for field in FIELDS if field.name in read)
