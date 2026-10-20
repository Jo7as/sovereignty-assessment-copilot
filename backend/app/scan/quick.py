"""Schnellcheck: Außenscan, Unternehmensprofil und Vorschläge in einem Durchlauf.

Die Schritte stehen in STEPS und werden über `on_step` gemeldet, damit die Oberfläche beim
Warten zeigt, was tatsächlich gerade passiert.
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.scan import STEPS as SCAN_STEPS
from app.scan import NetworkLookup, Resolver, ScanResult, scan
from app.scan.profile import CompanyProfile, Gleif, build_profile, looks_like_imprint
from app.scan.suggest import Suggester, Suggestions, suggest
from app.scan.website import PageFetcher, visible_text

STEPS = (*SCAN_STEPS, "Impressum und Register prüfen", "Branche und Größe vorschlagen")
IMPRINT_FALLBACKS = ("/impressum", "/impressum/", "/imprint")


@dataclass
class QuickCheck:
    scan: ScanResult
    profile: CompanyProfile
    suggestions: Suggestions


def run_quick_check(
    domain: str,
    resolver: Resolver,
    networks: NetworkLookup,
    fetcher: PageFetcher,
    gleif: Gleif,
    suggester: Suggester | None,
    sectors: dict[str, str],
    on_step: Callable[[str], None] = lambda step: None,
) -> QuickCheck:
    result = scan(domain, resolver, networks, fetcher, on_step)

    on_step(STEPS[4])
    imprint_url, imprint_text = _load_imprint(result, fetcher)
    profile = build_profile(imprint_text, imprint_url, gleif)

    on_step(STEPS[5])
    if suggester is None:
        suggestions = Suggestions(note="Ohne KI-Schlüssel gibt es keine Vorschläge.")
    else:
        text = " | ".join(part for part in (result.home_text, imprint_text) if part)
        suggestions = suggest(text, sectors, suggester)
    return QuickCheck(result, profile, suggestions)


def _load_imprint(result: ScanResult, fetcher: PageFetcher) -> tuple[str | None, str | None]:
    """Impressum über den Link der Startseite, sonst über die üblichen Adressen."""
    candidates = list(result.imprint_urls[:3])
    candidates += [
        f"https://{host}{path}"
        for host in (result.domain, f"www.{result.domain}")
        for path in IMPRINT_FALLBACKS
    ]
    for url in dict.fromkeys(candidates):
        try:
            page = fetcher.fetch(url)
        except Exception:  # noqa: BLE001 - gesperrt oder nicht erreichbar: nächste Adresse
            continue
        text = visible_text(page.html) if page.status < 400 else ""
        if text and looks_like_imprint(text):
            return page.url, text
    return None, None
