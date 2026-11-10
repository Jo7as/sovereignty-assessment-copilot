"""Qualität der Vertragsanalyse messen: Ergebnis des Ablaufs gegen die Musterlösung.

Kennzahlen nach Arbeitsanweisung, Abschnitt 9. Gezählt werden nur die Felder, die die
Musterlösung labelt (data/testdata/contracts/gold/).
"""

from dataclasses import dataclass

from app.contracts.fields import NOT_FOUND
from app.contracts.pipeline import FieldState, MergedField


@dataclass(frozen=True)
class FieldScore:
    contract: str
    field: str
    expected: str  # Wert der Musterlösung oder NICHT_GEFUNDEN
    acceptable: frozenset[str]  # erwarteter Wert und weitere vertretbare Werte
    expected_pages: frozenset[int]
    state: FieldState
    values: tuple[str, ...]  # verschiedene Werte der KI, bei UNKLAR mehrere
    pages: tuple[int, ...]

    @property
    def reported(self) -> bool:
        """Die KI hat eine Angabe gemacht (gefunden oder unklar)."""
        return self.state != FieldState.NICHT_GEFUNDEN

    @property
    def correct(self) -> bool:
        """Wert richtig. Ein Widerspruch zählt als richtig, wenn die Musterlösung jeden der
        Werte für vertretbar hält: Dann ist „unklar“ genau das gewünschte Ergebnis."""
        if not self.reported:
            return NOT_FOUND in self.acceptable
        return set(self.values) <= self.acceptable

    @property
    def page_correct(self) -> bool:
        """Wert richtig und mindestens eine Fundstelle auf einer Seite der Musterlösung."""
        if not self.correct:
            return False
        return not self.reported or bool(set(self.pages) & self.expected_pages)


def score(contract: str, gold: dict, merged: list[MergedField]) -> list[FieldScore]:
    """Vergleicht je Feld der Musterlösung. `merged` ist das Ergebnis von `pipeline.merge`."""
    by_field = {item.field: item for item in merged}
    scores = []
    for name, label in gold.items():
        result = by_field.get(name)
        findings = result.findings if result else ()
        scores.append(
            FieldScore(
                contract=contract,
                field=name,
                expected=label["value"],
                acceptable=frozenset([label["value"], *label.get("also_correct", [])]),
                expected_pages=frozenset(item["page"] for item in label.get("evidence", [])),
                state=result.state if result else FieldState.NICHT_GEFUNDEN,
                values=result.values if result else (),
                pages=tuple(sorted({item.page for item in findings})),
            )
        )
    return scores


@dataclass(frozen=True)
class Summary:
    fields: int
    agreement: float  # Anteil aller Felder mit richtigem Ergebnis, „nicht gefunden“ eingeschlossen
    precision: float  # Genauigkeit: Anteil der Angaben der KI mit richtigem Wert
    page_precision: float  # Anteil der Angaben der KI mit richtigem Wert und richtiger Seite
    recall: float  # Trefferquote: Anteil der Angaben der Musterlösung, die die KI richtig fand
    false_not_found: float  # steht im Vertrag, die KI meldet nichts


def summarize(scores: list[FieldScore]) -> Summary:
    reported = [item for item in scores if item.reported]
    expected = [item for item in scores if item.expected != NOT_FOUND]
    return Summary(
        fields=len(scores),
        agreement=_share(sum(item.correct for item in scores), len(scores)),
        precision=_share(sum(item.correct for item in reported), len(reported)),
        page_precision=_share(sum(item.page_correct for item in reported), len(reported)),
        recall=_share(sum(item.correct and item.reported for item in expected), len(expected)),
        false_not_found=_share(sum(not item.reported for item in expected), len(expected)),
    )


def _share(part: int, whole: int) -> float:
    return round(part / whole, 3) if whole else 0.0
