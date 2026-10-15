from datetime import date
from pathlib import Path

import pytest
import yaml

from app.inventory import build_template, read_inventory
from app.models import Criticality

TESTDATA = Path(__file__).resolve().parents[2] / "data" / "testdata"
REQUIRED = {"purpose": "Zweck", "criticality": "hoch", "critical_function": "nein"}


def xlsx(tmp_path, rows) -> bytes:
    return build_template(tmp_path / "bestand.xlsx", rows).read_bytes()


def test_musterbank_file_is_read_without_errors():
    result = read_inventory((TESTDATA / "musterbank-it-bestand.xlsx").read_bytes(), "bestand.xlsx")
    expected = yaml.safe_load((TESTDATA / "musterbank.yaml").read_text())

    assert result.errors == []
    assert [entry.service for entry in result.entries] == [row["service"] for row in expected]


def test_values_are_converted_to_their_types(tmp_path):
    row = {
        "service": "O365",
        "purpose": "E-Mail",
        "criticality": "hoch",
        "critical_function": "ja",
        "notice_period_days": 30,
        "contract_start": "01.04.2020",
    }

    entry = read_inventory(xlsx(tmp_path, [row]), "bestand.xlsx").entries[0]

    assert entry.criticality is Criticality.HOCH
    assert entry.critical_function is True
    assert entry.values["notice_period_days"] == 30
    assert entry.values["contract_start"] == date(2020, 4, 1)
    assert entry.row == 2


def test_missing_required_value_is_reported_with_row_and_column(tmp_path):
    result = read_inventory(
        xlsx(tmp_path, [{"service": "O365", "purpose": "E-Mail", "critical_function": "ja"}]),
        "bestand.xlsx",
    )

    assert result.entries == []
    assert [(error.row, error.column) for error in result.errors] == [(2, "Kritikalität *")]


def test_value_outside_the_list_is_reported(tmp_path):
    result = read_inventory(
        xlsx(tmp_path, [{"service": "O365", **REQUIRED, "criticality": "sehr hoch"}]),
        "bestand.xlsx",
    )

    assert "gering, mittel, hoch" in result.errors[0].message


def test_list_values_are_accepted_regardless_of_case_and_spaces():
    csv = (
        "Dienst *;Zweck *;Kritikalität *;Kritische oder wichtige Funktion *\n"
        "O365;E-Mail; HOCH ;Ja\n"
    )

    result = read_inventory(csv.encode(), "bestand.csv")

    assert result.errors == []
    assert result.entries[0].criticality is Criticality.HOCH


def test_csv_with_semicolons_and_byte_order_mark_is_read():
    csv = (
        "﻿Dienst *;Zweck *;Kritikalität *;Kritische oder wichtige Funktion *\n"
        "Slack;Chat;gering;nein\n"
    )

    result = read_inventory(csv.encode("utf-8"), "bestand.csv")

    assert [entry.service for entry in result.entries] == ["Slack"]


def test_csv_with_commas_and_windows_encoding_is_read():
    csv = (
        "Dienst,Zweck,Kritikalität,Kritische oder wichtige Funktion\n"
        "Personio,Personalverwaltung,mittel,nein\n"
    )

    result = read_inventory(csv.encode("cp1252"), "bestand.csv")

    assert result.entries[0].criticality is Criticality.MITTEL


def test_headers_may_be_written_without_asterisk_or_as_keys():
    csv = "service;purpose;KRITIKALITÄT;kritische oder wichtige funktion\nSlack;Chat;gering;nein\n"

    assert read_inventory(csv.encode(), "bestand.csv").errors == []


def test_missing_required_column_is_reported_once():
    csv = "Dienst *;Zweck *;Kritikalität *\nSlack;Chat;gering\n"

    result = read_inventory(csv.encode(), "bestand.csv")

    assert [(error.row, error.column) for error in result.errors] == [
        (1, "Kritische oder wichtige Funktion *")
    ]
    assert result.entries == []


def test_unknown_column_is_ignored_with_a_warning():
    csv = (
        "Dienst;Zweck;Kritikalität;Kritische oder wichtige Funktion;Kostenstelle\n"
        "Slack;Chat;gering;nein;4711\n"
    )

    result = read_inventory(csv.encode(), "bestand.csv")

    assert result.errors == []
    assert result.warnings == ["Spalte „Kostenstelle“ ist unbekannt und wird ignoriert."]


def test_duplicate_column_uses_the_first_and_warns():
    csv = (
        "Dienst;Zweck;Kritikalität;Kritische oder wichtige Funktion;Zweck\n"
        "Slack;Chat;gering;nein;Anderes\n"
    )

    result = read_inventory(csv.encode(), "bestand.csv")

    assert result.entries[0].values["purpose"] == "Chat"
    assert "doppelt" in result.warnings[0]


def test_empty_rows_are_skipped():
    csv = (
        "Dienst;Zweck;Kritikalität;Kritische oder wichtige Funktion\n"
        ";;;\n"
        "Slack;Chat;gering;nein\n"
        ";;;\n"
    )

    result = read_inventory(csv.encode(), "bestand.csv")

    assert [entry.row for entry in result.entries] == [3]


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("Kündigungsfrist (Tage)", "drei Monate", "ganze Zahl"),
        ("Kündigungsfrist (Tage)", "-5", "ganze Zahl"),
        ("Vertragsbeginn", "2020-13-01", "TT.MM.JJJJ"),
    ],
)
def test_invalid_numbers_and_dates_are_reported(column, value, message):
    csv = (
        f"Dienst;Zweck;Kritikalität;Kritische oder wichtige Funktion;{column}\n"
        f"Slack;Chat;gering;nein;{value}\n"
    )

    result = read_inventory(csv.encode(), "bestand.csv")

    assert message in result.errors[0].message


def test_iso_dates_are_accepted():
    csv = (
        "Dienst;Zweck;Kritikalität;Kritische oder wichtige Funktion;Vertragsbeginn\n"
        "Slack;Chat;gering;nein;2020-04-01\n"
    )

    assert read_inventory(csv.encode(), "bestand.csv").entries[0].values["contract_start"] == date(
        2020, 4, 1
    )


def test_unsupported_file_type_is_rejected():
    from app.inventory import UnreadableFile

    with pytest.raises(UnreadableFile, match="xlsx oder .csv"):
        read_inventory(b"irgendwas", "bestand.pdf")


def test_broken_excel_file_is_rejected():
    from app.inventory import UnreadableFile

    with pytest.raises(UnreadableFile, match="Excel"):
        read_inventory(b"kein zip", "bestand.xlsx")


def test_file_without_header_row_is_rejected():
    from app.inventory import UnreadableFile

    with pytest.raises(UnreadableFile, match="leer"):
        read_inventory(b"", "bestand.csv")
