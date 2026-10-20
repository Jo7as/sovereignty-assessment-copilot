"""API-Endpunkt: Außenscan einer Domain."""

from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_session
from app.inventory.api import error
from app.matching.catalog import load_catalog
from app.scan import (
    STEPS,
    Category,
    Finding,
    InvalidDomain,
    NetworkLookup,
    Resolver,
    Strength,
    normalize_domain,
    scan,
)
from app.scan.fetch import SafeFetcher
from app.scan.network import DnsResolver, RipeStat
from app.scan.website import PageFetcher

router = APIRouter(prefix="/scan", tags=["Außenscan"])


class ScanRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=300)


def get_resolver() -> Resolver:
    return DnsResolver()


def get_networks() -> NetworkLookup:
    return RipeStat()


def get_fetcher(resolver: Annotated[Resolver, Depends(get_resolver)]) -> PageFetcher:
    return SafeFetcher(resolver)


@router.post("")
def scan_domain(
    body: ScanRequest,
    session: Annotated[Session, Depends(get_session)],
    resolver: Annotated[Resolver, Depends(get_resolver)],
    networks: Annotated[NetworkLookup, Depends(get_networks)],
    fetcher: Annotated[PageFetcher, Depends(get_fetcher)],
) -> dict:
    """Prüft E-Mail, Domain, Hosting und die eingebundenen Dienste der Website.

    Erkannte Dienste kommen mit Fund und Beleg, getrennt nach Unternehmensdiensten und
    Website-Werkzeugen. Alle übrigen Funde kommen roh, nach Gruppe sortiert.
    """
    try:
        domain = normalize_domain(body.domain)
    except InvalidDomain as problem:
        raise error(422, "INVALID_DOMAIN", str(problem)) from problem
    result = scan(domain, resolver, networks, fetcher)
    catalog = {service.slug: service for service in load_catalog(session)}

    services, other = [], [f for f in result.findings if f.service is None]
    for slug, findings in result.services.items():
        if slug not in catalog:  # Merkmal ohne Dienst in der Datenbank: roh melden
            other.extend(findings)
            continue
        nutzung = any(f.strength is Strength.NUTZUNG for f in findings)
        # Ein Dienst, der auch außerhalb der Website auftaucht, ist ein Unternehmensdienst
        website_only = all(f.category is Category.WEBSITE for f in findings)
        services.append(
            {
                "service": slug,
                "name": catalog[slug].name,
                "provider": catalog[slug].provider,
                "strength": Strength.NUTZUNG if nutzung else Strength.HINWEIS,
                "group": "WEBSITE" if website_only else "UNTERNEHMEN",
                "findings": [_finding(f) for f in findings],
            }
        )
    services.sort(key=lambda item: (item["strength"] != Strength.NUTZUNG, item["name"].casefold()))
    return {
        "domain": domain,
        "title": result.title,
        "imprint_url": result.imprint_url,
        "steps": list(STEPS),
        "services": services,
        "other_findings": [
            _finding(f) for f in sorted(other, key=lambda f: list(Category).index(f.category))
        ],
        "problems": result.problems,
    }


def _finding(finding: Finding) -> dict:
    data = asdict(finding)
    data["category"] = finding.category
    data["evidence"] = finding.evidence.model_dump(mode="json") if finding.evidence else None
    return data
