"""Regeln für die Stufe 0 bis 4 je Zielbereich.

Jeder Zielbereich besteht aus Kriterien. Ein Kriterium nennt die Stufe, die es höchstens
zulässt, und den Grund dafür. Die Stufe des Zielbereichs ist die niedrigste dieser
Obergrenzen. Das folgt Abschnitt 4 des EU Cloud Sovereignty Framework: Eine wesentliche
Schwäche in einem Kriterium senkt die Stufe des ganzen Zielbereichs.

Herleitung und Quellen stehen in docs/bewertungslogik.md.
"""

from collections.abc import Callable
from datetime import date

from app.models.enums import (
    AiTraining,
    DataExport,
    DataLocation,
    DependencyKind,
    Jurisdiction,
    KeyManagement,
    Openness,
    OperationsLocation,
    RenewableEnergy,
    TransferBasis,
)
from app.scoring.model import MAX_LEVEL, Finding, Objective, VariantFacts

EU = Jurisdiction.EU_EWR
ADEQUATE = Jurisdiction.ANGEMESSEN

# Zertifikate, die ein EU-Staat oder die EU herausgibt, und international anerkannte
EU_CERTIFICATES = frozenset({"bsi-c5"})
INTERNATIONAL_CERTIFICATES = frozenset({"iso-27001"})

JURISDICTION_LABEL = {
    Jurisdiction.EU_EWR: "EU/EWR",
    Jurisdiction.ANGEMESSEN: "Drittstaat mit Angemessenheitsbeschluss",
    Jurisdiction.USA: "USA",
    Jurisdiction.DRITTSTAAT: "Drittstaat",
}


def known(criterion: str, ceiling: int, reason: str, fact: str | None = None) -> Finding:
    return Finding(criterion, ceiling, ceiling, reason, fact)


def gap(criterion: str, worst: int, best: int, reason: str, fact: str) -> Finding:
    """Eine fehlende Angabe: gesichert gilt der ungünstigste Fall, möglich der günstigste."""
    return Finding(criterion, worst, best, reason, fact)


# --- Bausteine, die mehrere Zielbereiche nutzen ----------------------------------------


def jurisdiction_ceiling(jurisdiction: Jurisdiction, has_eu_operating_company: bool) -> int:
    """Wie weit trägt ein Rechtsraum? Entspricht den Stufenbeschreibungen des Rahmenwerks.

    4: vollständig unter EU-Kontrolle.
    3: Drittstaat, dem die EU ein angemessenes Schutzniveau bescheinigt.
    2: außerhalb der EU, aber mit eigener Betriebsgesellschaft in der EU (mittelbare Kontrolle).
    1: außerhalb der EU, EU-Recht gilt nur formal.
    """
    if jurisdiction is EU:
        return 4
    if jurisdiction is ADEQUATE:
        return 3
    return 2 if has_eu_operating_company else 1


def control(facts: VariantFacts, criterion: str) -> Finding:
    """Wer entscheidet über den Dienst, und welchem Recht untersteht er?"""
    jurisdiction = facts.controller_jurisdiction
    ceiling = jurisdiction_ceiling(jurisdiction, facts.has_eu_operating_company)
    label = JURISDICTION_LABEL[jurisdiction]
    if jurisdiction is EU:
        reason = "Die Konzernmutter des verantwortlichen Unternehmens sitzt in der EU."
    elif jurisdiction is ADEQUATE:
        reason = f"Die Konzernmutter sitzt außerhalb der EU ({label})."
    elif facts.has_eu_operating_company:
        reason = (
            f"Die Konzernmutter sitzt außerhalb der EU ({label}). "
            "Eine Betriebsgesellschaft mit Sitz in der EU betreibt den Dienst."
        )
    else:
        reason = (
            f"Die Konzernmutter sitzt außerhalb der EU ({label}), "
            "eine eigene Betriebsgesellschaft in der EU gibt es nicht."
        )
    return known(criterion, ceiling, reason, "ultimate_parent")


def origin_ceiling(facts: VariantFacts) -> int:
    """Woher stammt die Technologie? Maßgeblich ist der Anbieter, nicht der Betreiber."""
    return jurisdiction_ceiling(facts.provider_jurisdiction, facts.has_eu_operating_company)


def critical_non_eu_dependency(
    facts: VariantFacts,
    criterion: str,
    ceiling: int,
    kinds: frozenset[DependencyKind] | None = None,
) -> Finding:
    """Senkt die Stufe, wenn der Dienst ohne einen Zulieferer außerhalb der EU ausfällt."""
    critical = [
        dependency
        for dependency in facts.dependencies
        if dependency.critical
        and dependency.jurisdiction is not EU
        and (kinds is None or dependency.kind in kinds)
    ]
    if critical:
        names = ", ".join(sorted({dependency.supplier for dependency in critical}))
        return known(
            criterion,
            ceiling,
            f"Der Dienst fällt ohne Zulieferer außerhalb der EU aus ({names}).",
            "dependencies",
        )
    if facts.dependencies_complete:
        return known(
            criterion, MAX_LEVEL, "Kein kritischer Zulieferer außerhalb der EU.", "dependencies"
        )
    return gap(
        criterion,
        ceiling,
        MAX_LEVEL,
        "Die Zulieferer sind nicht vollständig geprüft. "
        "Ein kritischer Zulieferer außerhalb der EU ist nicht auszuschließen.",
        "dependencies",
    )


# --- SOV-1 Strategisch -----------------------------------------------------------------


def strategic(facts: VariantFacts, today: date) -> list[Finding]:
    return [
        control(facts, "Entscheidungsgewalt"),
        critical_non_eu_dependency(facts, "Fortbestand ohne Nicht-EU-Zulieferer", ceiling=3),
    ]


# --- SOV-2 Rechtlich -------------------------------------------------------------------


def legal(facts: VariantFacts, today: date) -> list[Finding]:
    findings = [control(facts, "Zugriff fremder Behörden"), governing_law(facts)]
    transfer = transfer_basis(facts)
    if transfer is not None:
        findings.append(transfer)
    return findings


def governing_law(facts: VariantFacts) -> Finding:
    criterion = "Vertragsrecht und Gerichtsstand"
    law = facts.governing_law
    if law is None:
        return gap(
            criterion,
            1,
            MAX_LEVEL,
            "Vertragsrecht und Gerichtsstand sind nicht belegt.",
            "governing_law",
        )
    if law is EU:
        return known(
            criterion, 4, "Der Vertrag unterliegt dem Recht eines EU-Staats.", "governing_law"
        )
    if law is ADEQUATE:
        return known(
            criterion,
            3,
            "Der Vertrag unterliegt dem Recht eines Drittstaats mit Angemessenheitsbeschluss.",
            "governing_law",
        )
    return known(
        criterion,
        1,
        f"Der Vertrag unterliegt dem Recht eines Staats außerhalb der EU "
        f"({JURISDICTION_LABEL[law]}).",
        "governing_law",
    )


def transfer_basis(facts: VariantFacts) -> Finding | None:
    """Eine Übermittlungsgrundlage braucht, wer Daten dem Zugriff aus einem Drittstaat aussetzt."""
    criterion = "Grundlage für die Datenübermittlung"
    # Für einen Staat mit Angemessenheitsbeschluss genügt dieser Beschluss (Art. 45 DSGVO)
    needed = (
        facts.controller_jurisdiction not in (EU, ADEQUATE)
        or facts.data_location is DataLocation.NICHT_EU
    )
    possibly_needed = not needed and facts.data_location is DataLocation.UNBEKANNT
    if not needed and not possibly_needed:
        return None

    basis = facts.transfer_basis
    if basis is TransferBasis.UNBEKANNT:
        if possibly_needed:
            # Ob überhaupt übermittelt wird, hängt am Datenstandort. Er ist die eigentliche Lücke.
            return gap(
                criterion,
                0,
                MAX_LEVEL,
                "Der Datenstandort ist offen, "
                "eine Übermittlung in Drittstaaten ist nicht auszuschließen.",
                "data_location",
            )
        return gap(
            criterion,
            0,
            MAX_LEVEL,
            "Eine Übermittlungsgrundlage ist nicht belegt.",
            "transfer_basis",
        )
    if basis is TransferBasis.KEINE:
        reason = "Für die Übermittlung in einen Drittstaat fehlt eine Rechtsgrundlage."
        if possibly_needed:
            return gap(
                criterion, 0, MAX_LEVEL, reason + " Der Datenstandort ist offen.", "data_location"
            )
        return known(criterion, 0, reason, "transfer_basis")
    labels = {
        TransferBasis.NICHT_NOETIG: "Eine Übermittlung in einen Drittstaat findet nicht statt.",
        TransferBasis.STANDARDVERTRAGSKLAUSELN: (
            "Die Übermittlung stützt sich auf Standardvertragsklauseln."
        ),
        TransferBasis.DATA_PRIVACY_FRAMEWORK: (
            "Die Übermittlung stützt sich auf das EU-US Data Privacy Framework."
        ),
        TransferBasis.ANGEMESSENHEITSBESCHLUSS: (
            "Die Übermittlung stützt sich auf einen Angemessenheitsbeschluss der EU."
        ),
        TransferBasis.VERBINDLICHE_UNTERNEHMENSREGELN: (
            "Die Übermittlung stützt sich auf verbindliche Unternehmensregeln (BCR)."
        ),
    }
    return known(criterion, MAX_LEVEL, labels[basis], "transfer_basis")


# --- SOV-3 Daten und KI ----------------------------------------------------------------

DATA_LOCATION = {
    DataLocation.EU_ZUGESICHERT: (4, "Speicherung und Verarbeitung in der EU sind zugesichert."),
    DataLocation.EU_WAEHLBAR: (
        3,
        "Ein Standort in der EU ist wählbar, aber nicht voreingestellt oder zugesichert.",
    ),
    DataLocation.NICHT_EU: (0, "Die Daten liegen außerhalb der EU."),
}

# Stufe je Schlüsselverwaltung, abhängig davon, wem die Herausgabe befohlen werden könnte:
# (Kontrolle in der EU, Drittstaat mit Angemessenheitsbeschluss, sonstiger Drittstaat)
KEY_MANAGEMENT = {
    KeyManagement.KUNDE_EXTERN: (4, 4, 4),
    KeyManagement.KUNDE_BEIM_ANBIETER: (4, 3, 2),
    KeyManagement.ANBIETER: (3, 2, 1),
}
KEY_MANAGEMENT_REASON = {
    KeyManagement.KUNDE_EXTERN: (
        "Die Schlüssel liegen beim Kunden außerhalb der Systeme des Anbieters."
    ),
    KeyManagement.KUNDE_BEIM_ANBIETER: (
        "Der Kunde steuert die Schlüssel, sie liegen aber in Systemen des Anbieters."
    ),
    KeyManagement.ANBIETER: "Der Anbieter verwaltet die Schlüssel.",
}

AI_TRAINING = {
    AiTraining.NEIN: (4, "Kundendaten werden nicht für KI-Training genutzt."),
    AiTraining.ABWAEHLBAR: (3, "Die Nutzung von Kundendaten für KI-Training ist abwählbar."),
    AiTraining.JA: (1, "Kundendaten werden für KI-Training genutzt."),
}


def data_and_ai(facts: VariantFacts, today: date) -> list[Finding]:
    return [data_location(facts), key_management(facts), ai_training(facts)]


def data_location(facts: VariantFacts) -> Finding:
    criterion = "Datenstandort"
    if facts.data_location is DataLocation.UNBEKANNT:
        return gap(criterion, 0, MAX_LEVEL, "Der Datenstandort ist nicht belegt.", "data_location")
    ceiling, reason = DATA_LOCATION[facts.data_location]
    return known(criterion, ceiling, reason, "data_location")


def key_management(facts: VariantFacts) -> Finding:
    criterion = "Schlüsselverwaltung"
    column = {EU: 0, ADEQUATE: 1}.get(facts.controller_jurisdiction, 2)
    if facts.key_management is KeyManagement.UNBEKANNT:
        return gap(
            criterion,
            KEY_MANAGEMENT[KeyManagement.ANBIETER][column],
            MAX_LEVEL,
            "Die Schlüsselverwaltung ist nicht belegt. "
            "Angenommen wird, dass der Anbieter sie führt.",
            "key_management",
        )
    ceiling = KEY_MANAGEMENT[facts.key_management][column]
    return known(criterion, ceiling, KEY_MANAGEMENT_REASON[facts.key_management], "key_management")


def ai_training(facts: VariantFacts) -> Finding:
    criterion = "KI-Training mit Kundendaten"
    fact = "ai_training_on_customer_data"
    if facts.ai_training is AiTraining.UNBEKANNT:
        return gap(
            criterion,
            1,
            MAX_LEVEL,
            "Ob Kundendaten für KI-Training genutzt werden, ist nicht belegt.",
            fact,
        )
    ceiling, reason = AI_TRAINING[facts.ai_training]
    return known(criterion, ceiling, reason, fact)


# --- SOV-4 Operativ --------------------------------------------------------------------

OPERATIONS_LOCATION = {
    OperationsLocation.NUR_EU: (4, "Betrieb und Support erfolgen ausschließlich aus der EU."),
    OperationsLocation.EU_MIT_AUSNAHMEN: (
        2,
        "Betrieb und Support erfolgen aus der EU, mit Ausnahmen außerhalb.",
    ),
    OperationsLocation.WELTWEIT: (1, "Betrieb und Support erfolgen weltweit."),
}

DATA_EXPORT = {
    DataExport.OFFENE_FORMATE: (4, "Die Daten lassen sich in offenen Formaten exportieren."),
    DataExport.PROPRIETAER: (2, "Der Export ist nur in einem Format des Anbieters möglich."),
    DataExport.KEIN_EXPORT: (1, "Ein Export der Daten ist nicht vorgesehen."),
}


def operational(facts: VariantFacts, today: date) -> list[Finding]:
    return [
        operations_location(facts),
        data_export(facts),
        critical_non_eu_dependency(facts, "Betrieb ohne Nicht-EU-Zulieferer", ceiling=2),
    ]


def operations_location(facts: VariantFacts) -> Finding:
    criterion = "Ort von Betrieb und Support"
    if facts.operations_location is OperationsLocation.UNBEKANNT:
        return gap(
            criterion,
            1,
            MAX_LEVEL,
            "Von wo aus betrieben und Support geleistet wird, ist nicht belegt.",
            "operations_location",
        )
    ceiling, reason = OPERATIONS_LOCATION[facts.operations_location]
    return known(criterion, ceiling, reason, "operations_location")


def data_export(facts: VariantFacts) -> Finding:
    criterion = "Wechselfähigkeit"
    if facts.data_export is DataExport.UNBEKANNT:
        return gap(
            criterion,
            1,
            MAX_LEVEL,
            "Ob ein Export der Daten möglich ist, ist nicht belegt.",
            "data_export",
        )
    ceiling, reason = DATA_EXPORT[facts.data_export]
    return known(criterion, ceiling, reason, "data_export")


# --- SOV-5 Lieferkette -----------------------------------------------------------------


def supply_chain(facts: VariantFacts, today: date) -> list[Finding]:
    return [technology_origin(facts, "Herkunft der Technologie"), dependencies(facts)]


def technology_origin(facts: VariantFacts, criterion: str) -> Finding:
    ceiling = origin_ceiling(facts)
    label = JURISDICTION_LABEL[facts.provider_jurisdiction]
    if facts.provider_jurisdiction is EU:
        reason = "Die Technologie stammt von einem Anbieter unter EU-Kontrolle."
    elif facts.has_eu_operating_company:
        reason = (
            f"Die Technologie stammt von einem Anbieter außerhalb der EU ({label}), "
            "betrieben wird sie von einer Gesellschaft mit Sitz in der EU."
        )
    else:
        reason = f"Die Technologie stammt von einem Anbieter außerhalb der EU ({label})."
    return known(criterion, ceiling, reason, "ultimate_parent")


def dependencies(facts: VariantFacts) -> Finding:
    criterion = "Zulieferer außerhalb der EU"
    non_eu = [dependency for dependency in facts.dependencies if dependency.jurisdiction is not EU]
    names = ", ".join(sorted({dependency.supplier for dependency in non_eu}))
    if any(dependency.critical for dependency in non_eu):
        return known(
            criterion,
            2,
            f"Mindestens ein kritischer Zulieferer sitzt außerhalb der EU ({names}).",
            "dependencies",
        )
    known_ceiling = 3 if non_eu else 4
    known_part = (
        f"Einzelne, nicht kritische Zulieferer sitzen außerhalb der EU ({names})." if non_eu else ""
    )
    if facts.dependencies_complete:
        return known(
            criterion,
            known_ceiling,
            known_part or "Kein Zulieferer außerhalb der EU.",
            "dependencies",
        )
    return gap(
        criterion,
        2,
        known_ceiling,
        (known_part + " " if known_part else "") + "Die Zulieferer sind nicht vollständig geprüft. "
        "Ein kritischer Zulieferer außerhalb der EU ist nicht auszuschließen.",
        "dependencies",
    )


# --- SOV-6 Technologie -----------------------------------------------------------------


def technology(facts: VariantFacts, today: date) -> list[Finding]:
    return [
        openness(facts),
        critical_non_eu_dependency(
            facts,
            "Technologie von Nicht-EU-Zulieferern",
            ceiling=2,
            kinds=frozenset({DependencyKind.TECHNOLOGIE}),
        ),
    ]


def openness_ceiling(value: Openness, origin: int) -> int:
    """Offener Quellcode macht unabhängig von der Herkunft. Sonst zählt die Herkunft mit."""
    if value is Openness.OPEN_SOURCE:
        return 4
    if value is Openness.OFFENE_STANDARDS:
        return max(origin, 2)
    # Proprietär: Auch bei EU-Herkunft bleibt die Bindung an einen Hersteller
    return min(origin, 3)


def openness(facts: VariantFacts) -> Finding:
    criterion = "Offenheit der Technologie"
    origin = origin_ceiling(facts)
    if facts.openness is Openness.UNBEKANNT:
        return gap(
            criterion,
            openness_ceiling(Openness.PROPRIETAER, origin),
            MAX_LEVEL,
            "Die Offenheit der Technologie ist nicht belegt. "
            "Angenommen wird eine proprietäre Lösung.",
            "openness",
        )
    reasons = {
        Openness.OPEN_SOURCE: (
            "Der Quellcode ist offen und lässt sich prüfen, ändern und selbst betreiben."
        ),
        Openness.OFFENE_STANDARDS: "Die Lösung nutzt offene Standards und Schnittstellen.",
        Openness.PROPRIETAER: (
            "Die Lösung ist proprietär, der Kunde ist an den Hersteller gebunden."
        ),
    }
    return known(
        criterion, openness_ceiling(facts.openness, origin), reasons[facts.openness], "openness"
    )


# --- SOV-7 Sicherheit und Compliance ---------------------------------------------------


def security(facts: VariantFacts, today: date) -> list[Finding]:
    return [control(facts, "Sicherheitsbetrieb unter EU-Recht"), certificates(facts, today)]


def certificates(facts: VariantFacts, today: date) -> Finding:
    criterion = "Zertifikate"
    valid = {
        certificate.slug
        for certificate in facts.certificates
        if certificate.valid_until is None or certificate.valid_until >= today
    }
    expired = sorted({certificate.slug for certificate in facts.certificates} - valid)
    note = f" Abgelaufen: {', '.join(expired)}." if expired else ""
    if valid & EU_CERTIFICATES:
        return known(
            criterion,
            4,
            "Ein in der EU anerkanntes Testat liegt vor (BSI C5)." + note,
            "certificates",
        )
    if valid & INTERNATIONAL_CERTIFICATES:
        return known(
            criterion,
            3,
            "Ein international anerkanntes Zertifikat liegt vor (ISO/IEC 27001), "
            "aber kein in der EU anerkanntes Testat." + note,
            "certificates",
        )
    return gap(
        criterion, 1, MAX_LEVEL, "Ein gültiges Zertifikat ist nicht belegt." + note, "certificates"
    )


# --- SOV-8 Umwelt ----------------------------------------------------------------------


def environmental(facts: VariantFacts, today: date) -> list[Finding]:
    criterion = "Erneuerbare Energie"
    if facts.renewable_energy is RenewableEnergy.NACHGEWIESEN:
        return [
            known(
                criterion,
                4,
                "Der Betrieb mit erneuerbarer Energie ist nachgewiesen.",
                "renewable_energy",
            )
        ]
    if facts.renewable_energy is RenewableEnergy.ZUGESAGT:
        return [
            known(
                criterion,
                2,
                "Erneuerbare Energie ist zugesagt, ein Nachweis liegt nicht vor.",
                "renewable_energy",
            )
        ]
    return [
        gap(
            criterion,
            0,
            MAX_LEVEL,
            "Zur Energieversorgung gibt es keine Angabe.",
            "renewable_energy",
        )
    ]


RULES: dict[Objective, Callable[[VariantFacts, date], list[Finding]]] = {
    Objective.STRATEGISCH: strategic,
    Objective.RECHTLICH: legal,
    Objective.DATEN_KI: data_and_ai,
    Objective.OPERATIV: operational,
    Objective.LIEFERKETTE: supply_chain,
    Objective.TECHNOLOGIE: technology,
    Objective.SICHERHEIT: security,
    Objective.UMWELT: environmental,
}
