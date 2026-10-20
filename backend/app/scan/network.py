"""Echte Abfragen für den Außenscan: DNS und RIPEstat. In Tests ersetzt durch Attrappen."""

import dns.resolver
import httpx2

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

    def network(self, ip: str) -> tuple[int, str] | None:
        info = self._client.get(f"{RIPESTAT}/network-info/data.json", params={"resource": ip})
        info.raise_for_status()
        asns = info.json()["data"].get("asns") or []
        if not asns:
            return None
        asn = int(asns[0])
        overview = self._client.get(
            f"{RIPESTAT}/as-overview/data.json", params={"resource": f"AS{asn}"}
        )
        overview.raise_for_status()
        return asn, overview.json()["data"].get("holder") or ""
