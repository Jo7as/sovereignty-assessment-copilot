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
    Finding,
    InvalidDomain,
    NetworkLookup,
    Resolver,
    Strength,
    normalize_domain,
    scan,
)
from app.scan.network import DnsResolver, RipeStat

router = APIRouter(prefix="/scan", tags=["Außenscan"])


class ScanRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=300)


def get_resolver() -> Resolver:
    return DnsResolver()


def get_networks() -> NetworkLookup:
    return RipeStat()


@router.post("")
def scan_domain(
    body: ScanRequest,
    session: Annotated[Session, Depends(get_session)],
    resolver: Annotated[Resolver, Depends(get_resolver)],
    networks: Annotated[NetworkLookup, Depends(get_networks)],
) -> dict:
    """Prüft Mailserver, SPF, Nameserver und Netzbetreiber der Website. Jeder erkannte Dienst
    kommt mit Fund und Beleg, alle übrigen Funde roh."""
    try:
        domain = normalize_domain(body.domain)
    except InvalidDomain as problem:
        raise error(422, "INVALID_DOMAIN", str(problem)) from problem
    result = scan(domain, resolver, networks)
    catalog = {service.slug: service for service in load_catalog(session)}

    services, other = [], [f for f in result.findings if f.service is None]
    for slug, findings in result.services.items():
        if slug not in catalog:  # Merkmal ohne Dienst in der Datenbank: roh melden
            other.extend(findings)
            continue
        strongest = (
            Strength.NUTZUNG
            if any(f.strength is Strength.NUTZUNG for f in findings)
            else Strength.HINWEIS
        )
        services.append(
            {
                "service": slug,
                "name": catalog[slug].name,
                "provider": catalog[slug].provider,
                "strength": strongest,
                "findings": [_finding(f) for f in findings],
            }
        )
    services.sort(key=lambda item: (item["strength"] != Strength.NUTZUNG, item["name"].casefold()))
    return {
        "domain": domain,
        "services": services,
        "other_findings": [_finding(f) for f in other],
        "problems": result.problems,
    }


def _finding(finding: Finding) -> dict:
    data = asdict(finding)
    data["evidence"] = finding.evidence.model_dump(mode="json") if finding.evidence else None
    return data
