"""Schutz vor schleichender Verschlechterung: Neue Dienste in der Datenbank dürfen die
Zuordnung der Musterbank nicht verschlechtern. Ein neuer Firmenname mit der Rechtsform
„SAS“ hatte das einmal unbemerkt getan."""

from pathlib import Path

import yaml

from app.matching import Method, match_entry
from app.matching.catalog import load_catalog
from app.seed import load_seed

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
# Stand 19.10.2026: 53 von 58 Einträgen ordnet der Textvergleich sicher und richtig zu
MIN_CORRECT_TEXT_MATCHES = 53


def test_text_matching_on_the_musterbank_never_gets_worse(session):
    load_seed(session, DATA_DIR)
    catalog = load_catalog(session)
    rows = yaml.safe_load((DATA_DIR / "testdata" / "musterbank.yaml").read_text(encoding="utf-8"))

    results = [(row, match_entry(row, catalog)) for row in rows]
    text = [(row, result) for row, result in results if result.method is Method.TEXT]
    wrong = [row["service"] for row, result in text if result.slug != row["erwartet"]]
    correct = len(text) - len(wrong)

    assert wrong == [], "Der Textvergleich darf nie ohne Prüfung falsch zuordnen"
    assert correct >= MIN_CORRECT_TEXT_MATCHES
