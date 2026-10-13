# Coding-Plan: Sovereignty Assessment Copilot

Gilt zusammen mit der CLAUDE.md. Jede Phase besteht aus kleinen Schritten. Ein Schritt wird erst begonnen, wenn der vorige getestet ist und Jonas ihn freigegeben hat. Erledigte Schritte bitte abhaken.

Jede Phase endet mit einer Interview-Notiz: Welche Entscheidung wurde getroffen, und warum? Das wird später die Grundlage für die Fallstudie.

---

## Phase 0: Projekt aufsetzen
- [x] 0.1 Ordnerstruktur anlegen: `backend/` (mit `tests/`), `frontend/`, `data/`, `docs/`
- [x] 0.2 Git initialisieren, `.gitignore`, GitHub-Repository anlegen
- [x] 0.3 Python-Umgebung mit uv, `pyproject.toml` und `uv.lock`
- [x] 0.4 Minimale FastAPI-App mit `/health`-Endpunkt
- [x] 0.5 PostgreSQL per Docker Compose starten und Verbindung testen

**Fertig, wenn:** `GET /health` antwortet und die Datenbank erreichbar ist.

## Phase 1: Datenmodell und Anbieterdatenbank
- [x] 1.1 Datenmodell entwerfen und besprechen: Anbieter, Mutterkonzern, Dienst, Variante, Kategorie, Zertifikat, Abhängigkeit, EU-Alternative, Nachweis (siehe `docs/datenmodell.md`)
- [ ] 1.2 Modelle mit SQLAlchemy umsetzen, Migrationen mit Alembic
- [ ] 1.3 Seed-Format festlegen (YAML oder CSV in `data/`), damit die Daten auch ohne Code pflegbar sind
- [ ] 1.4 Erste 20 Dienste von Hand erfassen (Microsoft 365, SAP, Salesforce, AWS, Google Workspace, DATEV, Personio …), jeweils mit Quelle
- [ ] 1.5 Seed-Skript, das die Daten in die Datenbank lädt
- [ ] 1.6 Auf 150 Dienste erweitern (KI darf vorschlagen, jeder Eintrag wird geprüft)

**Fertig, wenn:** 150 Dienste mit Mutterkonzern, Rechtsraum, Kritikalität und mindestens einer EU-Alternative in der Datenbank stehen.

## Phase 2: IT-Bestand und Testdaten
- [ ] 2.1 Excel-Vorlage für den IT-Bestand definieren (Dienst, Zweck, Abteilung, Kritikalität, Datenarten)
- [ ] 2.2 Fiktive Bank „Musterbank AG“ mit ca. 60 Diensten als Testdatei anlegen
- [ ] 2.3 Import-Endpunkt: Excel/CSV hochladen und einlesen
- [ ] 2.4 Normalisierung: Freitext wie „O365“ oder „Teams“ einem Dienst zuordnen (erst unscharfer Textvergleich, dann KI als Rückfall). Dafür die KI-Anbindung als austauschbares Modul anlegen (zuerst Claude API; OpenRouter als Option für Modellvergleiche, später ein in der EU betriebenes Modell wie Mistral)
- [ ] 2.5 Nicht zugeordnete Einträge als „zur Prüfung“ markieren

**Fertig, wenn:** Die Musterbank-Datei vollständig importiert ist und mindestens 90 % der Einträge automatisch zugeordnet werden.

## Phase 3: Außenscan
- [ ] 3.1 DNS-Abfragen (MX, NS, A, TXT/SPF) mit dnspython
- [ ] 3.2 IP zu Netzbetreiber (ASN) über die RIPEstat-API
- [ ] 3.3 Website laden mit Playwright und Drittanbieter-Requests sammeln
- [ ] 3.4 Funde den Diensten der Anbieterdatenbank zuordnen
- [ ] 3.5 Ergebnis als Vorschlag für die Dienstliste zurückgeben

**Fertig, wenn:** Für drei echte Domains eine plausible Dienstliste herauskommt, mit Fundstelle je Dienst.

## Phase 4: Fragebogen
- [ ] 4.1 Rund 25 Fragen als YAML definieren (Ziele, Risikotoleranz, Branche, Notfallplan, Exit-Strategie)
- [ ] 4.2 Endpunkte zum Laden der Fragen und Speichern der Antworten
- [ ] 4.3 Branche bestimmt, ob NIS2 und/oder DORA gelten

**Fertig, wenn:** Ein Assessment mit Fragebogen-Antworten gespeichert werden kann.

## Phase 5: Bewertungslogik
- [ ] 5.1 Regeln für die Stufe 0 bis 4 je Zielbereich als eigenes, gut lesbares Modul
- [ ] 5.2 Gesamtstufe je Dienst = schwächster Zielbereich
- [ ] 5.3 Gewichtung nach Kritikalität und Gesamtwert für das Unternehmen
- [ ] 5.4 NIS2- und DORA-Hinweise je nach Branche
- [ ] 5.5 Unit-Tests mit pytest für alle Regeln, inklusive Grenzfällen

**Fertig, wenn:** Die Musterbank eine nachvollziehbare Bewertung erhält und alle Tests grün sind.

## Phase 6: Roadmap
- [ ] 6.1 Priorisierung: hohe Kritikalität und niedrige Stufe zuerst
- [ ] 6.2 Pro Dienst EU-Alternative und grober Migrationsaufwand
- [ ] 6.3 Einteilung in drei Wellen (schnelle Erfolge, mittelfristig, strategisch)

**Fertig, wenn:** Für die Musterbank eine Roadmap mit drei Wellen entsteht, die ein Berater so zeigen würde.

## Phase 7: Oberfläche (Next.js)
- [ ] 7.1 Projekt aufsetzen, Verbindung zur API
- [ ] 7.2 Ablauf: Domain eingeben, Dienste bestätigen, Fragebogen, Ergebnis
- [ ] 7.3 Heatmap Dienste × Zielbereiche
- [ ] 7.4 Roadmap-Ansicht
- [ ] 7.5 Sauberes, seriöses Design (Beraterstil, keine Spielerei)

**Fertig, wenn:** Ein kompletter Durchlauf mit der Musterbank im Browser funktioniert.

## Phase 8: Bericht
- [ ] 8.1 PDF-Bericht: Zusammenfassung, Heatmap, Top-Risiken, Roadmap, Methodik
- [ ] 8.2 Hinweis zu Grenzen und dazu, dass es keine Rechtsberatung ist

**Fertig, wenn:** Das PDF ohne Erklärung verständlich ist.

## Phase 9: Stufe 3, Vertragsanalyse
- [ ] 9.1 KI-Modul aus 2.4 um strukturierte Ausgaben mit Seitenangabe erweitern
- [ ] 9.2 Testverträge sammeln: öffentlich verfügbare Auftragsverarbeitungsverträge von Microsoft, AWS, Salesforce und zwei EU-Anbietern
- [ ] 9.3 PDF hochladen und Text extrahieren
- [ ] 9.4 KI extrahiert Datenstandort, Unterauftragnehmer, Gerichtsstand, Kündigungsfristen und Exit-Regeln als strukturierte Daten, jeweils mit Seitenangabe
- [ ] 9.5 Prüfansicht: Der Berater bestätigt oder korrigiert jede Aussage
- [ ] 9.6 Bestätigte Vertragsdaten fließen in die Bewertung ein
- [ ] 9.7 Qualität messen: Für die Testverträge eine von Hand erstellte Lösung anlegen und die Trefferquote der KI ausrechnen

**Fertig, wenn:** Die KI für die Testverträge mindestens 90 % der Angaben richtig findet und jede Angabe auf ihre Fundstelle verweist. Die gemessene Quote ist ein starkes Argument im Interview.

## Phase 10: Stufe 3, DORA-Register und Workshop-Präsentation
- [ ] 10.1 Entwurf des DORA-Informationsregisters aus IT-Bestand und Vertragsdaten erzeugen (Excel)
- [ ] 10.2 Workshop-Präsentation mit python-pptx: Ausgangslage, Heatmap, Top-Risiken, Roadmap, offene Fragen für den Workshop
- [ ] 10.3 Vollständiger Durchlauf der Musterbank durch alle drei Stufen

**Fertig, wenn:** Die Musterbank einen vollständigen Bericht, einen Registerentwurf und eine Präsentation erhält, die ein Berater direkt im Workshop zeigen könnte.

## Phase 11: Für die Bewerbung verpacken
- [ ] 11.1 README mit Problem, Lösung, Screenshots, Architektur, Grenzen
- [ ] 11.2 Online stellen (z. B. Render oder Fly.io), damit Recruiter es ausprobieren können
- [ ] 11.3 Demo-Video, 2 bis 3 Minuten
- [ ] 11.4 Einseitige Fallstudie „Musterbank AG“ im Beraterstil
- [ ] 11.5 Zwei bis drei Sätze für Lebenslauf und Anschreiben

---

## Später, nur bei echter Nachfrage
EU-Hosting (z. B. Hetzner oder IONOS), Wechsel auf ein in der EU betriebenes KI-Modell, Benutzerkonten und Bezahlung, n8n-Workflow, der Anbieter regelmäßig auf Änderungen prüft.
