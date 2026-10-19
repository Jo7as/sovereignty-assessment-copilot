"""Misst die Zuordnung an der Musterbank: Wie viele Einträge landen beim richtigen Dienst?

Aufruf im Ordner backend/:
    uv run python -m app.matching            mit KI, falls ein Schlüssel hinterlegt ist
    uv run python -m app.matching --ohne-ki  nur Textvergleich
    uv run python -m app.matching ../data/testdata/zweiter-testsatz.yaml  andere Testdatei

Die KI antwortet nicht immer gleich. Mit KI läuft die Messung deshalb dreimal, ausgegeben
werden der letzte Durchlauf im Detail und die Spanne über alle Durchläufe.
"""

import sys
from collections import Counter
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.config import PROJECT_ROOT
from app.db import engine
from app.matching import Method, match_entry
from app.matching.catalog import default_classifier, load_catalog

# Diese 20 Dienste standen in der Datenbank, bevor die Musterbank geschrieben wurde. Ihre
# Schreibweisen kannte der Autor der Testdaten, die Quote für sie ist vermutlich zu gut.
KNOWN_BEFORE_TESTDATA = {
    "amazon-web-services", "atlassian-cloud", "chatgpt-enterprise", "datev", "github",
    "google-cloud", "google-workspace", "ionos-cloud", "microsoft-365", "microsoft-azure",
    "nextcloud", "ovhcloud", "personio", "salesforce", "sap-s4hana-cloud", "servicenow",
    "slack", "stackit", "t-cloud-public", "zoom",
}  # fmt: skip


RUNS_WITH_AI = 3


def main(arguments: list[str]) -> int:
    files = [argument for argument in arguments if argument.endswith(".yaml")]
    path = Path(files[0]) if files else PROJECT_ROOT / "data/testdata/musterbank.yaml"
    print(f"Testdatei: {path.name}")
    rows = yaml.safe_load(path.read_text("utf-8"))
    classifier = None if "--ohne-ki" in arguments else default_classifier()
    with Session(engine) as session:
        catalog = load_catalog(session)

    runs = RUNS_WITH_AI if classifier else 1
    totals = [evaluate(rows, catalog, classifier, verbose=run == runs - 1) for run in range(runs)]
    if runs > 1:
        print(f"\n{runs} Durchläufe, richtig: {min(totals)} bis {max(totals)} von {len(rows)}")
    return 0


def evaluate(rows, catalog, classifier, verbose: bool) -> int:
    outcome = Counter()
    groups = Counter()
    for row in rows:
        expected = row["erwartet"]
        result = match_entry(row, catalog, classifier)
        correct = result.slug == expected
        outcome[(result.method, correct)] += 1
        group = (
            "ohne Dienst"
            if expected is None
            else ("vorher bekannt" if expected in KNOWN_BEFORE_TESTDATA else "danach angelegt")
        )
        groups[(group, correct)] += 1
        if verbose and (not correct or result.method is not Method.TEXT):
            mark = "richtig" if correct else "FALSCH "
            print(
                f"{mark} {result.method:<4} {row['service'][:34]:<35} -> {result.slug or '-':<24}"
                f" erwartet {expected or '-'}"
            )

    total = len(rows)
    text_right = outcome[(Method.TEXT, True)]
    correct = text_right + outcome[(Method.AI, True)] + outcome[(Method.NONE, True)]
    if not verbose:
        return correct
    print(f"\nKI-Stufe: {'aktiv' if classifier else 'aus'}")
    text_wrong = outcome[(Method.TEXT, False)]
    ai_right, ai_wrong = outcome[(Method.AI, True)], outcome[(Method.AI, False)]
    none_right, none_wrong = outcome[(Method.NONE, True)], outcome[(Method.NONE, False)]
    print(f"{total} Einträge, davon richtig: {correct} ({correct / total:.0%})")
    print(f"  Textvergleich: {text_right} richtig, {text_wrong} falsch (ohne Prüfung übernommen)")
    print(f"  KI-Vorschlag:  {ai_right} richtig, {ai_wrong} falsch (werden geprüft)")
    print(f"  Kein Treffer:  {none_right} richtig, {none_wrong} falsch (werden geprüft)")
    print(f"  Automatisch und richtig zugeordnet: {text_right / total:.0%}")
    for group in ("vorher bekannt", "danach angelegt", "ohne Dienst"):
        right, wrong = groups[(group, True)], groups[(group, False)]
        if right + wrong:
            print(f"  {group}: {right} von {right + wrong} richtig")
    return correct


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
