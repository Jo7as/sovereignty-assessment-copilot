# Sovereignty Assessment Copilot

Projektkontext für Claude Code. Diese Datei in den Projektordner legen, Claude liest sie bei jedem Start.

## Ziel
Portfolio-Projekt für die Bewerbung als Praktikant/Werkstudent in der Strategie- und Managementberatung bei Capgemini Invent. Es soll zeigen: Geschäftsproblem verstehen, Methodik entwickeln, mit KI umsetzen, Nutzen belegen. Das Tool soll außerdem Potenzial zur Vermarktung haben.

## Idee
Ein Tool, das die Abhängigkeit eines Unternehmens von außereuropäischen IT-Anbietern bewertet und eine Roadmap ableitet. Es ist eine automatisierte Variante von Capgeminis 30-tägigem „Digital Sovereignty Assessment“.

Abgrenzung zu meetergo (scan.meetergo.com, kostenlos): meetergo prüft von außen nur die Website (DNS, Hosting, Tracker). Wir prüfen von innen: IT-Bestand, Verträge, Organisation. Bewertet wird nach den acht Zielbereichen des EU Cloud Sovereignty Framework (v1.2.1, Okt. 2025), dazu NIS2 und DORA. meetergo nicht kopieren, sondern ergänzen.

## Nutzungsstufen
1. Schnellcheck: Domain eingeben, Außenscan füllt die Dienstliste vor, weitere Dienste aus einer Liste anklicken. Keine Unterlagen.
2. Assessment: zusätzlich Fragebogen (Kritikalität, Ziele, Exit-Strategie). Standardverträge großer Anbieter sind im Tool hinterlegt. Keine Unterlagen.
3. Tiefenprüfung: echter IT-Bestand (Excel/CSV) und Verträge hochladen, KI-Vertragsanalyse. Kommt nach den Stufen 1 und 2 (PLAN.md, Phasen 9 und 10).

## Bewertung
- Acht Zielbereiche: Strategisch, Rechtlich, Daten und KI, Operativ, Lieferkette, Technologie, Sicherheit und Compliance, Umwelt
- Pro Dienst und Bereich eine Stufe 0 bis 4 (SEAL), die Gesamtstufe eines Dienstes ist die schwächste der sieben Bereiche ohne Umwelt. Umwelt zählt nur im Souveränitätswert (0 bis 100, Gewichte des Rahmenwerks)
- Unsere Auslegung der Stufen: 0 = Nicht-EU ohne Schutz, 1 = Nicht-EU mit EU-Rechenzentrum und Standardvertragsklauseln, 2 = Nicht-EU mit EU-Betriebsgesellschaft, eigener Schlüsselverwaltung und Exit, oder EU-Anbieter mit kritischer Nicht-EU-Abhängigkeit, 3 = EU-Anbieter mit einzelnen, nicht kritischen Nicht-EU-Abhängigkeiten oder mit proprietärer Technik, 4 = vollständig EU und offen. Regeln im Detail: docs/bewertungslogik.md
- Gewichtung nach Kritikalität (gering, mittel, hoch), Ausgabe als Heatmap Dienste × Zielbereiche
- Maßgeblich ist der Rechtsraum des Mutterkonzerns (CLOUD Act), nicht der Serverstandort

## Umfang der Stufen 1 und 2
- Anbieterdatenbank: zuerst die rund 50 bis 60 Dienste, die die Musterbank braucht, danach Ausbau auf ca. 150 häufige Unternehmensdienste. Je Dienst Mutterkonzern, Sitzland, Zertifikate (C5, ISO 27001), Kritikalität, EU-Alternativen (Entscheidung vom 14.10.2026: vom Ergebnis her planen, erst ein vollständiger Durchlauf mit der Musterbank)
- Vorlage für den IT-Bestand plus Testdaten: fiktive kleine Bank mit ca. 60 Diensten
- Außenscan (DNS, Hosting/ASN, Website-Dienste), Dienstauswahl, Fragebogen, Bewertung, Heatmap, Roadmap

## Tech-Stack
Python mit FastAPI, PostgreSQL, Next.js als Oberfläche, python-pptx für die Workshop-Präsentation (Phase 10). KI für Zuordnung und Vertragsanalyse über ein austauschbares Modul: zuerst Claude API, OpenRouter als Option, später ein in der EU betriebenes Modell.

## Arbeitsweise
- In kleinen Schritten arbeiten: jeden Schritt kurz erklären und auf Jonas' Okay warten, bevor er umgesetzt wird
- Entscheidungen begründen, damit Jonas sie im Interview erklären kann
- KI-Aussagen immer mit Quelle oder Fundstelle versehen. Bei den Anbieterdaten prüft die KI ihre Quellen in einem zweiten Durchgang selbst nach (Status `KI_NACHGEPRUEFT`), eine Bestätigung durch einen Menschen (`GEPRUEFT`) ist dort freiwillig. Der Status wird im Tool ausgewiesen
- Erster Schritt: Projektstruktur anlegen und das Datenmodell der Anbieterdatenbank entwerfen

## Ausführliche Methodik
Siehe Dokument „Sovereignty Assessment Copilot: Methodik“: https://claude.ai/code/artifact/0c4b9f36-9a69-425f-979b-910975a98d2c
