"""Fragebogen des Assessments, definiert in data/questionnaire.yaml.

Das Schema prüft beim Laden, was sich an der Datei prüfen lässt: Verweise auf Abschnitte,
Handlungsfelder und Rechtsquellen, eindeutige Schlüssel und vollständige Reifegrade. Ob
die Fundstellen im Gesetzestext stehen, prüft scripts/verify_evidence.py.
"""

import datetime
from enum import auto
from functools import cache
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.config import PROJECT_ROOT
from app.models.enums import Values

QUESTIONNAIRE_FILE = PROJECT_ROOT / "data" / "questionnaire.yaml"
PROFILE_SECTION = "profil"
UNKNOWN = "UNBEKANNT"
MAX_LEVEL = 4


class QuestionType(Values):
    SINGLE = auto()
    NUMBER = auto()


class Model(BaseModel):
    # Unbekannte Felder sind fast immer Tippfehler und werden abgelehnt
    model_config = ConfigDict(extra="forbid", frozen=True)


class Law(Model):
    key: str
    title: str
    url: str


class Section(Model):
    key: str
    title: str


class Dimension(Model):
    key: str
    label: str


class Basis(Model):
    """Rechtsgrundlage einer Frage mit wörtlicher Fundstelle."""

    law: str
    article: str
    source: str
    quote: str
    retrieved: datetime.date


class Option(Model):
    value: str
    label: str
    level: int | None = Field(default=None, ge=0, le=MAX_LEVEL)
    dora: bool = False
    nis2_annex: Literal["I", "II"] | None = None


class Question(Model):
    key: str
    section: str
    type: QuestionType
    text: str
    help: str | None = None
    unit: str | None = None
    dimension: str | None = None
    options: tuple[Option, ...] = ()
    basis: tuple[Basis, ...] = ()

    @property
    def is_maturity(self) -> bool:
        return self.dimension is not None

    @model_validator(mode="after")
    def options_fit_the_type(self) -> Self:
        values = [option.value for option in self.options]
        if len(values) != len(set(values)):
            raise ValueError(f"{self.key}: Antwortwerte doppelt")
        if self.type is QuestionType.SINGLE and len(values) < 2:
            raise ValueError(f"{self.key}: Auswahlfrage braucht mindestens zwei Antworten")
        if self.type is QuestionType.NUMBER and values:
            raise ValueError(f"{self.key}: Zahlenfrage hat keine Antworten")
        return self

    @model_validator(mode="after")
    def maturity_is_complete(self) -> Self:
        levels = [option.level for option in self.options]
        if not self.is_maturity:
            if any(level is not None for level in levels):
                raise ValueError(f"{self.key}: Stufe ohne Handlungsfeld")
            return self
        if self.section == PROFILE_SECTION:
            raise ValueError(f"{self.key}: Profilfragen ergeben keinen Reifegrad")
        if self.type is not QuestionType.SINGLE or None in levels:
            raise ValueError(f"{self.key}: jede Antwort braucht eine Stufe")
        if max(levels) != MAX_LEVEL or min(levels) != 0:
            raise ValueError(f"{self.key}: Stufen müssen von 0 bis {MAX_LEVEL} reichen")
        unknown = [option for option in self.options if option.value == UNKNOWN]
        if not unknown or unknown[0].level != 0:
            raise ValueError(f"{self.key}: „Weiß nicht“ fehlt oder zählt nicht wie „Nein“")
        return self


class Questionnaire(Model):
    version: int
    laws: tuple[Law, ...]
    sections: tuple[Section, ...]
    dimensions: tuple[Dimension, ...]
    questions: tuple[Question, ...]

    def question(self, key: str) -> Question:
        return next(question for question in self.questions if question.key == key)

    @model_validator(mode="after")
    def references_exist(self) -> Self:
        for name, keys in [
            ("Rechtsquelle", [law.key for law in self.laws]),
            ("Abschnitt", [section.key for section in self.sections]),
            ("Handlungsfeld", [dimension.key for dimension in self.dimensions]),
            ("Frage", [question.key for question in self.questions]),
        ]:
            if len(keys) != len(set(keys)):
                raise ValueError(f"{name} doppelt")
        laws = {law.key: law.url for law in self.laws}
        sections = {section.key for section in self.sections}
        dimensions = {dimension.key for dimension in self.dimensions}
        for question in self.questions:
            if question.section not in sections:
                raise ValueError(f"{question.key}: Abschnitt {question.section} fehlt")
            if question.dimension is not None and question.dimension not in dimensions:
                raise ValueError(f"{question.key}: Handlungsfeld {question.dimension} fehlt")
            for basis in question.basis:
                if laws.get(basis.law) != basis.source:
                    raise ValueError(f"{question.key}: Quelle passt nicht zu {basis.law}")
        return self


def parse_questionnaire(path: Path) -> Questionnaire:
    return Questionnaire.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@cache
def load_questionnaire() -> Questionnaire:
    return parse_questionnaire(QUESTIONNAIRE_FILE)
