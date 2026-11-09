"""Belegprüfung: Steht ein Zitat wörtlich im Text? Gemeinsam für Schnellcheck und Verträge."""

from app.matching.quotes import is_quoted, numbers


def test_quote_is_found_regardless_of_whitespace_and_separators():
    text = "Willkommen | Wir sind die Direktbank\n für 9.500.000 Kunden"

    assert is_quoted("Wir sind die  Direktbank für 9.500.000 Kunden", text)


def test_short_or_invented_quote_is_not_accepted():
    text = "Die Daten werden ausschließlich in der EU gespeichert."

    assert not is_quoted("in der EU", text)  # unter 10 Zeichen belegt nichts
    assert not is_quoted("Die Daten werden in Deutschland gespeichert", text)


def test_word_split_at_line_end_still_matches():
    """PDFs trennen Wörter am Zeilenende: „Verarbei-“ / „tung“."""
    text = "Die Verarbei-\ntung der Kundendaten erfolgt in Rechenzentren in Frankfurt."

    assert is_quoted("Die Verarbeitung der Kundendaten erfolgt", text)


def test_hyphenated_compound_split_at_line_end_still_matches():
    text = "Der Anbieter beachtet die Vorgaben zur IT-\nSicherheit nach dem Stand der Technik."

    assert is_quoted("die Vorgaben zur IT-Sicherheit nach dem Stand", text)


def test_soft_hyphen_is_ignored():
    text = "Kündigungs­frist von drei Monaten zum Quartalsende"

    assert is_quoted("Kündigungsfrist von drei Monaten", text)


def test_spaces_inserted_into_words_by_pdf_extraction_are_ignored():
    """pypdf liest aus dem AWS-Vertrag „becom e aware“ und „Cus tomer“."""
    text = "it is unlikely that AWS would becom e aware that Cus tomer Data is inaccurate"

    assert is_quoted("AWS would become aware that Customer Data is inaccurate", text)


def test_numbers_with_thousands_separators():
    assert numbers("Rund 6.000 Mitarbeitende, 9 500 000 Kunden, 30 Tage") == {6000, 9500000, 30}
