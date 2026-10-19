"""Tabellen für gespeicherte Assessments und ihre Fragebogen-Antworten."""

from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.matching import Method
from app.models.base import Base, TimestampMixin, enum_type


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
    inventory: Mapped["AssessmentInventory | None"] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    matches: Mapped[list["InventoryMatch"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", order_by="InventoryMatch.row"
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


class AssessmentInventory(TimestampMixin, Base):
    """Der hochgeladene IT-Bestand, als Originaldatei.

    Gespeichert wird die Datei, nicht die gelesenen Werte: So bleibt der Importer die einzige
    Stelle, die Dateien liest, und das Original bleibt als Nachweis erhalten.
    """

    __tablename__ = "assessment_inventory"

    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessment.id", ondelete="CASCADE"), primary_key=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content: Mapped[bytes] = mapped_column(LargeBinary)

    assessment: Mapped[Assessment] = relationship(back_populates="inventory")


class InventoryMatch(TimestampMixin, Base):
    """Zuordnung einer Zeile des IT-Bestands zu einem Dienst, berechnet beim Hochladen.

    Gespeichert, damit die KI nicht bei jedem Abruf neu gefragt wird: Das kostet und liefert
    nicht immer dasselbe Ergebnis.
    """

    __tablename__ = "inventory_match"
    __table_args__ = (UniqueConstraint("assessment_id", "row"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessment.id", ondelete="CASCADE"))
    row: Mapped[int]
    # Kurzname statt Fremdschlüssel: Verschwindet ein Dienst aus der Datenbank, bleibt die
    # Zuordnung lesbar und wird bei der Bewertung als offen gemeldet
    service_slug: Mapped[str | None] = mapped_column(String(80))
    method: Mapped[Method] = mapped_column(enum_type(Method, "match_method"))
    confidence: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text)

    assessment: Mapped[Assessment] = relationship(back_populates="matches")
