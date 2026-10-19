"""Antworten prüfen und den Reifegrad je Handlungsfeld berechnen.

Der Reifegrad eines Handlungsfelds ist der Mittelwert der Stufen seiner Fragen. Anders als
bei den Anbietern zählt nicht die schwächste Antwort: Der Reifegrad beschreibt, wie weit
ein Unternehmen insgesamt ist. Bei der Souveränität eines Dienstes entscheidet dagegen das
schwächste Glied, weil eine einzige Lücke den Zugriff von außen ermöglicht.

Wie bei den Anbietern gibt es zwei Werte: Der gesicherte zählt offene Fragen mit 0, der
mögliche mit 4. Liegen beide auseinander, fehlen Antworten.
"""

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.questionnaire import MAX_LEVEL, Question, Questionnaire, QuestionType

type AnswerValue = str | Decimal
MAX_NUMBER = Decimal(
    "1e12"
)  # passt in die Spalte number_value (14 Stellen, davon 2 nach dem Komma)


@dataclass(frozen=True)
class AnswerProblem:
    question: str
    message: str


@dataclass(frozen=True)
class DimensionMaturity:
    key: str
    label: str
    secured: float
    possible: float
    answered: int
    total: int


@dataclass(frozen=True)
class Maturity:
    dimensions: tuple[DimensionMaturity, ...]
    secured: float
    possible: float


def check_answers(
    questionnaire: Questionnaire, answers: dict[str, object]
) -> tuple[dict[str, AnswerValue | None], list[AnswerProblem]]:
    """Prüft rohe Antworten aus einer Anfrage. `None` heißt: Antwort löschen.

    Gibt die umgewandelten Antworten und alle Probleme auf einmal zurück, damit sich die
    Eingabe in einem Durchgang korrigieren lässt.
    """
    questions = {question.key: question for question in questionnaire.questions}
    checked: dict[str, AnswerValue | None] = {}
    problems: list[AnswerProblem] = []
    for key, raw in answers.items():
        question = questions.get(key)
        if question is None:
            problems.append(AnswerProblem(key, "Unbekannte Frage"))
            continue
        if raw is None:
            checked[key] = None
            continue
        value, message = _convert(question, raw)
        if message:
            problems.append(AnswerProblem(key, message))
        else:
            checked[key] = value
    return checked, problems


def _convert(question: Question, raw: object) -> tuple[AnswerValue | None, str | None]:
    if question.type is QuestionType.SINGLE:
        allowed = [option.value for option in question.options]
        if not isinstance(raw, str) or raw not in allowed:
            return None, f"Erlaubt sind: {', '.join(allowed)}"
        return raw, None
    # bool ist in Python eine Zahl, als Antwort aber ein Fehler
    if isinstance(raw, bool) or not isinstance(raw, int | float) or not math.isfinite(raw):
        return None, "Erwartet wird eine Zahl"
    number = Decimal(str(raw))
    if number < 0 or number >= MAX_NUMBER:
        return None, "Die Zahl muss zwischen 0 und 1 Billion liegen"
    return number, None


def maturity(questionnaire: Questionnaire, answers: dict[str, AnswerValue]) -> Maturity:
    dimensions, secured, possible = [], [], []
    for dimension in questionnaire.dimensions:
        questions = [q for q in questionnaire.questions if q.dimension == dimension.key]
        levels = [_level(question, answers.get(question.key)) for question in questions]
        known = [level for level in levels if level is not None]
        missing = len(levels) - len(known)
        secured.append(_mean([*known, *[0] * missing]))
        possible.append(_mean([*known, *[MAX_LEVEL] * missing]))
        dimensions.append(
            DimensionMaturity(
                key=dimension.key,
                label=dimension.label,
                secured=_round(secured[-1]),
                possible=_round(possible[-1]),
                answered=len(known),
                total=len(levels),
            )
        )
    # Gerundet wird erst hier, sonst würde der Gesamtwert aus gerundeten Werten gemittelt
    return Maturity(
        dimensions=tuple(dimensions),
        secured=_round(_mean(secured)),
        possible=_round(_mean(possible)),
    )


def _level(question: Question, value: AnswerValue | None) -> int | None:
    option = next((option for option in question.options if option.value == value), None)
    return option.level if option else None


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _round(value: float) -> float:
    """Kaufmännisch auf eine Stelle: 0,25 wird 0,3. Pythons round() ergäbe 0,2."""
    return float(Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
