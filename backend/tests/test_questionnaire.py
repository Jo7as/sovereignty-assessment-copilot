import copy

import pytest
from pydantic import ValidationError

from app.questionnaire import (
    PROFILE_SECTION,
    Questionnaire,
    QuestionType,
    load_questionnaire,
)

URL = "https://beispiel.example/gesetz"
MINIMAL = {
    "version": 1,
    "laws": [{"key": "DORA", "title": "DORA", "url": URL}],
    "sections": [{"key": "profil", "title": "Unternehmen"}, {"key": "exit", "title": "Exit"}],
    "dimensions": [{"key": "EXIT", "label": "Exit und Ersetzbarkeit"}],
    "questions": [
        {"key": "employees", "section": "profil", "type": "NUMBER", "text": "Beschäftigte?"},
        {
            "key": "exit_strategy",
            "section": "exit",
            "type": "SINGLE",
            "dimension": "EXIT",
            "text": "Exit-Strategie?",
            "options": [
                {"value": "NEIN", "label": "Nein", "level": 0},
                {"value": "JA", "label": "Ja", "level": 4},
                {"value": "UNBEKANNT", "label": "Weiß nicht", "level": 0},
            ],
            "basis": [
                {
                    "law": "DORA",
                    "article": "Art. 28 Abs. 8",
                    "source": URL,
                    "quote": "richten Finanzunternehmen Ausstiegsstrategien ein.",
                    "retrieved": "2026-10-19",
                }
            ],
        },
    ],
}


def variant(change) -> dict:
    data = copy.deepcopy(MINIMAL)
    change(data)
    return data


def exit_question(data: dict) -> dict:
    return data["questions"][1]


def test_questionnaire_file_is_valid():
    questionnaire = load_questionnaire()

    assert 20 <= len(questionnaire.questions) <= 30


def test_every_dimension_has_at_least_two_questions():
    questionnaire = load_questionnaire()

    for dimension in questionnaire.dimensions:
        count = sum(question.dimension == dimension.key for question in questionnaire.questions)
        assert count >= 2, dimension.key


def test_profile_determines_the_regulation():
    questionnaire = load_questionnaire()

    profile = [q.key for q in questionnaire.questions if q.section == PROFILE_SECTION]

    assert profile == ["sector", "employees", "annual_turnover", "balance_sheet_total"]
    assert questionnaire.question("employees").type is QuestionType.NUMBER


def test_every_sector_except_other_falls_under_dora_or_nis2():
    sector = load_questionnaire().question("sector")

    unregulated = [o.value for o in sector.options if not o.dora and o.nis2_annex is None]

    assert unregulated == ["ANDERER"]


def test_banks_fall_under_dora_and_nis2_annex_one():
    """Kreditinstitute stehen in Anhang I der NIS2, DORA geht ihr aber als Spezialgesetz vor."""
    sector = load_questionnaire().question("sector")

    bank = next(option for option in sector.options if option.value == "KREDITINSTITUT")

    assert (bank.dora, bank.nis2_annex) == (True, "I")


def test_minimal_questionnaire_is_valid():
    assert Questionnaire.model_validate(MINIMAL).question("exit_strategy").is_maturity


def test_unknown_field_is_rejected():
    with pytest.raises(ValidationError, match="extra"):
        Questionnaire.model_validate(variant(lambda d: exit_question(d).update(hint="x")))


def test_maturity_question_needs_unknown_answer():
    def drop_unknown(data):
        exit_question(data)["options"].pop()

    with pytest.raises(ValidationError, match="Weiß nicht"):
        Questionnaire.model_validate(variant(drop_unknown))


def test_unknown_answer_counts_like_no():
    def raise_unknown(data):
        exit_question(data)["options"][2]["level"] = 2

    with pytest.raises(ValidationError, match="Weiß nicht"):
        Questionnaire.model_validate(variant(raise_unknown))


def test_maturity_levels_span_zero_to_four():
    def cap_at_three(data):
        exit_question(data)["options"][1]["level"] = 3

    with pytest.raises(ValidationError, match="von 0 bis 4"):
        Questionnaire.model_validate(variant(cap_at_three))


def test_every_maturity_answer_needs_a_level():
    def drop_level(data):
        del exit_question(data)["options"][1]["level"]

    with pytest.raises(ValidationError, match="Stufe"):
        Questionnaire.model_validate(variant(drop_level))


def test_level_without_dimension_is_rejected():
    def drop_dimension(data):
        del exit_question(data)["dimension"]

    with pytest.raises(ValidationError, match="ohne Handlungsfeld"):
        Questionnaire.model_validate(variant(drop_dimension))


def test_profile_question_never_counts_towards_maturity():
    with pytest.raises(ValidationError, match="Profilfragen"):
        Questionnaire.model_validate(variant(lambda d: exit_question(d).update(section="profil")))


def test_unknown_section_is_rejected():
    with pytest.raises(ValidationError, match="Abschnitt"):
        Questionnaire.model_validate(variant(lambda d: exit_question(d).update(section="ziele")))


def test_unknown_dimension_is_rejected():
    with pytest.raises(ValidationError, match="Handlungsfeld"):
        Questionnaire.model_validate(variant(lambda d: exit_question(d).update(dimension="X")))


def test_basis_must_cite_the_registered_law_text():
    def other_source(data):
        exit_question(data)["basis"][0]["source"] = "https://anderswo.example"

    with pytest.raises(ValidationError, match="Quelle passt nicht"):
        Questionnaire.model_validate(variant(other_source))


def test_duplicate_question_key_is_rejected():
    def duplicate(data):
        data["questions"].append(copy.deepcopy(data["questions"][0]))

    with pytest.raises(ValidationError, match="Frage doppelt"):
        Questionnaire.model_validate(variant(duplicate))


def test_duplicate_answer_value_is_rejected():
    def duplicate(data):
        exit_question(data)["options"][1]["value"] = "NEIN"

    with pytest.raises(ValidationError, match="doppelt"):
        Questionnaire.model_validate(variant(duplicate))


def test_number_question_has_no_options():
    def add_options(data):
        data["questions"][0]["options"] = copy.deepcopy(exit_question(data)["options"])

    with pytest.raises(ValidationError, match="Zahlenfrage"):
        Questionnaire.model_validate(variant(add_options))
