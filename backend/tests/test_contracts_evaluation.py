"""Messung der Vertragsanalyse: Vergleich mit der Musterlösung und Kennzahlen."""

from app.contracts import DocumentType
from app.contracts.evaluation import score, summarize
from app.contracts.pipeline import Evidence, FieldState, merge

AVV = [DocumentType.AVV]

GOLD = {
    "data_location": {
        "value": "EU_ZUGESICHERT",
        "also_correct": ["EU_WAEHLBAR"],
        "evidence": [{"page": 3, "quote": "…"}],
    },
    "operations_location": {"value": "NUR_EU", "evidence": [{"page": 5, "quote": "…"}]},
    "key_management": {"value": "NICHT_GEFUNDEN"},
    "data_export": {"value": "NICHT_GEFUNDEN"},
}


def scored(*findings):
    return {item.field: item for item in score("test", GOLD, merge(GOLD, findings, AVV))}


def test_right_value_on_a_gold_page_is_correct():
    result = scored(Evidence("data_location", "EU_ZUGESICHERT", "…", 3))["data_location"]

    assert result.correct and result.page_correct


def test_right_value_on_another_page_counts_for_the_value_not_the_page():
    result = scored(Evidence("data_location", "EU_ZUGESICHERT", "…", 9))["data_location"]

    assert result.correct and not result.page_correct


def test_also_correct_value_counts():
    assert scored(Evidence("data_location", "EU_WAEHLBAR", "…", 3))["data_location"].correct


def test_contradiction_is_correct_when_gold_accepts_every_value():
    result = scored(
        Evidence("data_location", "EU_ZUGESICHERT", "…", 3),
        Evidence("data_location", "EU_WAEHLBAR", "…", 31),
    )["data_location"]

    assert result.state == FieldState.UNKLAR
    assert result.correct


def test_contradiction_with_a_wrong_value_is_wrong():
    result = scored(
        Evidence("data_location", "EU_ZUGESICHERT", "…", 3),
        Evidence("data_location", "NICHT_EU", "…", 30),
    )["data_location"]

    assert not result.correct


def test_not_found_is_correct_only_when_gold_says_so():
    result = scored()

    assert result["key_management"].correct
    assert not result["operations_location"].correct


def test_summary_counts_precision_recall_and_false_not_found():
    scores = score(
        "test",
        GOLD,
        merge(
            GOLD,
            [
                Evidence("data_location", "EU_ZUGESICHERT", "…", 3),  # richtig
                Evidence("data_export", "KEIN_EXPORT", "…", 7),  # erfunden
            ],
            AVV,
        ),
    )

    summary = summarize(scores)

    assert summary.fields == 4
    assert summary.agreement == 0.5  # data_location, key_management
    assert summary.precision == 0.5  # 1 von 2 Angaben
    assert summary.page_precision == 0.5
    assert summary.recall == 0.5  # data_location von 2 Angaben der Musterlösung
    assert summary.false_not_found == 0.5  # operations_location übersehen


def test_check_is_scored_by_its_judged_verdict():
    gold = {"dsgvo_28_3_g": {"value": "TEILWEISE", "evidence": [{"page": 6, "quote": "…"}]}}
    deletion_only = Evidence("dsgvo_28_3_g.loeschung", "BELEGT", "…", 6)

    (result,) = score("test", gold, merge(gold, [deletion_only], AVV))

    assert result.values == ("TEILWEISE",)
    assert result.correct and result.page_correct
