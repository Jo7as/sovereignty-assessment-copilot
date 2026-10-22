"""API-Endpunkte: Schnellcheck einer Domain, auf einmal oder Schritt für Schritt."""

import json
import queue
import threading
from dataclasses import asdict, dataclass
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.inventory.api import error
from app.models import Service
from app.models.enums import Criticality
from app.questionnaire import load_questionnaire
from app.scan import (
    Category,
    Finding,
    InvalidDomain,
    NetworkLookup,
    Resolver,
    Strength,
    normalize_domain,
)
from app.scan.fetch import SafeFetcher
from app.scan.network import DnsResolver, GleifApi, RipeStat
from app.scan.profile import Gleif
from app.scan.quick import STEPS, QuickCheck, profile_check, run_quick_check, suggestions_for
from app.scan.suggest import OpenRouterSuggester, Suggester, Suggestions
from app.scan.website import PageFetcher
from app.scoring import PortfolioItem, ServiceAssessment, assess_portfolio, assess_variant
from app.scoring.adapter import controlling_jurisdiction

router = APIRouter(prefix="/scan", tags=["Außenscan"])


class ScanRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=300)


def get_resolver() -> Resolver:
    return DnsResolver()


def get_networks() -> NetworkLookup:
    return RipeStat()


def get_fetcher(resolver: Annotated[Resolver, Depends(get_resolver)]) -> PageFetcher:
    return SafeFetcher(resolver)


def get_gleif() -> Gleif:
    return GleifApi()


def get_suggester() -> Suggester | None:
    """Vorschläge der KI nur, wenn ein Schlüssel hinterlegt ist."""
    if not settings.openrouter_api_key:
        return None
    return OpenRouterSuggester(settings.openrouter_api_key, settings.openrouter_model)


@dataclass(frozen=True)
class CatalogEntry:
    name: str
    provider: str
    criticality: str
    assessment: ServiceAssessment
    category: str = ""
    owner: str = ""  # oberste Konzernmutter, sonst der Anbieter selbst
    owner_country: str = ""
    jurisdiction: str = (
        ""  # maßgeblicher Rechtsraum wie in der Bewertung (CLOUD Act über die Mutter)
    )
    alternatives: tuple[dict, ...] = ()


def catalog_entries(session: Session) -> dict[str, CatalogEntry]:
    """Name, Anbieter und Bewertung der Standardvariante je Dienst, vorab aus der Datenbank.

    So braucht der eigentliche Scan keine Datenbank und kann in einem eigenen Thread laufen.
    """
    today = date.today()
    services = session.scalars(select(Service)).all()
    entries = {}
    for service in services:
        owner = service.provider.ultimate_parent or service.provider
        entries[service.slug] = CatalogEntry(
            name=service.name,
            provider=service.provider.name,
            criticality=service.typical_criticality,
            assessment=assess_variant(next(v for v in service.variants if v.is_default), today),
            category=service.category.name,
            owner=owner.name,
            owner_country=owner.country.code,
            jurisdiction=controlling_jurisdiction(service.provider),
            alternatives=tuple(
                {
                    "service": item.alternative.slug,
                    "name": item.alternative.name,
                    "effort": item.migration_effort,
                    "jurisdiction": controlling_jurisdiction(item.alternative.provider),
                    "note": item.note,
                }
                for item in service.alternatives
            ),
        )
    return entries


Dependencies = tuple[Resolver, NetworkLookup, PageFetcher, Gleif, Suggester | None]


def dependencies(
    resolver: Annotated[Resolver, Depends(get_resolver)],
    networks: Annotated[NetworkLookup, Depends(get_networks)],
    fetcher: Annotated[PageFetcher, Depends(get_fetcher)],
    gleif: Annotated[Gleif, Depends(get_gleif)],
    suggester: Annotated[Suggester | None, Depends(get_suggester)],
) -> Dependencies:
    return resolver, networks, fetcher, gleif, suggester


def _domain(raw: str) -> str:
    try:
        return normalize_domain(raw)
    except InvalidDomain as problem:
        raise error(422, "INVALID_DOMAIN", str(problem)) from problem


def _sectors() -> dict[str, str]:
    return {
        option.value: option.label for option in load_questionnaire().question("sector").options
    }


def _check(domain: str, deps: Dependencies) -> QuickCheck:
    return run_quick_check(domain, *deps, _sectors())


@router.post("")
def scan_domain(
    body: ScanRequest,
    session: Annotated[Session, Depends(get_session)],
    deps: Annotated[Dependencies, Depends(dependencies)],
) -> dict:
    """Schnellcheck in einem Aufruf: E-Mail, Domain, Hosting, Website, Impressum, Register und
    Vorschläge. Erkannte Dienste mit Fund, Beleg und Stufe, übrige Funde roh."""
    domain = _domain(body.domain)
    return quick_check_response(_check(domain, deps), catalog_entries(session))


@router.get("/stream")
def scan_stream(
    domain: str,
    session: Annotated[Session, Depends(get_session)],
    deps: Annotated[Dependencies, Depends(dependencies)],
) -> StreamingResponse:
    """Wie POST /scan, meldet aber jeden Schritt sofort (Server-Sent Events).

    Ereignisse: zuerst „plan“ mit allen Schritten, dann „step“ mit dem Namen des Schritts, dann
    „result“ mit dem Ergebnis, dessen Vorschläge noch offen sind (pending), und zuletzt
    „suggestions“ mit den Vorschlägen der KI. Scheitert der Scan, kommt „error“ mit einer Meldung.
    """
    normalized = _domain(domain)
    catalog = catalog_entries(session)  # vorab, der Thread nutzt keine Datenbank
    events: queue.Queue = queue.Queue()
    events.put(("plan", list(STEPS)))  # zuerst alle Schritte, damit die Oberfläche sie zeigen kann

    def work() -> None:
        resolver, networks, fetcher, gleif, suggester = deps
        try:
            check = profile_check(
                normalized,
                resolver,
                networks,
                fetcher,
                gleif,
                lambda step: events.put(("step", step)),
            )
            events.put(("result", quick_check_response(check, catalog)))
        except Exception:  # noqa: BLE001 - der Nutzer bekommt eine Meldung statt eines Abbruchs
            events.put(("error", "Der Schnellcheck ist fehlgeschlagen. Bitte erneut versuchen."))
            events.put(None)
            return
        try:
            suggestions = suggestions_for(check, suggester, _sectors())
        except Exception:  # noqa: BLE001 - das Ergebnis steht schon, es fehlen nur Vorschläge
            suggestions = Suggestions(note="Die Vorschläge ließen sich nicht erstellen.")
        events.put(("suggestions", asdict(suggestions)))
        events.put(None)

    threading.Thread(target=work, daemon=True).start()

    def stream():
        while (item := events.get()) is not None:
            kind, data = item
            yield f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )


def quick_check_response(check: QuickCheck, catalog: dict[str, CatalogEntry]) -> dict:
    result = check.scan
    services, other = [], [f for f in result.findings if f.service is None]
    for slug, findings in result.services.items():
        entry = catalog.get(slug)
        if entry is None:  # Merkmal ohne Dienst in der Datenbank: roh melden
            other.extend(findings)
            continue
        nutzung = any(f.strength is Strength.NUTZUNG for f in findings)
        # Ein Dienst, der auch außerhalb der Website auftaucht, ist ein Unternehmensdienst
        website_only = all(f.category is Category.WEBSITE for f in findings)
        assessment = entry.assessment
        services.append(
            {
                "service": slug,
                "name": entry.name,
                "provider": entry.provider,
                "criticality": entry.criticality,
                "strength": Strength.NUTZUNG if nutzung else Strength.HINWEIS,
                "group": "WEBSITE" if website_only else "UNTERNEHMEN",
                "level": assessment.level,
                "potential": assessment.potential,
                "score": round(assessment.score, 1),
                "objectives": {
                    objective: {"level": item.level, "potential": item.potential}
                    for objective, item in assessment.objectives.items()
                },
                "findings": [_finding(f) for f in findings],
                "category": entry.category,
                "owner": entry.owner,
                "owner_country": entry.owner_country,
                "jurisdiction": entry.jurisdiction,
                "alternatives": list(entry.alternatives),
            }
        )
    services.sort(key=lambda item: (item["strength"] != Strength.NUTZUNG, item["name"].casefold()))
    # Gesamtstufe wie im Assessment, gewichtet mit der typischen Kritikalität der Dienste
    items = [
        PortfolioItem(s["service"], Criticality(s["criticality"]), catalog[s["service"]].assessment)
        for s in services
    ]
    portfolio = assess_portfolio(items) if items else None
    return {
        "domain": result.domain,
        "title": result.title,
        "imprint_url": result.imprint_url,
        "steps": list(STEPS),
        "profile": asdict(check.profile),
        "suggestions": asdict(check.suggestions),
        "services": services,
        "summary": _summary(services, portfolio),
        "levers": _levers(services),
        "other_findings": [
            _finding(f) for f in sorted(other, key=lambda f: list(Category).index(f.category))
        ],
        "signals": result.signals,
        "problems": result.problems,
    }


def _summary(services: list[dict], portfolio) -> dict:
    """Kopfzeile des Ergebnisses: wie viele Dienste, wie viele außerhalb der EU, Gesamtstufe."""
    outside = [s for s in services if s["jurisdiction"] not in {"EU_EWR", "ANGEMESSEN"}]
    return {
        "recognized": len(services),
        "outside_eu": len(outside),
        "outside_eu_names": [s["name"] for s in outside],
        "with_alternative": sum(1 for s in services if s["alternatives"]),
        "level": round(portfolio.level, 1) if portfolio else None,
        "score": round(portfolio.score) if portfolio else None,
        "potential_score": round(portfolio.potential_score) if portfolio else None,
    }


LEVERS = 3


def _levers(services: list[dict]) -> list[dict]:
    """Die Dienste, bei denen ein Wechsel am meisten bringt: Kritikalität mal Abstand zur
    Höchststufe, wie in der Roadmap. Dienste mit EU-Alternative zuerst."""
    weight = {"GERING": 1, "MITTEL": 2, "HOCH": 3}
    ranked = sorted(
        services,
        key=lambda s: (
            -weight[s["criticality"]] * (4 - s["level"]),
            not s["alternatives"],
            s["name"],
        ),
    )
    return [
        {
            "service": s["service"],
            "name": s["name"],
            "level": s["level"],
            "criticality": s["criticality"],
            "priority": weight[s["criticality"]] * (4 - s["level"]),
            "alternative": s["alternatives"][0] if s["alternatives"] else None,
        }
        for s in ranked[:LEVERS]
        if s["level"] < 4
    ]


def _finding(finding: Finding) -> dict:
    data = asdict(finding)
    data["category"] = finding.category
    data["evidence"] = finding.evidence.model_dump(mode="json") if finding.evidence else None
    return data
