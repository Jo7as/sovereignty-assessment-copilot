# Testverträge und Musterlösung

Grundlage, um die Trefferquote der Vertragsanalyse zu messen (`docs/tiefenpruefung-ablauf.md`, Abschnitt 9).

- `sources.yaml`: die vier Testverträge mit Adresse und Prüfsumme. Die PDFs selbst liegen nicht im Repository. Laden mit `cd backend && uv run python scripts/fetch_contracts.py`.
- `gold/<id>.yaml`: die Musterlösung je Vertrag.

## Format der Musterlösung

```yaml
status: ENTWURF          # ENTWURF, bis ein Mensch die Lösung geprüft hat, danach GEPRUEFT
fields:
  data_location:
    value: EU_WAEHLBAR   # erwarteter Wert oder NICHT_GEFUNDEN
    also_correct: []     # weitere vertretbare Werte, optional
    evidence:            # alle Stellen, die den Wert tragen
      - page: 5          # physische Seite im PDF, gezählt ab 1
        quote: "Customer can specify the location(s) where Customer Data will be processed"
    note: "…"            # Begründung bei Auslegungsfragen, optional
```

Gelabelt werden die Felder der Themenblöcke für den Dokumenttyp AVV (Arbeitsanweisung 5.2): die Bewertungsfakten aus 6.1 (ohne Unterauftragnehmer-Liste), vier Punkte aus DORA Art. 30 und alle acht Punkte aus DSGVO Art. 28 Abs. 3.

## Regeln für die Musterlösung

- **Nur ausdrückliche Aussagen.** Ein Wert gilt nur, wenn das Dokument ihn ausdrücklich nennt. Was man nur ableiten kann (etwa „Nutzung nur zur Leistungserbringung, also wohl kein KI-Training“), ist `NICHT_GEFUNDEN`. Die KI soll dasselbe tun, sonst wäre der Vergleich unfair.
- **Verweise zählen nicht.** Steht der Wert nur in einem verlinkten Dokument (etwa der Liste der Unterauftragnehmer auf einer Website), ist er `NICHT_GEFUNDEN`.
- **Prüfpunkte** (`dora_*`, `dsgvo_*`): `VORHANDEN`, wenn der Punkt geregelt ist; `TEILWEISE`, wenn er geregelt, aber deutlich eingeschränkt ist (z. B. Prüfung nur über Berichte des Anbieters, nur Löschung statt Rückgabe); `NICHT_GEFUNDEN`, wenn das Dokument ihn nicht regelt.
- **Zitate** stehen so im Dokument, wie sie gedruckt sind. Leerraum und Trennstriche zählen beim Vergleich nicht, weil die Textauslese aus PDFs sie verändert. Ein Test prüft jedes Zitat gegen die genannte Seite, wenn die PDFs geladen sind.

Die Musterlösung hat Claude am 9.11.2026 beim Aufbau erstellt (ein anderes und größeres Modell als das der Vertragsanalyse). Sie steht auf `ENTWURF`, bis Jonas sie geprüft hat. Auslegungsfragen sind im Feld `note` begründet.
