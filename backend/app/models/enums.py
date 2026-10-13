"""Wertelisten der Anbieterdatenbank, erklärt in docs/datenmodell.md."""

from enum import StrEnum, auto


class Jurisdiction(StrEnum):
    EU_EWR = auto()
    ANGEMESSEN = auto()
    USA = auto()
    DRITTSTAAT = auto()


class Criticality(StrEnum):
    GERING = auto()
    MITTEL = auto()
    HOCH = auto()


class DataLocation(StrEnum):
    EU_ZUGESICHERT = auto()
    EU_WAEHLBAR = auto()
    NICHT_EU = auto()
    UNBEKANNT = auto()


class OperationsLocation(StrEnum):
    NUR_EU = auto()
    EU_MIT_AUSNAHMEN = auto()
    WELTWEIT = auto()
    UNBEKANNT = auto()


class TransferBasis(StrEnum):
    NICHT_NOETIG = auto()
    STANDARDVERTRAGSKLAUSELN = auto()
    DATA_PRIVACY_FRAMEWORK = auto()
    KEINE = auto()
    UNBEKANNT = auto()


class KeyManagement(StrEnum):
    ANBIETER = auto()
    KUNDE_BEIM_ANBIETER = auto()
    KUNDE_EXTERN = auto()
    UNBEKANNT = auto()


class DataExport(StrEnum):
    OFFENE_FORMATE = auto()
    PROPRIETAER = auto()
    KEIN_EXPORT = auto()
    UNBEKANNT = auto()


class Openness(StrEnum):
    OPEN_SOURCE = auto()
    OFFENE_STANDARDS = auto()
    PROPRIETAER = auto()
    UNBEKANNT = auto()


class AiTraining(StrEnum):
    NEIN = auto()
    ABWAEHLBAR = auto()
    JA = auto()
    UNBEKANNT = auto()


class RenewableEnergy(StrEnum):
    NACHGEWIESEN = auto()
    ZUGESAGT = auto()
    KEINE_ANGABE = auto()


class ReviewStatus(StrEnum):
    KI_VORSCHLAG = auto()
    KI_NACHGEPRUEFT = auto()
    GEPRUEFT = auto()


class DependencyKind(StrEnum):
    HOSTING = auto()
    UNTERAUFTRAGNEHMER = auto()
    TECHNOLOGIE = auto()
    SUPPORT = auto()


class MigrationEffort(StrEnum):
    GERING = auto()
    MITTEL = auto()
    HOCH = auto()
