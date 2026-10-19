import pytest
from fastapi.testclient import TestClient

from app.db import get_session
from app.main import app
from app.models import AssessmentAnswer

client = TestClient(app)


@pytest.fixture(autouse=True)
def database(session):
    app.dependency_overrides[get_session] = lambda: session
    yield
    app.dependency_overrides.clear()


def create(name: str = "Musterbank AG") -> dict:
    response = client.post("/assessments", json={"name": name})
    assert response.status_code == 201
    return response.json()


def put_answers(assessment_id: int, answers: dict):
    return client.put(f"/assessments/{assessment_id}/answers", json={"answers": answers})


def test_questionnaire_lists_questions_with_legal_basis():
    body = client.get("/questionnaire").json()

    exit_strategy = next(q for q in body["questions"] if q["key"] == "exit_strategy")

    assert len(body["questions"]) == 27
    assert exit_strategy["basis"][0]["article"] == "Art. 28 Abs. 8"
    assert exit_strategy["basis"][0]["retrieved"] == "2026-10-19"


def test_new_assessment_starts_empty():
    body = create("  Musterbank AG  ")

    assert body["name"] == "Musterbank AG"
    assert body["questionnaire_version"] == 1
    assert body["answers"] == {}
    assert body["progress"] == {"answered": 0, "total": 27}
    assert (body["maturity"]["secured"], body["maturity"]["possible"]) == (0.0, 4.0)


@pytest.mark.parametrize("payload", [{"name": "   "}, {"name": "x" * 201}, {}])
def test_assessment_needs_a_name(payload):
    response = client.post("/assessments", json=payload)

    error = response.json()["error"]
    assert response.status_code == 422
    assert error["code"] == "INVALID_REQUEST"
    assert error["details"][0]["location"].startswith("body")


def test_answers_are_saved_and_returned():
    assessment = create()

    response = put_answers(
        assessment["id"], {"sector": "KREDITINSTITUT", "employees": 180, "exit_strategy": "ALLE"}
    )

    stored = client.get(f"/assessments/{assessment['id']}").json()
    assert response.status_code == 200
    assert stored["answers"] == {
        "sector": "KREDITINSTITUT",
        "employees": 180,
        "exit_strategy": "ALLE",
    }
    assert stored["progress"]["answered"] == 3
    exit_dimension = next(d for d in stored["maturity"]["dimensions"] if d["key"] == "EXIT")
    assert (exit_dimension["secured"], exit_dimension["answered"]) == (0.6, 1)


def test_decimal_numbers_keep_their_value():
    assessment = create()

    body = put_answers(assessment["id"], {"annual_turnover": 42.5}).json()

    assert body["answers"] == {"annual_turnover": 42.5}


def test_later_answers_change_only_what_they_name():
    assessment = create()
    put_answers(assessment["id"], {"sector": "KREDITINSTITUT", "exit_strategy": "NEIN"})

    body = put_answers(assessment["id"], {"exit_strategy": "ALLE_UEBERPRUEFT"}).json()

    assert body["answers"] == {"sector": "KREDITINSTITUT", "exit_strategy": "ALLE_UEBERPRUEFT"}


def test_changing_an_answer_does_not_create_a_second_row(session):
    assessment = create()
    put_answers(assessment["id"], {"employees": 180})

    put_answers(assessment["id"], {"employees": 200})

    rows = session.query(AssessmentAnswer).filter_by(assessment_id=assessment["id"]).all()
    assert [(row.question_key, row.number_value) for row in rows] == [("employees", 200)]


def test_null_deletes_an_answer():
    assessment = create()
    put_answers(assessment["id"], {"sector": "KREDITINSTITUT", "employees": 180})

    body = put_answers(assessment["id"], {"sector": None}).json()

    assert body["answers"] == {"employees": 180}


def test_one_invalid_answer_saves_nothing():
    assessment = create()

    response = put_answers(
        assessment["id"], {"sector": "KREDITINSTITUT", "employees": "viele", "farbe": "BLAU"}
    )

    error = response.json()["error"]
    assert response.status_code == 422
    assert error["code"] == "INVALID_ANSWERS"
    assert error["message"].startswith("2 Antworten sind ungültig")
    assert [problem["question"] for problem in error["details"]] == ["employees", "farbe"]
    assert client.get(f"/assessments/{assessment['id']}").json()["answers"] == {}


def test_empty_answers_are_rejected():
    assessment = create()

    response = put_answers(assessment["id"], {})

    assert response.json()["error"]["code"] == "INVALID_REQUEST"


def test_unknown_assessment_gives_404():
    assert client.get("/assessments/999999").json()["error"]["code"] == "ASSESSMENT_NOT_FOUND"
    assert put_answers(999999, {"sector": "ANDERER"}).status_code == 404


def test_demo_route_is_not_mistaken_for_an_assessment_id():
    response = client.get("/assessments/demo")

    assert response.status_code == 200
    assert response.json()["inventory"]["name"] == "Musterbank AG"
