"""Was aus Verträgen ausgelesen wird: Themenblöcke, Felder, erlaubte Werte, Routing.

Abschnitte 5.2, 6.1, 6.3 und 6.4 der Arbeitsanweisung als Daten. Prompt, Wertprüfung und
Messung lesen alle aus dieser einen Liste, damit sie nicht auseinanderlaufen.

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
# Werte der Prüfpunkte. NICHT_GEFUNDEN meldet die KI, indem sie den Punkt weglässt.
CHECK = ("VORHANDEN", "TEILWEISE")


class Block(StrEnum):
    """Themenblöcke, je Block eine Anfrage an die KI (Arbeitsanweisung 5.3)."""

    DATENORT = "Datenort"
    UNTERAUFTRAGNEHMER = "Unterauftragnehmer"
    DATEN_UND_EXIT = "Daten und Exit"
    DSGVO = "DSGVO-Prüfliste"
    RECHT_UND_LAUFZEIT = "Recht und Laufzeit"
    BETRIEB_UND_AUFSICHT = "Betrieb und Aufsicht"


@dataclass(frozen=True)
class ContractField:
    name: str
    values: tuple[str, ...]
    hint: str  # Auslegung, geht wörtlich in den Prompt
    blocks: tuple[Block, ...]


def _known(values) -> tuple[str, ...]:
    """Werte einer Werteliste ohne UNBEKANNT: Unbekannt heißt im Vertrag NICHT_GEFUNDEN."""
    return tuple(str(value) for value in values if value != "UNBEKANNT")


FACTS = (
    ContractField(
        "data_location",
        _known(DataLocation),
        "Ort der Datenspeicherung. EU_ZUGESICHERT nur, wenn der Vertrag Speicherung "
        "ausschließlich in EU/EWR zusagt. Eine Region, die der Kunde wählen kann, ohne Zusage "
        "im Vertrag, ist EU_WAEHLBAR. EU_UND_ANGEMESSEN: EU und Länder mit "
        "Angemessenheitsbeschluss, etwa die Schweiz.",
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
        "Herausgabe der Daten bei Vertragsende und ihr Format. Nur Löschung ohne Herausgabe "
        "ist KEIN_EXPORT. Ohne Angabe zum Format nicht melden.",
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

# DORA Art. 30, Wortlaut verkürzt nach der amtlichen deutschen Fassung (Arbeitsanweisung 6.3)
DORA = {
    "dora_30_2_a": (
        "Beschreibung aller Leistungen; ob Unterauftragsvergabe zulässig ist und unter welchen "
        "Bedingungen",
        (Block.UNTERAUFTRAGNEHMER,),
    ),
    "dora_30_2_b": (
        "Regionen oder Länder der Leistung und der Datenverarbeitung samt Speicherort; Pflicht, "
        "Änderungen vorab mitzuteilen",
        (Block.DATENORT,),
    ),
    "dora_30_2_c": (
        "Verfügbarkeit, Authentizität, Integrität und Vertraulichkeit der Daten",
        (Block.BETRIEB_UND_AUFSICHT,),
    ),
    "dora_30_2_d": (
        "Zugang zu den Daten, Wiederherstellung und Rückgabe in leicht zugänglichem Format bei "
        "Insolvenz, Abwicklung, Einstellung oder Vertragsende",
        (Block.DATEN_UND_EXIT,),
    ),
    "dora_30_2_e": ("Beschreibung der Dienstleistungsgüte", (Block.BETRIEB_UND_AUFSICHT,)),
    "dora_30_2_f": (
        "Unterstützung bei IKT-Vorfällen ohne zusätzliche oder zu vorab festgelegten Kosten",
        (Block.BETRIEB_UND_AUFSICHT,),
    ),
    "dora_30_2_g": (
        "volle Zusammenarbeit mit den zuständigen Behörden",
        (Block.BETRIEB_UND_AUFSICHT,),
    ),
    "dora_30_2_h": ("Kündigungsrechte und Mindestkündigungsfristen", (Block.RECHT_UND_LAUFZEIT,)),
    "dora_30_2_i": (
        "Teilnahme an Schulungen zur IKT-Sicherheit und digitalen Resilienz",
        (Block.BETRIEB_UND_AUFSICHT,),
    ),
    "dora_30_3_a": (
        "präzise quantitative und qualitative Leistungsziele",
        (Block.BETRIEB_UND_AUFSICHT,),
    ),
    "dora_30_3_b": (
        "Kündigungsfristen und Berichtspflichten des Anbieters",
        (Block.RECHT_UND_LAUFZEIT,),
    ),
    "dora_30_3_c": (
        "Notfallpläne, die der Anbieter umsetzt und testet; Sicherheitsmaßnahmen",
        (Block.BETRIEB_UND_AUFSICHT,),
    ),
    "dora_30_3_d": (
        "Mitwirkung an bedrohungsorientierten Penetrationstests (TLPT)",
        (Block.BETRIEB_UND_AUFSICHT,),
    ),
    # Prüfrechte stehen meist im AVV, deshalb auch im Block der DSGVO-Prüfliste
    "dora_30_3_e": (
        "uneingeschränkte Zugangs-, Inspektions- und Auditrechte des Kunden",
        (Block.BETRIEB_UND_AUFSICHT, Block.DSGVO),
    ),
    "dora_30_3_f": (
        "Ausstiegsstrategie mit verbindlichem, angemessenem Übergangszeitraum",
        (Block.DATEN_UND_EXIT,),
    ),
    "dora_28_7": (
        "Kündigungsrechte bei erheblichem Verstoß, festgestellter Beeinträchtigung, Schwächen im "
        "IKT-Risikomanagement oder wenn keine wirksame Aufsicht mehr möglich ist",
        (Block.RECHT_UND_LAUFZEIT,),
    ),
}

# DSGVO Art. 28 Abs. 3 (Arbeitsanweisung 6.4)
DSGVO = {
    "a": "Verarbeitung nur auf dokumentierte Weisung, auch bei Übermittlung in Drittländer",
    "b": "Vertraulichkeit der zur Verarbeitung befugten Personen",
    "c": "Maßnahmen zur Sicherheit der Verarbeitung nach Art. 32",
    "d": "Bedingungen für weitere Auftragsverarbeiter nach Art. 28 Abs. 2 und 4",
    "e": "Unterstützung bei Anträgen betroffener Personen",
    "f": "Unterstützung bei den Pflichten nach Art. 32 bis 36 (Sicherheit, Meldungen, DSFA)",
    "g": "Löschung oder Rückgabe aller Daten nach Ende der Leistung",
    "h": "Nachweise und Überprüfungen einschließlich Inspektionen",
}

CHECK_HINT = (
    "Prüfpunkt: VORHANDEN, wenn der Vertrag den Punkt regelt; TEILWEISE, wenn er geregelt, "
    "aber deutlich eingeschränkt ist. Inhalt: "
)

FIELDS: tuple[ContractField, ...] = (
    *FACTS,
    *(
        ContractField(name, CHECK, CHECK_HINT + text, blocks)
        for name, (text, blocks) in DORA.items()
    ),
    *(
        ContractField(f"dsgvo_28_3_{letter}", CHECK, CHECK_HINT + text, (Block.DSGVO,))
        for letter, text in DSGVO.items()
    ),
)
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
