"""Tabellen für gespeicherte Assessments: Fragebogen-Antworten, IT-Bestand und Verträge."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.contracts import DocumentType, FindingStatus, RunStatus
from app.matching import Method
from app.models.base import Base, TimestampMixin, enum_type


class Assessment(TimestampMixin, Base):
    __tablename__ = "assessment"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    # Fassung des Fragebogens beim Anlegen. Ändert sich der Fragebogen, bleibt erkennbar,
    # auf welche Fragen sich die Antworten beziehen.
    questionnaire_version: Mapped[int]
    # Aus dem Schnellcheck: geprüfte Domain und Vorschläge (Branche, Beschäftigte, Profil) mit
    # Zitat. Vorschläge sind keine Antworten, ein Mensch übernimmt sie im Fragebogen.
    domain: Mapped[str | None] = mapped_column(String(253))
    prefill: Mapped[dict | None] = mapped_column(JSON)

    answers: Mapped[list["AssessmentAnswer"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentAnswer.id"
    )
    inventory: Mapped["AssessmentInventory | None"] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )
    matches: Mapped[list["InventoryMatch"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", order_by="InventoryMatch.row"
    )
    contracts: Mapped[list["AssessmentContract"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", order_by="AssessmentContract.id"
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


class AssessmentContract(TimestampMixin, Base):
    """Ein hochgeladenes Vertragsdokument mit dem Text jeder Seite (Tiefenprüfung).

    Datei und Text werden beide gespeichert: die Datei als Nachweis, der Text, damit Zitate
    der KI immer gegen genau den Text geprüft werden, den die KI gelesen hat.
    """

    __tablename__ = "assessment_contract"

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessment.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content: Mapped[bytes] = mapped_column(LargeBinary)
    # Text je physischer PDF-Seite, Seite 1 an Stelle 0. Seiten ohne Text sind leer.
    pages: Mapped[list[str]] = mapped_column(JSON)
    # Einordnung (Arbeitsanweisung 5.2): von der KI vorgeschlagen, vom Berater bestätigt.
    # Kurzname statt Fremdschlüssel, wie bei der Zuordnung des IT-Bestands.
    service_slug: Mapped[str | None] = mapped_column(String(80))
    document_type: Mapped[DocumentType | None] = mapped_column(
        enum_type(DocumentType, "document_type")
    )
    # Vorschlag der KI mit Zitat, Seite und Hinweis. Bleibt neben der Bestätigung erhalten,
    # damit erkennbar ist, ob der Berater dem Vorschlag gefolgt ist.
    classification: Mapped[dict | None] = mapped_column(JSON)

    assessment: Mapped[Assessment] = relationship(back_populates="contracts")
    runs: Mapped[list["ContractRun"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan", order_by="ContractRun.id"
    )


class ContractRun(TimestampMixin, Base):
    """Ein Lauf der Vertragsanalyse für ein Dokument, mit Protokoll (Arbeitsanweisung 8).

    Ältere Läufe bleiben erhalten, maßgeblich ist der jüngste fertige Lauf.
    """

    __tablename__ = "contract_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_contract.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[RunStatus] = mapped_column(enum_type(RunStatus, "run_status"))
    prompt_version: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(100))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Je Themenblock: Dauer, Fehler, geprüfte Antworten der KI, verworfene Angaben mit Grund
    log: Mapped[dict] = mapped_column(JSON)

    contract: Mapped[AssessmentContract] = relationship(back_populates="runs")
    findings: Mapped[list["ContractFinding"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="ContractFinding.id"
    )


class ContractFinding(TimestampMixin, Base):
    """Eine Angabe aus dem Vertrag, die die Belegprüfung bestanden hat."""

    __tablename__ = "contract_finding"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("contract_run.id", ondelete="CASCADE"), index=True
    )
    field: Mapped[str] = mapped_column(String(60))
    value: Mapped[str] = mapped_column(String(60))
    quote: Mapped[str] = mapped_column(Text)
    page: Mapped[int]  # physische PDF-Seite, gezählt ab 1
    status: Mapped[FindingStatus] = mapped_column(enum_type(FindingStatus, "finding_status"))

    run: Mapped[ContractRun] = relationship(back_populates="findings")
