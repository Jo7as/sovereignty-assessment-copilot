"""Sucht Fundstellen auf einer Seite, als Hilfe bei der Recherche für die Anbieterdaten.

Aufruf im Ordner backend/:
    uv run python scripts/find_quote.py URL "Suchmuster" ["weiteres Suchmuster" ...]

Lädt die Seite genauso wie verify_evidence.py, damit eine gefundene Fundstelle später
auch die Nachprüfung besteht. Suchmuster sind reguläre Ausdrücke, Groß- und
Kleinschreibung zählt nicht.
"""

import re
import sys

from verify_evidence import page_text

CONTEXT = 200
MAX_HITS = 2


def main(url: str, patterns: list[str]) -> int:
    try:
        text = re.sub(r"\s+", " ", page_text(url))
    except Exception as error:  # noqa: BLE001 - jede Abruf-Störung wird gemeldet
        print(f"=== {url}\nNICHT ABRUFBAR: {error}")
        return 1
    print(f"=== {url} [{len(text)} Zeichen]")
    for pattern in patterns:
        hits = list(re.finditer(pattern, text, re.IGNORECASE))
        print(f"--- {pattern!r}: {len(hits)} Treffer")
        for hit in hits[:MAX_HITS]:
            start, end = max(0, hit.start() - CONTEXT), hit.end() + CONTEXT
            print(f"   …{text[start:end]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2:]))
