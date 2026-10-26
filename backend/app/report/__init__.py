"""Bausteine des PDF-Berichts aus einem bewerteten IT-Bestand.

Die Sätze der Management Summary entstehen aus festen Regeln, nicht aus einer KI: Jeder Satz
lässt sich auf eine Zahl der Bewertung zurückführen und ist bei gleichen Daten gleich.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.roadmap import TOPICS

# Namen wie in der Oberfläche (frontend/src/lib/labels.ts), in der Reihenfolge des Rahmenwerks
OBJECTIVES = {
    "STRATEGISCH": "Strategisch",
    "RECHTLICH": "Rechtlich",
    "DATEN_KI": "Daten und KI",
    "OPERATIV": "Operativ",
    "LIEFERKETTE": "Lieferkette",
    "TECHNOLOGIE": "Technologie",
    "SICHERHEIT": "Sicherheit und Compliance",
    "UMWELT": "Umwelt",
}
OUTSIDE_OVERALL = {"UMWELT"}  # zählt nur im Souveränitätswert, nicht in der Gesamtstufe
INSIDE_EU = {"EU_EWR", "ANGEMESSEN"}  # wie im Schnellcheck
WEIGHT = {"GERING": 1, "MITTEL": 2, "HOCH": 3}  # wie in Roadmap und Gesamtwert
# Bei gleicher Punktzahl: Recht außerhalb der EU wiegt schwerer
JURISDICTION_RANK = {"USA": 0, "DRITTSTAAT": 1, "ANGEMESSEN": 2, "EU_EWR": 3}
ENTITY_CLASS = {"WESENTLICH": "wesentliche Einrichtung", "WICHTIG": "wichtige Einrichtung"}

TOP_RISKS = 3
# Risiken im Detail: hohe und mittlere Kritikalität, gesichert höchstens Stufe 1
RISK_CRITICALITY = {"HOCH", "MITTEL"}
RISK_LEVEL = 1
MAX_REASONS = 2
MAX_OPEN_FACTS = 4


def build_report(
    inventory: dict, jurisdictions: dict[str, str], regulation: dict | None = None
) -> dict:
    """Kernaussage, Kennzahlen, Rechtslage, Top-Risiken, Maßnahmen je Welle und Quellen.

    `inventory` ist das Ergebnis der Bewertung eines IT-Bestands, `jurisdictions` der
    maßgebliche Rechtsraum je Dienst, `regulation` die Rechtslage aus dem Fragebogen.
    """
    services = inventory["services"]
    outside = [s for s in services if jurisdictions.get(s["service"]) not in INSIDE_EU]
    groups = _risk_groups(services, jurisdictions)
    return {
        "headline": _headline(len(services), len(outside)),
        "assessed": len(services),
        "outside_eu": len(outside),
        "key_figures": _key_figures(inventory.get("portfolio")) + _group_figure(groups),
        "regulation": _regulation(regulation),
        "top_risks": [
            _risk(s, jurisdictions) for s in _ranked(services, jurisdictions)[:TOP_RISKS]
        ],
        "risk_groups": groups,
        "actions": _actions(inventory["roadmap"]["waves"]),
        "sources": _sources(services),
    }


def _headline(assessed: int, outside: int) -> str:
    if assessed == 0:
        return "Im IT-Bestand wurde noch kein Dienst bewertet."
    return (
        f"{outside} von {assessed} bewerteten Diensten unterliegen dem Recht eines Staates "
        "außerhalb der EU."
    )


def _decimal(value: float) -> str:
    """Eine Nachkommastelle, kaufmännisch gerundet und mit Komma: 0,39 → „0,4“."""
    rounded = Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return str(rounded).replace(".", ",")


def _whole(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _key_figures(portfolio: dict | None) -> list[str]:
    if not portfolio:
        return []
    figures = [
        f"Gesamtstufe {_decimal(portfolio['level'])} von 4, möglich "
        f"{_decimal(portfolio['potential'])}. Gesichert heißt: Fehlende Angaben zählen wie der "
        "ungünstigste Fall.",
        f"Souveränitätswert {_whole(portfolio['score'])} von 100, möglich "
        f"{_whole(portfolio['potential_score'])}, gewichtet nach Kritikalität der Dienste.",
    ]
    weakest = portfolio.get("weakest_critical_services") or []
    if weakest:
        figures.append(
            f"{len(weakest)} hoch kritische Dienste stehen gesichert auf Stufe "
            f"{portfolio['weakest_critical_level']}."
        )
    return figures


def _group_figure(groups: dict) -> list[str]:
    structural, clarify = len(groups["structural"]), len(groups["clarify"])
    if not structural and not clarify:
        return []
    subject = "kritischer Dienst bleibt" if structural == 1 else "kritische Dienste bleiben"
    return [
        f"{structural} {subject} selbst im besten Fall bei Stufe 1 oder darunter, hier hilft nur "
        f"ein Wechsel. Bei {clarify} weiteren kann eine Nachfrage beim Anbieter die Stufe heben."
    ]


def _regulation(regulation: dict | None) -> str:
    open_text = (
        "Ob DORA und NIS2 gelten, ist offen, weil der Fragebogen dazu noch nicht beantwortet ist."
    )
    if regulation is None:
        return open_text
    dora, nis2 = regulation["dora"]["status"], regulation["nis2"]["status"]
    if dora == nis2 == "NICHT_BESTIMMBAR":
        return open_text
    parts = [
        {"GILT": "DORA gilt.", "GILT_NICHT": "DORA gilt nicht."}.get(
            dora, "Ob DORA gilt, ist offen."
        )
    ]
    entity = ENTITY_CLASS.get(regulation["nis2"].get("entity_class") or "")
    detail = f" ({entity})" if entity else ""
    if nis2 == "GILT" and dora == "GILT" and regulation.get("dora_precedes_nis2"):
        parts.append(f"NIS2 gilt ebenfalls{detail}, DORA geht als speziellere Regelung vor.")
    elif nis2 == "GILT":
        parts.append(f"NIS2 gilt{detail}.")
    elif nis2 == "GILT_NICHT":
        parts.append("NIS2 gilt nicht.")
    else:
        parts.append("Ob NIS2 gilt, ist offen.")
    return " ".join(parts)


def _ranked(services: list[dict], jurisdictions: dict[str, str]) -> list[dict]:
    """Kritikalität mal Abstand zur Höchststufe. Bei Gleichstand zuerst, wer selbst im besten
    Fall unten bleibt (strukturelles Risiko statt bloßer Lücke), dann Recht außerhalb der EU."""
    return sorted(
        services,
        key=lambda s: (
            -WEIGHT[s["criticality"]] * (4 - s["level"]),
            -WEIGHT[s["criticality"]],
            s["potential"],
            JURISDICTION_RANK.get(jurisdictions.get(s["service"], ""), 0),
            s["name"].casefold(),
        ),
    )


def _risk(service: dict, jurisdictions: dict[str, str]) -> dict:
    """Ein Risiko mit Begründung: der schwächste Zielbereich und was ihn unten hält."""
    counted = {
        key: value for key, value in service["objectives"].items() if key not in OUTSIDE_OVERALL
    }
    lowest = min((value["level"] for value in counted.values()), default=service["level"])
    weakest = [key for key in OBJECTIVES if key in counted and counted[key]["level"] == lowest]
    reasons: list[str] = []
    binding: list[str] = []  # Merkmale, die den schwächsten Bereich unten halten
    for key in weakest:
        for finding in counted[key]["findings"]:
            if finding["ceiling"] != lowest:
                continue
            if finding["reason"] not in reasons:
                reasons.append(finding["reason"])
            if finding.get("fact") in service["gaps"] and finding["fact"] not in binding:
                binding.append(finding["fact"])
    open_facts = binding + [gap for gap in service["gaps"] if gap not in binding]
    return {
        **_identity(service, jurisdictions),
        "cap": _cap(service, counted),
        "cap_reason": _cap_reason(service, counted),
        "weakest": [OBJECTIVES[key] for key in weakest],
        "reasons": reasons[:MAX_REASONS],
        "open_facts": [TOPICS.get(gap, gap) for gap in open_facts][:MAX_OPEN_FACTS],
    }


def _identity(service: dict, jurisdictions: dict[str, str]) -> dict:
    return {
        "service": service["service"],
        "name": service["name"],
        "provider": service["provider"],
        "criticality": service["criticality"],
        "level": service["level"],
        "potential": service["potential"],
        "jurisdiction": jurisdictions.get(service["service"]),
    }


def _cap(service: dict, counted: dict) -> str | None:
    """Warum die Stufe selbst im besten Fall nicht höher geht, als ganzer Satz."""
    reason = _cap_reason(service, counted)
    if reason is None:
        return None
    return f"Selbst im besten Fall höchstens Stufe {service['potential']}: {reason}"


def _cap_reason(service: dict, counted: dict) -> str | None:
    """Das Kriterium, das auch im günstigsten Fall die Stufe begrenzt, etwa der Rechtsraum."""
    if service["potential"] >= 4:
        return None
    return next(
        (
            finding["reason"]
            for key in OBJECTIVES
            if key in counted
            for finding in counted[key]["findings"]
            if finding["potential"] == service["potential"]
        ),
        None,
    )


def _risk_groups(services: list[dict], jurisdictions: dict[str, str]) -> dict:
    """Strukturell: Selbst im besten Fall bleibt die Stufe bei 1 oder darunter, helfen kann nur
    ein Wechsel. Klärung: Es fehlen nur Angaben, eine Nachfrage beim Anbieter kann die Stufe
    heben. Beides für Dienste mit hoher oder mittlerer Kritikalität auf Stufe 0 oder 1."""
    relevant = [
        s
        for s in _ranked(services, jurisdictions)
        if s["criticality"] in RISK_CRITICALITY and s["level"] <= RISK_LEVEL
    ]
    return {
        "structural": [_risk(s, jurisdictions) for s in relevant if s["potential"] <= RISK_LEVEL],
        "clarify": [_risk(s, jurisdictions) for s in relevant if s["potential"] > RISK_LEVEL],
    }


def _actions(waves: list[dict]) -> list[dict]:
    """Je Welle der wichtigste Punkt und wie viele es insgesamt sind."""
    return [
        {
            "wave": wave["wave"],
            "title": wave["title"],
            "count": len(wave["items"]),
            "first": max(wave["items"], key=lambda item: item["priority"])["title"],
        }
        for wave in waves
        if wave["items"]
    ]


def _sources(services: list[dict]) -> list[dict]:
    """Jede Fundstelle einmal, mit allen Diensten, deren Bewertung sie stützt."""
    sources: dict[tuple[str, str], dict] = {}
    for service in services:
        for item in service["evidence"]:
            key = (item["source_url"], item["quote"])
            entry = sources.setdefault(
                key,
                {
                    "url": item["source_url"],
                    "quote": item["quote"],
                    "retrieved_at": item["retrieved_at"],
                    "services": [],
                },
            )
            if service["name"] not in entry["services"]:
                entry["services"].append(service["name"])
    return sorted(sources.values(), key=lambda entry: (entry["url"], entry["quote"]))
