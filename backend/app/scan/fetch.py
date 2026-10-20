"""Sicheres Laden fremder Seiten.

Wer eine Domain eingeben kann, könnte versuchen, über das Tool interne Systeme abzufragen
(Server-Side Request Forgery). Deshalb gilt für jede Anfrage und jede Weiterleitung:
nur http und https, nur die Standardports, und jeder Hostname muss ausschließlich auf
öffentliche Adressen zeigen. Dazu kommen Grenzen für Zeit, Größe und Weiterleitungen.

Verbleibende Lücke: Zwischen der eigenen Namensauflösung und der Verbindung könnte ein
Angreifer die Auflösung ändern (DNS-Rebinding). Für einen Prototyp ist das hinnehmbar,
für den Betrieb gehört der Abruf in eine abgeschottete Umgebung ohne Zugang zum internen Netz.
"""

import ipaddress
from urllib.parse import urljoin, urlsplit

import httpx2

from app.scan import Resolver, is_public_ip
from app.scan.website import MAX_BYTES, BlockedAddress, Page

TIMEOUT = 8
MAX_REDIRECTS = 4
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "de,en;q=0.8",
}


def check_url(url: str, resolver: Resolver) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise BlockedAddress(f"Nur http und https sind erlaubt: {url}")
    if parts.port not in {None, 80, 443}:
        raise BlockedAddress(f"Nur die Standardports sind erlaubt: {url}")
    host = parts.hostname or ""
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise BlockedAddress(f"Nur Hostnamen sind erlaubt, keine IP-Adressen: {url}")
    if not host:
        raise BlockedAddress(f"Die Adresse hat keinen Hostnamen: {url}")
    addresses = resolver.lookup(host, "A") + resolver.lookup(host, "AAAA")
    if not addresses or not all(is_public_ip(address) for address in addresses):
        raise BlockedAddress(f"{host} zeigt nicht ausschließlich auf öffentliche Adressen.")


class SafeFetcher:
    def __init__(self, resolver: Resolver) -> None:
        self._resolver = resolver
        self._client = httpx2.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=False)

    def fetch(self, url: str) -> Page:
        for _ in range(MAX_REDIRECTS + 1):
            check_url(url, self._resolver)
            with self._client.stream("GET", url) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                body = b""
                for chunk in response.iter_bytes():
                    body += chunk
                    if len(body) > MAX_BYTES:
                        body = body[:MAX_BYTES]  # ein einzelner Block kann größer sein
                        break
                kind = response.headers.get("content-type", "")
                html = (
                    body.decode(response.encoding or "utf-8", "replace") if "html" in kind else ""
                )
                return Page(url=str(response.url), status=response.status_code, html=html)
        raise BlockedAddress(f"Zu viele Weiterleitungen ab {url}")
