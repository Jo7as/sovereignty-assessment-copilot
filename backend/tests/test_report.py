"""Bausteine des Berichts: Kernaussage, Top-Risiken, Maßnahmen je Welle, Quellenverzeichnis."""

from app.report import build_report


def service(slug, name, criticality, level, potential=4, objectives=None, gaps=(), evidence=()):
    return {
        "service": slug,
        "name": name,
        "provider": f"{name} Inc.",
        "criticality": criticality,
        "level": level,
        "potential": potential,
        "gaps": list(gaps),
        "objectives": objectives
        or {"RECHTLICH": {"level": level, "potential": potential, "findings": []}},
        "evidence": list(evidence),
    }


def finding(reason, ceiling, potential=None):
    potential = ceiling if potential is None else potential
    return {"criterion": "x", "ceiling": ceiling, "potential": potential, "reason": reason}


def inventory(services, waves=None, portfolio=None):
    return {
        "inventory": {
            "name": "bestand.xlsx",
            "entries": len(services),
            "assessed_on": "2026-10-25",
        },
        "services": services,
        "portfolio": portfolio
        or {"level": 0.4, "potential": 1.8, "score": 29.2, "potential_score": 68.1},
        "roadmap": {"waves": waves or [], "measures": [], "questions": []},
    }


def test_headline_counts_services_outside_the_eu():
    services = [
        service("m365", "Microsoft 365", "HOCH", 1),
        service("datev", "DATEV", "HOCH", 1),
        service("aws", "AWS", "MITTEL", 1),
    ]
    jurisdictions = {"m365": "USA", "datev": "EU_EWR", "aws": "USA"}

    report = build_report(inventory(services), jurisdictions)

    assert report["outside_eu"] == 2
    assert report["headline"] == (
        "2 von 3 bewerteten Diensten unterliegen dem Recht eines Staates außerhalb der EU."
    )


def test_adequacy_decision_counts_as_inside():
    report = build_report(inventory([service("x", "X", "HOCH", 1)]), {"x": "ANGEMESSEN"})

    assert report["outside_eu"] == 0


def test_key_figures_show_secured_and_possible_values():
    report = build_report(inventory([service("x", "X", "HOCH", 1)]), {"x": "USA"})

    assert "Gesamtstufe 0,4 von 4, möglich 1,8" in report["key_figures"][0]
    assert "Souveränitätswert 29 von 100, möglich 68" in report["key_figures"][1]


def test_top_risks_are_ranked_by_criticality_times_distance_to_the_top():
    services = [
        service("low", "Gering kritisch", "GERING", 0),  # 1 × 4 = 4
        service("mid", "Mittel kritisch", "MITTEL", 1),  # 2 × 3 = 6
        service("high", "Hoch kritisch", "HOCH", 2),  # 3 × 2 = 6, bei Gleichstand vorn
        service("top", "Sehr riskant", "HOCH", 0),  # 3 × 4 = 12
    ]

    report = build_report(inventory(services), {})

    assert [risk["name"] for risk in report["top_risks"]] == [
        "Sehr riskant",
        "Hoch kritisch",
        "Mittel kritisch",
    ]


def test_risk_names_the_weakest_objective_and_what_holds_it_down():
    objectives = {
        "RECHTLICH": {
            "level": 0,
            "potential": 3,
            "findings": [
                finding("Die Konzernmutter sitzt in den USA.", 0),
                finding("Vertragsrecht ist nicht belegt.", 1, 4),
            ],
        },
        "OPERATIV": {"level": 2, "potential": 4, "findings": [finding("egal", 2)]},
        "UMWELT": {"level": 0, "potential": 0, "findings": [finding("zählt nicht", 0)]},
    }
    risky = service("m365", "Microsoft 365", "HOCH", 0, 3, objectives, gaps=["data_location"])

    risk = build_report(inventory([risky]), {"m365": "USA"})["top_risks"][0]

    assert risk["weakest"] == ["Rechtlich"]  # Umwelt zählt nicht zur Gesamtstufe
    assert risk["reasons"] == ["Die Konzernmutter sitzt in den USA."]
    assert risk["open_facts"] == ["Datenstandort"]
    assert risk["jurisdiction"] == "USA"


def test_one_action_per_wave_with_the_number_of_items():
    waves = [
        {
            "wave": 1,
            "title": "Schnelle Erfolge (0 bis 6 Monate)",
            "items": [
                {"title": "Kernfrage an Avaloq klären", "priority": 12},
                {"title": "b", "priority": 9},
            ],
        },
        {"wave": 2, "title": "Mittelfristig (6 bis 18 Monate)", "items": []},
    ]

    report = build_report(inventory([service("x", "X", "HOCH", 1)], waves), {})

    assert report["actions"] == [
        {
            "wave": 1,
            "title": "Schnelle Erfolge (0 bis 6 Monate)",
            "count": 2,
            "first": "Kernfrage an Avaloq klären",
        }
    ]


def test_sources_are_listed_once_with_all_services_that_use_them():
    shared = {"source_url": "https://a.example", "quote": "Q", "retrieved_at": "2026-10-14"}
    other = {"source_url": "https://b.example", "quote": "R", "retrieved_at": "2026-10-15"}
    services = [
        service("x", "X", "HOCH", 1, evidence=[shared]),
        service("y", "Y", "HOCH", 1, evidence=[shared, other]),
    ]

    report = build_report(inventory(services), {})

    assert report["sources"] == [
        {
            "url": "https://a.example",
            "quote": "Q",
            "retrieved_at": "2026-10-14",
            "services": ["X", "Y"],
        },
        {"url": "https://b.example", "quote": "R", "retrieved_at": "2026-10-15", "services": ["Y"]},
    ]


def test_regulation_sentence_when_dora_applies():
    regulation = {
        "dora": {"status": "GILT"},
        "nis2": {"status": "GILT", "entity_class": "WICHTIG"},
        "dora_precedes_nis2": True,
    }

    report = build_report(inventory([service("x", "X", "HOCH", 1)]), {}, regulation)

    assert report["regulation"] == (
        "DORA gilt. NIS2 gilt ebenfalls (wichtige Einrichtung), "
        "DORA geht als speziellere Regelung vor."
    )


def test_regulation_is_open_without_questionnaire():
    report = build_report(inventory([service("x", "X", "HOCH", 1)]), {})

    assert report["regulation"] == (
        "Ob DORA und NIS2 gelten, ist offen, weil der Fragebogen dazu noch nicht beantwortet ist."
    )


def test_without_any_service_there_is_no_risk_and_no_headline_number():
    report = build_report(inventory([], portfolio=None) | {"portfolio": None}, {})

    assert report["top_risks"] == []
    assert report["headline"] == "Im IT-Bestand wurde noch kein Dienst bewertet."
    assert report["key_figures"] == []


def test_structural_risk_comes_before_a_mere_lack_of_information():
    """Gleiche Punktzahl: Wer selbst im besten Fall unten bleibt, ist das größere Risiko."""
    services = [
        service("eu", "A EU-Anbieter mit Lücken", "HOCH", 0, potential=4),
        service("us", "B US-Anbieter", "HOCH", 0, potential=1),
        service("ch", "C Schweizer Anbieter", "HOCH", 0, potential=1),
    ]
    jurisdictions = {"eu": "EU_EWR", "us": "USA", "ch": "ANGEMESSEN"}

    report = build_report(inventory(services), jurisdictions)

    assert [risk["service"] for risk in report["top_risks"]] == ["us", "ch", "eu"]


def test_open_facts_that_hold_down_the_weakest_objective_come_first():
    objectives = {
        "DATEN_KI": {
            "level": 0,
            "potential": 4,
            "findings": [{**finding("Datenstandort nicht belegt.", 0, 4), "fact": "data_location"}],
        },
        "OPERATIV": {"level": 2, "potential": 4, "findings": []},
    }
    risky = service(
        "x", "X", "HOCH", 0, 4, objectives, gaps=["certificates", "data_export", "data_location"]
    )

    risk = build_report(inventory([risky]), {})["top_risks"][0]

    assert risk["open_facts"] == ["Datenstandort", "Zertifikate", "Datenexport"]


def test_risk_explains_why_even_the_best_case_stays_low():
    objectives = {
        "RECHTLICH": {
            "level": 1,
            "potential": 1,
            "findings": [finding("Die Konzernmutter sitzt in den USA.", 1, 1)],
        },
        "DATEN_KI": {
            "level": 0,
            "potential": 4,
            "findings": [finding("Der Datenstandort ist nicht belegt.", 0, 4)],
        },
    }
    capped = service("cs", "CrowdStrike", "HOCH", 0, 1, objectives)
    open_only = service("eu", "EU-Anbieter", "HOCH", 0, 4)

    risks = build_report(inventory([capped, open_only]), {})["top_risks"]

    assert (
        risks[0]["cap"]
        == "Selbst im besten Fall höchstens Stufe 1: Die Konzernmutter sitzt in den USA."
    )
    assert risks[1]["cap"] is None
    assert risks[0]["cap_reason"] == "Die Konzernmutter sitzt in den USA."


def test_risks_are_split_into_structural_ones_and_open_questions():
    services = [
        service("us", "US-Dienst", "HOCH", 0, potential=1),
        service("eu", "EU-Dienst mit Lücken", "HOCH", 1, potential=4),
        service("mid", "Mittel, strukturell", "MITTEL", 1, potential=1),
        service("ok", "Schon gut", "HOCH", 3, potential=4),
        service("low", "Gering kritisch", "GERING", 0, potential=1),
    ]

    groups = build_report(inventory(services), {"us": "USA"})["risk_groups"]

    assert [item["name"] for item in groups["structural"]] == ["US-Dienst", "Mittel, strukturell"]
    assert [item["name"] for item in groups["clarify"]] == ["EU-Dienst mit Lücken"]
    assert groups["structural"][0]["jurisdiction"] == "USA"


def test_key_figures_count_structural_risks_and_open_questions():
    services = [
        service("us", "US-Dienst", "HOCH", 0, potential=1),
        service("eu", "EU-Dienst mit Lücken", "MITTEL", 1, potential=4),
    ]

    figures = build_report(inventory(services), {})["key_figures"]

    assert figures[-1] == (
        "1 kritischer Dienst bleibt selbst im besten Fall bei Stufe 1 oder darunter, hier hilft "
        "nur ein Wechsel. Bei 1 weiteren kann eine Nachfrage beim Anbieter die Stufe heben."
    )
