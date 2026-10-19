"""Tabellen für gespeicherte Assessments und ihre Fragebogen-Antworten."""

from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Assessment(TimestampMixin, Base):
    __tablename__ = "assessment"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    # Fassung des Fragebogens beim Anlegen. Ändert sich der Fragebogen, bleibt erkennbar,
    # auf welche Fragen sich die Antworten beziehen.
    questionnaire_version: Mapped[int]

    answers: Mapped[list["AssessmentAnswer"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentAnswer.id"
    )


class AssessmentAnswer(TimestampMixin, Base):
    """Eine Antwort: bei Auswahlfragen der Wert der Antwort, bei Zahlenfragen die Zahl."""

    __tablename__ = "assessment_answer"
    __table_args__ = (
        UniqueConstraint("assessment_id", "question_key"),
        CheckConstraint(
            "(option_value IS NULL) <> (number_value IS NULL)", name="exactly_one_value"
        ),
        CheckConstraint("number_value >= 0", name="number_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Ohne eigenen Index: Die Eindeutigkeitsregel beginnt mit dieser Spalte und dient als Index
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessment.id", ondelete="CASCADE"))
    question_key: Mapped[str] = mapped_column(String(60))
    option_value: Mapped[str | None] = mapped_column(String(60))
    number_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))

    assessment: Mapped[Assessment] = relationship(back_populates="answers")
