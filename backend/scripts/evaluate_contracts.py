"""Misst die Vertragsanalyse an den Testverträgen und ihrer Musterlösung.

Läuft den echten Ablauf mit der KI aus der .env (Einordnen, Auslesen, Belegprüfung,
Zusammenführen) und vergleicht jedes Feld der Musterlösung. Kennzahlen nach
docs/tiefenpruefung-ablauf.md, Abschnitt 9. Das Ergebnis landet zusätzlich in
data/testdata/contracts/results/<Prompt-Version>.json, ohne Vertragstext.

Vorher die PDFs laden:  uv run python scripts/fetch_contracts.py
Aufruf im Ordner backend/:
    PYTHONPATH=. uv run python scripts/evaluate_contracts.py [--only aws-dpa]
Dauer: einige Minuten, die Ausgabe kommt je Vertrag.
"""

import argparse
import json
import sys
import time
from dataclasses import asdict
from datetime import date
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.config import settings
from app.contracts import DocumentType, read_pages
from app.contracts.evaluation import FieldScore, score, summarize
from app.contracts.pipeline import (
    PROMPT_VERSION,
    ElementState,
    MergedField,
    OpenRouterExtractor,
    classify,
    extract,
    merge,
)
from app.db import engine
from app.matching.catalog import load_catalog

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "data" / "testdata" / "contracts"
WORKERS = 4


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", help="nur dieser Vertrag, z. B. aws-dpa")
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # Fortschritt auch, wenn die Ausgabe umgeleitet ist
    if not settings.openrouter_api_key:
        print("Kein OPENROUTER_API_KEY in der .env.")
        return 1
    extractor = OpenRouterExtractor(settings.openrouter_api_key, settings.openrouter_model)
    sources = yaml.safe_load((CONTRACTS_DIR / "sources.yaml").read_text())["contracts"]
    inventory = {source["service"] for source in sources if source["service"]}
    with Session(engine) as session:
        candidates = [item for item in load_catalog(session) if item.slug in inventory]

    scores: list[FieldScore] = []
    contracts = []
    for source in sources:
        name = source["id"]
        pdf = CONTRACTS_DIR / "pdf" / f"{name}.pdf"
        if (args.only and name != args.only) or not pdf.exists():
            if not args.only:
                print(f"übersprungen {name}: PDF fehlt")
            continue
        gold = yaml.safe_load((CONTRACTS_DIR / "gold" / f"{name}.yaml").read_text())["fields"]
        pages = read_pages(pdf.read_bytes())
        started = time.monotonic()
        proposal = classify(extractor, pages, candidates)
        blocks = extract(extractor, pages, DocumentType.AVV, WORKERS)
        accepted = [item for block in blocks for item in block.accepted]
        rejected = sum(len(block.rejected) for block in blocks)
        merged = merge(gold, accepted, [DocumentType.AVV])
        result = score(name, gold, merged)
        scores.extend(result)
        contracts.append(
            {
                "contract": name,
                "seconds": round(time.monotonic() - started),
                "classification_type": proposal.document_type,
                "classification_type_correct": proposal.document_type == DocumentType.AVV,
                "classification_service": proposal.service,
                "classification_service_correct": proposal.service == source["service"],
                "accepted": len(accepted),
                "rejected": rejected,
                "errors": [block.error for block in blocks if block.error],
                "summary": asdict(summarize(result)),
            }
        )
        _print_contract(contracts[-1], result, merged)

    total = summarize(scores)
    accepted = sum(item["accepted"] for item in contracts)
    rejected = sum(item["rejected"] for item in contracts)
    _print_fields(scores)
    print(f"\nGesamt über {len(contracts)} Verträge, {total.fields} Felder:")
    print(f"  Übereinstimmung      {total.agreement:.0%}  (alle Felder, auch „nicht gefunden“)")
    print(f"  Genauigkeit          {total.precision:.0%}  (Angaben der KI mit richtigem Wert)")
    print(f"  ... mit Seite        {total.page_precision:.0%}")
    print(f"  Trefferquote         {total.recall:.0%}  (Angaben der Musterlösung gefunden)")
    print(f"  Fälschlich nicht gef. {total.false_not_found:.0%}")
    print(f"  Verwerfungsquote     {_share(rejected, accepted + rejected):.0%}")

    if not args.only:
        target = CONTRACTS_DIR / "results" / f"{PROMPT_VERSION}.json"
        target.parent.mkdir(exist_ok=True)
        report = {
            "prompt_version": PROMPT_VERSION,
            "model": settings.openrouter_model,
            "date": date.today().isoformat(),
            "summary": asdict(total),
            "rejection_rate": _share(rejected, accepted + rejected),
            "contracts": contracts,
            "fields": [_row(item) for item in scores],
        }
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")
        print(f"\nGespeichert: {target.relative_to(CONTRACTS_DIR.parents[2])}")
    return 0


def _print_contract(contract: dict, result: list[FieldScore], merged: list[MergedField]) -> None:
    summary = contract["summary"]
    elements = {field.field: field.elements for field in merged}
    print(
        f"\n## {contract['contract']} ({contract['seconds']} s): "
        f"Übereinstimmung {summary['agreement']:.0%}, Genauigkeit {summary['precision']:.0%}, "
        f"Trefferquote {summary['recall']:.0%}, verworfen {contract['rejected']}"
    )
    print(
        f"   Einordnung: {contract['classification_type']} / "
        f"{contract['classification_service']}"
        + ("" if contract["classification_service_correct"] else "  (Dienst falsch)")
    )
    for error in contract["errors"]:
        print(f"   FEHLER {error}")
    for item in result:
        if not item.correct:
            got = " + ".join(item.values) or "NICHT_GEFUNDEN"
            print(f"   falsch  {item.field:30} erwartet {item.expected:24} KI {got}")
            # Bei Prüfpunkten: welche Bestandteile das Urteil tragen
            for part in elements[item.field]:
                if part.state != ElementState.NICHT_GEPRUEFT:
                    print(f"           {part.state:14} {part.element.name}")


def _print_fields(scores: list[FieldScore]) -> None:
    print("\nJe Feld (richtig von Verträgen):")
    for name in dict.fromkeys(item.field for item in scores):
        items = [item for item in scores if item.field == name]
        right = sum(item.correct for item in items)
        print(f"   {name:30} {right}/{len(items)}")


def _row(item: FieldScore) -> dict:
    return {
        "contract": item.contract,
        "field": item.field,
        "expected": item.expected,
        "state": item.state,
        "values": list(item.values),
        "pages": list(item.pages),
        "correct": item.correct,
        "page_correct": item.page_correct,
    }


def _share(part: int, whole: int) -> float:
    return round(part / whole, 3) if whole else 0.0


if __name__ == "__main__":
    sys.exit(main())
