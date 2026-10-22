"""Echte Abfragen für den Außenscan: DNS und RIPEstat. In Tests ersetzt durch Attrappen."""

import dns.resolver
import httpx2

from app.scan.profile import LeiRecord

DNS_TIMEOUT = 4  # Sekunden je Abfrage
HTTP_TIMEOUT = 6
RIPESTAT = "https://stat.ripe.net/data"


class DnsResolver:
    def __init__(self) -> None:
        self._resolver = dns.resolver.Resolver()
        self._resolver.lifetime = DNS_TIMEOUT

    def lookup(self, name: str, record: str) -> list[str]:
        try:
            answer = self._resolver.resolve(name, record)
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            return []  # es gibt den Eintrag nicht, das ist ein Ergebnis und kein Fehler
        if record == "MX":
            return [str(item.exchange).rstrip(".").lower() for item in answer]
        if record in {"NS", "CNAME"}:
            return [str(item.target).rstrip(".").lower() for item in answer]
        if record == "TXT":
            return [b"".join(item.strings).decode("utf-8", "replace") for item in answer]
        return [item.to_text() for item in answer]


class RipeStat:
    """Netzbetreiber einer IP-Adresse über die öffentliche Schnittstelle von RIPEstat."""

    def __init__(self) -> None:
        self._client = httpx2.Client(
            timeout=HTTP_TIMEOUT, params={"sourceapp": "sovereignty-copilot"}
        )
        self._holders: dict[int, str] = {}  # Namen der Netzbetreiber, je Scan nur einmal abfragen

    def network(self, ip: str) -> tuple[int, str] | None:
        info = self._client.get(f"{RIPESTAT}/network-info/data.json", params={"resource": ip})
        info.raise_for_status()
        asns = info.json()["data"].get("asns") or []
        if not asns:
            return None
        asn = int(asns[0])
        if asn not in self._holders:
            overview = self._client.get(
                f"{RIPESTAT}/as-overview/data.json", params={"resource": f"AS{asn}"}
            )
            overview.raise_for_status()
            self._holders[asn] = overview.json()["data"].get("holder") or ""
        return asn, self._holders[asn]


GLEIF_API = "https://api.gleif.org/api/v1"


class GleifApi:
    """Offene Schnittstelle der Global Legal Entity Identifier Foundation (GLEIF)."""

    def __init__(self) -> None:
        self._client = httpx2.Client(timeout=HTTP_TIMEOUT)

    def by_register(self, register: str) -> list[LeiRecord]:
        return self._records({"filter[entity.registeredAs]": register})

    def by_name(self, name: str) -> list[LeiRecord]:
        return self._records({"filter[entity.legalName]": name})

    def ultimate_parent(self, lei: str) -> LeiRecord | None:
        response = self._client.get(f"{GLEIF_API}/lei-records/{lei}/ultimate-parent")
        if response.status_code == 404:  # keine Konzernmutter gemeldet
            return None
        response.raise_for_status()
        return _record(response.json()["data"])

    def _records(self, params: dict[str, str]) -> list[LeiRecord]:
        response = self._client.get(f"{GLEIF_API}/lei-records", params={**params, "page[size]": 20})
        response.raise_for_status()
        return [_record(item) for item in response.json()["data"]]


def _record(item: dict) -> LeiRecord:
    entity = item["attributes"]["entity"]
    return LeiRecord(
        lei=item["id"],
        name=entity["legalName"]["name"],
        city=entity["legalAddress"].get("city") or "",
        country=entity["legalAddress"].get("country") or "",
        registered_as=entity.get("registeredAs"),
    )
