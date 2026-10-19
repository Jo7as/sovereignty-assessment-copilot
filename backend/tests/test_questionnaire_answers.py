from decimal import Decimal

import pytest

from app.questionnaire import load_questionnaire
from app.questionnaire.answers import AnswerProblem, check_answers, maturity

QUESTIONNAIRE = load_questionnaire()
EXIT_QUESTIONS = [q.key for q in QUESTIONNAIRE.questions if q.dimension == "EXIT"]


def dimension(result, key: str):
    return next(item for item in result.dimensions if item.key == key)


def test_valid_answers_are_converted():
    checked, problems = check_answers(
        QUESTIONNAIRE, {"sector": "KREDITINSTITUT", "employees": 180, "annual_turnover": 42.5}
    )

    assert problems == []
    assert checked == {
        "sector": "KREDITINSTITUT",
        "employees": Decimal("180"),
        "annual_turnover": Decimal("42.5"),
    }


def test_none_deletes_an_answer():
    checked, problems = check_answers(QUESTIONNAIRE, {"sector": None})

    assert (checked, problems) == ({"sector": None}, [])


def test_unknown_question_is_reported():
    _, problems = check_answers(QUESTIONNAIRE, {"lieblingsfarbe": "BLAU"})

    assert problems == [AnswerProblem("lieblingsfarbe", "Unbekannte Frage")]


def test_answer_outside_the_options_names_the_allowed_values():
    _, problems = check_answers(QUESTIONNAIRE, {"exit_tested": "VIELLEICHT"})

    assert problems[0].question == "exit_tested"
    assert "NEIN, AM_TISCH, TECHNISCH, UNBEKANNT" in problems[0].message


@pytest.mark.parametrize("value", ["180", True, -1, float("nan"), float("inf"), 1e12, [180]])
def test_number_question_rejects_everything_but_a_plausible_number(value):
    _, problems = check_answers(QUESTIONNAIRE, {"employees": value})

    assert len(problems) == 1


def test_option_question_rejects_a_number():
    _, problems = check_answers(QUESTIONNAIRE, {"sector": 3})

    assert len(problems) == 1


def test_all_problems_are_reported_at_once():
    _, problems = check_answers(
        QUESTIONNAIRE, {"sector": "MOND", "employees": "viele", "exit_strategy": "ALLE"}
    )

    assert [problem.question for problem in problems] == ["sector", "employees"]


def test_without_answers_maturity_spans_zero_to_four():
    result = maturity(QUESTIONNAIRE, {})

    assert (result.secured, result.possible) == (0.0, 4.0)
    assert all(item.answered == 0 for item in result.dimensions)


def test_best_answers_everywhere_give_four():
    best = {
        question.key: max(question.options, key=lambda option: option.level).value
        for question in QUESTIONNAIRE.questions
        if question.is_maturity
    }

    result = maturity(QUESTIONNAIRE, best)

    assert (result.secured, result.possible) == (4.0, 4.0)


def test_maturity_is_the_mean_and_open_questions_count_zero_or_four():
    """Eine Antwort mit Stufe 3 bei fünf Exit-Fragen: gesichert 3/5, möglich (3+4·4)/5."""
    result = maturity(QUESTIONNAIRE, {"exit_strategy": "ALLE"})

    exit_dimension = dimension(result, "EXIT")

    assert len(EXIT_QUESTIONS) == 5
    assert (exit_dimension.secured, exit_dimension.possible) == (0.6, 3.8)
    assert (exit_dimension.answered, exit_dimension.total) == (1, 5)


def test_unknown_counts_as_answered_with_level_zero():
    result = maturity(QUESTIONNAIRE, dict.fromkeys(EXIT_QUESTIONS, "UNBEKANNT"))

    exit_dimension = dimension(result, "EXIT")

    assert (exit_dimension.secured, exit_dimension.possible, exit_dimension.answered) == (0, 0, 5)


def test_profile_answers_do_not_change_maturity():
    assert maturity(QUESTIONNAIRE, {"sector": "KREDITINSTITUT", "employees": Decimal(180)}) == (
        maturity(QUESTIONNAIRE, {})
    )


def test_values_are_rounded_half_up():
    """Eine Stufe 1 bei vier Fragen ist 0,25. Kaufmännisch gerundet 0,3, nicht 0,2."""
    result = maturity(QUESTIONNAIRE, {"management_oversight": "INFORMIERT"})

    assert dimension(result, "GOVERNANCE").secured == 0.3


def test_overall_value_is_averaged_before_rounding():
    """Ungerundet (0,25 + 0,2 + 0,25) / 5 = 0,14. Aus gerundeten Werten käme 0,16 heraus."""
    answers = dict.fromkeys(
        ["sovereignty_goals", "third_party_strategy", "business_impact_analysis"], "GEPLANT"
    )

    result = maturity(QUESTIONNAIRE, answers)

    assert [item.secured for item in result.dimensions] == [0.3, 0.2, 0.0, 0.3, 0.0]
    assert result.secured == 0.1
