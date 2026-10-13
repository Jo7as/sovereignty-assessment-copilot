"""Wertelisten der Anbieterdatenbank, erklärt in docs/datenmodell.md."""

from enum import StrEnum, auto


class Values(StrEnum):
    """Werteliste, deren Werte so heißen wie ihre Namen (`EU_EWR`, nicht `eu_ewr`)."""

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> str:
        return name


class Jurisdiction(Values):
    EU_EWR = auto()
    ANGEMESSEN = auto()
    USA = auto()
    DRITTSTAAT = auto()


class Criticality(Values):
    GERING = auto()
    MITTEL = auto()
    HOCH = auto()


class DataLocation(Values):
    EU_ZUGESICHERT = auto()
    EU_WAEHLBAR = auto()
    NICHT_EU = auto()
    UNBEKANNT = auto()


class OperationsLocation(Values):
    NUR_EU = auto()
    EU_MIT_AUSNAHMEN = auto()
    WELTWEIT = auto()
    UNBEKANNT = auto()


class TransferBasis(Values):
    NICHT_NOETIG = auto()
    STANDARDVERTRAGSKLAUSELN = auto()
    DATA_PRIVACY_FRAMEWORK = auto()
    KEINE = auto()
    UNBEKANNT = auto()


class KeyManagement(Values):
    ANBIETER = auto()
    KUNDE_BEIM_ANBIETER = auto()
    KUNDE_EXTERN = auto()
    UNBEKANNT = auto()


class DataExport(Values):
    OFFENE_FORMATE = auto()
    PROPRIETAER = auto()
    KEIN_EXPORT = auto()
    UNBEKANNT = auto()


class Openness(Values):
    OPEN_SOURCE = auto()
    OFFENE_STANDARDS = auto()
    PROPRIETAER = auto()
    UNBEKANNT = auto()


class AiTraining(Values):
    NEIN = auto()
    ABWAEHLBAR = auto()
    JA = auto()
    UNBEKANNT = auto()


class RenewableEnergy(Values):
    NACHGEWIESEN = auto()
    ZUGESAGT = auto()
    KEINE_ANGABE = auto()


class ReviewStatus(Values):
    KI_VORSCHLAG = auto()
    KI_NACHGEPRUEFT = auto()
    GEPRUEFT = auto()


class DependencyKind(Values):
    HOSTING = auto()
    UNTERAUFTRAGNEHMER = auto()
    TECHNOLOGIE = auto()
    SUPPORT = auto()


class MigrationEffort(Values):
    GERING = auto()
    MITTEL = auto()
    HOCH = auto()
