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
- [x] 1.2 Modelle mit SQLAlchemy umsetzen, Migrationen mit Alembic
- [x] 1.3 Seed-Format festlegen: YAML in `data/`, eine Datei je Dienst, beschrieben in `data/README.md`
- [x] 1.4 Erste 20 Dienste erfassen (Microsoft 365, SAP, Salesforce, AWS, Google Workspace, DATEV, Personio …), Pflichtangaben mit nachgeprüfter Quelle
- [x] 1.5 Seed-Skript, das die Daten in die Datenbank lädt
- [ ] 1.6 Erweitern: zuerst die Dienste aus dem Bestand der Musterbank (2.2), später auf 150 (KI recherchiert, prüft sich selbst nach)
  - Am 14.10.2026 erledigt: alle 30 fehlenden Dienste der Musterbank angelegt (50 Dienste insgesamt). Belegt sind vor allem Eigentum, Übermittlungsgrundlage und Hosting-Abhängigkeiten. Datenstandort, Schlüssel und Zertifikate fehlen bei den meisten neuen Diensten noch
- [ ] 1.7 Offene Angaben der ersten 20 Dienste nachtragen:
  - ServiceNow und ChatGPT Enterprise: Seiten nicht automatisch abrufbar, bisher ohne Merkmale
  - Übermittlungsgrundlage, Gerichtsstand, Datenexport, KI-Training, erneuerbare Energie: bei fast allen Diensten offen
  - Schlüsselverwaltung offen bei DATEV, Salesforce, SAP, IONOS, Zoom, STACKIT, T Cloud Public, OVHcloud, GitHub
  - Zertifikate offen bei Salesforce, STACKIT und OVHcloud (C5)
  - T Cloud Public: Technologie-Abhängigkeiten prüfen
  - Am 14.10.2026 nachgetragen: Übermittlungsgrundlage bei 9 US-Anbietern, erneuerbare Energie bei Microsoft, Amazon und Google, Vertragsrecht bei DATEV, IONOS und T Cloud Public, KI-Training bei Personio
  - Am 14.10.2026 zusätzlich: Datenexport bei IONOS und OVHcloud, Offenheit bei STACKIT, T Cloud Public und OVHcloud, Betrieb bei T Cloud Public, KI-Training bei Nextcloud, Azure-Abhängigkeit des DATEV Copilot
  - Noch offen für die EU-Anbieter (hebt deren gesicherte Stufe über 1): KI-Training (alle außer Personio und Nextcloud), Ort von Betrieb und Support (alle außer T Cloud Public), Datenexport (DATEV, Personio, SAP, STACKIT, T Cloud Public), Vertragsrecht (Personio, SAP, STACKIT, OVHcloud, Nextcloud)
  - Öffentlich kaum belegbar, vermutlich nur über Vertragsunterlagen oder Anfrage beim Anbieter: Ort von Betrieb und Support, KI-Training bei Infrastrukturanbietern
  - Noch offen: Übermittlungsgrundlage bei GitHub und der AWS European Sovereign Cloud, erneuerbare Energie bei den übrigen Anbietern
  - Zulieferer vollständig prüfen und `dependencies_complete` setzen
  - Schwächere Belege ersetzen: Konzernmutter von Google Cloud EMEA und Microsoft Ireland, Datenstandort DATEV

**Fertig, wenn:** 150 Dienste mit Mutterkonzern, Rechtsraum, Kritikalität und mindestens einer EU-Alternative in der Datenbank stehen.

## Phase 2: IT-Bestand und Testdaten
- [x] 2.1 Excel-Vorlage für den IT-Bestand definieren (Dienst, Zweck, Abteilung, Kritikalität, Datenarten), anschlussfähig an das DORA-Informationsregister: `data/templates/it-bestand-vorlage.xlsx`
- [x] 2.2 Fiktive Bank „Musterbank AG“ mit ca. 60 Diensten als Testdatei anlegen: 58 Einträge, 47 Dienste, Quelle `data/testdata/musterbank.yaml` mit erwarteter Zuordnung je Eintrag
- [x] 2.3 Import-Endpunkt: Excel/CSV hochladen und einlesen (`POST /inventory/import`, prüft und meldet Fehler zeilengenau, speichert noch nicht)
- [x] 2.4 Normalisierung: Freitext wie „O365“ oder „Teams“ einem Dienst zuordnen (erst unscharfer Textvergleich, dann KI als Rückfall). Dafür die KI-Anbindung als austauschbares Modul anlegen (zuerst Claude API; OpenRouter als Option für Modellvergleiche, später ein in der EU betriebenes Modell wie Mistral)
- [x] 2.5 Nicht zugeordnete Einträge als „zur Prüfung“ markieren (Feld `needs_review` je Eintrag im Import)

**Fertig, wenn:** Die Musterbank-Datei vollständig importiert ist und mindestens 90 % der Einträge automatisch zugeordnet werden.

## Phase 3: Außenscan
- [x] 3.1 DNS-Abfragen (MX, NS, A, TXT/SPF) mit dnspython
- [x] 3.2 IP zu Netzbetreiber (ASN) über die RIPEstat-API
- [x] 3.3 Website laden und eingebundene Dienste sammeln (ohne Playwright: das HTML reicht für Skripte, Iframes und Stylesheets, ein Browser auf dem Server wäre langsam und schwer abzusichern)
- [x] 3.4 Funde den Diensten der Anbieterdatenbank zuordnen
- [x] 3.6 Unternehmensprofil: Impressum (Name, Register, BaFin, USt-ID), Abgleich mit GLEIF (LEI, Konzernmutter), Vorschläge der KI für Branche und Beschäftigte mit geprüftem Zitat
- [x] 3.5 Schnellcheck in der Oberfläche: Website eingeben, echte Schritte beim Warten, Ergebnis mit Profil, Diensten, Belegen und übrigen Funden, Übergabe ins Assessment mit Startbestand und Vorschlägen

**Fertig, wenn:** Für drei echte Domains eine plausible Dienstliste herauskommt, mit Fundstelle je Dienst.

## Phase 4: Fragebogen
- [x] 4.1 Rund 25 Fragen als YAML definieren (Ziele, Risikotoleranz, Branche, Notfallplan, Exit-Strategie)
- [x] 4.2 Endpunkte zum Laden der Fragen und Speichern der Antworten
- [x] 4.3 Branche bestimmt, ob NIS2 und/oder DORA gelten

- [x] 4.4 IT-Bestand und Zuordnung am Assessment speichern, Gesamtergebnis aus Bestand, Fragebogen und Rechtslage

**Fertig, wenn:** Ein Assessment mit Fragebogen-Antworten gespeichert werden kann.

## Phase 5: Bewertungslogik
- [x] 5.1 Regeln für die Stufe 0 bis 4 je Zielbereich als eigenes, gut lesbares Modul
- [x] 5.2 Gesamtstufe je Dienst = schwächster Zielbereich
- [x] 5.3 Gewichtung nach Kritikalität und Gesamtwert für das Unternehmen
- [x] 5.4 NIS2- und DORA-Hinweise je nach Branche
- [x] 5.5 Unit-Tests mit pytest für alle Regeln, inklusive Grenzfällen (für 5.1 bis 5.4 erledigt)

**Fertig, wenn:** Die Musterbank eine nachvollziehbare Bewertung erhält und alle Tests grün sind.

Stand 19.10.2026: Die Bewertung der Musterbank läuft (`uv run python -m app.assessment`, `POST /assessments/preview`). Nach der Datenrunde für die 20 hoch kritischen Dienste stehen noch 10 von ihnen gesichert auf Stufe 0. Bei fast allen sperren die Anbieter automatische Abrufe oder veröffentlichen den Datenstandort nicht. Diese Lücken gehören in den Fragenkatalog an die Anbieter (Phase 6).

## Phase 6: Roadmap
- [x] 6.1 Priorisierung: hohe Kritikalität und niedrige Stufe zuerst (Kritikalität mal Abstand zur Höchststufe)
- [x] 6.2 Pro Dienst EU-Alternative und grober Migrationsaufwand, dazu Wechsel der Variante beim selben Anbieter
- [x] 6.3 Einteilung in drei Wellen (schnelle Erfolge, mittelfristig, strategisch)
- [x] 6.4 Fragenkatalog an die Anbieter aus den Lücken der Bewertung, mit Kernfragen je Anbieter
- [x] 6.5 EU-Alternativen für weitere Dienste der Musterbank ergänzen: 11 neue Dienste (cidaas, Myra, OpenProject, Passbolt, Matrix42, Yousign, Conceptboard, Mistral Vibe, Hawk, maincubes, alfaview), Alternativen jetzt für 18 Dienste. Ohne prüfbare Belege nicht aufgenommen: WithSecure, Logpoint, Brevo, Circula. Bewusst ohne Alternative: SWIFT, Mastercard, Bloomberg, LSEG, Avaloq

**Fertig, wenn:** Für die Musterbank eine Roadmap mit drei Wellen entsteht, die ein Berater so zeigen würde.

## Phase 7: Oberfläche (Next.js)
- [x] 7.1 Projekt aufsetzen, Verbindung zur API (Next.js 16, CORS im Backend)
- [x] 7.2 Ablauf: Assessment anlegen, Fragebogen, IT-Bestand, Ergebnis mit Heatmap, Roadmap, Rechtslage und Reifegrad. Musterbank und Vorschau ohne Speichern. Domain eingeben und Dienste bestätigen folgen mit Phase 3
- [x] 7.3 Heatmap Dienste × Zielbereiche, mit Erklärung beim Darüberfahren und Detailansicht mit Belegen
- [x] 7.4 Roadmap-Ansicht mit Wirkung der Maßnahmen und Fragenkatalog
- [x] 7.5 Sauberes, seriöses Design (Beraterstil, keine Spielerei), hell und dunkel, auf dem Handy nutzbar
- [x] 7.6 Startseite mit Nutzen, Ablauf und Abgrenzung zu meetergo, Gestaltungsdurchgang über alle Seiten (Ziel: so professionell wie scan.meetergo.com, ohne es zu kopieren)

**Fertig, wenn:** Ein kompletter Durchlauf mit der Musterbank im Browser funktioniert.

## Phase 8: Bericht
- [x] 8.1 PDF-Bericht: Zusammenfassung, Heatmap, Top-Risiken, Roadmap, Methodik (2.11.2026). Bausteine im Backend (`app/report`, feste Regeln statt KI), Berichtsseite mit Druck-CSS unter `/assessments/[id]/bericht` und `/beispiel/bericht`. Musterbank: 21 Seiten, davon 9 Hauptteil
- [x] 8.2 Hinweis zu Grenzen und dazu, dass es keine Rechtsberatung ist: Seite „Methodik und Grenzen“ mit Prüfstatus und nicht zugeordneten Einträgen, Quellenverzeichnis als Anhang C
- [x] 8.3 Alle 15 Dienste mit Status KI_VORSCHLAG an den Quellen nachgeprüft (4. bis 8.11.2026). Was sich nicht belegen ließ (z. B. SCHUFA, Bloomberg, gesperrte Seiten bei OpenAI und Adobe), bleibt offen und geht in den Fragenkatalog. Beispielbericht neu erzeugt, jetzt 22 Seiten

**Fertig, wenn:** Das PDF ohne Erklärung verständlich ist.

## Phase 9: Stufe 3, Vertragsanalyse
- [x] 9.0 Arbeitsanweisung für den Ablauf: `docs/tiefenpruefung-ablauf.md` (9.11.2026). Fester Workflow in sieben Schritten statt freiem Agenten, Felder aus Bewertung, DORA Art. 30, DSGVO Art. 28 Abs. 3 und Register B_02.02, Wortlaute an den amtlichen Fassungen geprüft
- [x] 9.1 KI-Modul aus 2.4 um strukturierte Ausgaben mit Seitenangabe erweitern (9.11.2026): `ai.structured()` mit Pydantic-Modell als Schema und Prüfung, eine Nachfrage bei ungültiger Antwort, Rückfall ohne Schema. Belegprüfung gemeinsam in `app/matching/quotes.py`, erkennt jetzt Silbentrennung aus PDFs. Probelauf mit DeepSeek V4.1 Flash: Schema wird von Anbietern ohne Datenspeicherung angenommen, Antwort in etwa 2 Sekunden
- [x] 9.2 Testverträge sammeln (9.11.2026): AVVs von AWS, Salesforce, Hetzner und STACKIT, Quellen mit Prüfsumme in `data/testdata/contracts/sources.yaml`, PDFs per `scripts/fetch_contracts.py` (nicht im Repo). Musterlösung mit 72 Angaben in `gold/`, Status ENTWURF bis zur Prüfung durch Jonas. Microsoft nur als Word-Datei, Personio sperrt den Abruf, DATEV nur über Formular
- [x] 9.3 PDF hochladen und Text extrahieren (9.11.2026): Tabelle `assessment_contract` mit Datei und Text je PDF-Seite, Endpunkte `POST/GET /assessments/{id}/contracts` und `DELETE …/contracts/{id}`. PDFs ohne Text werden abgelehnt, Seiten ohne Text gemeldet. Probe mit den vier Testverträgen: alle Seiten gelesen, 2 bis 6 Sekunden je Vertrag
- [ ] 9.4 KI extrahiert Datenstandort, Unterauftragnehmer, Gerichtsstand, Kündigungsfristen und Exit-Regeln als strukturierte Daten, jeweils mit Seitenangabe
  - [x] Einordnen, Auslesen, Belegprüfung (10.11.2026): Feldkatalog `app/contracts/fields.py` (7 Bewertungsfakten, 16 DORA-Punkte, 8 DSGVO-Punkte, Routing nach Dokumenttyp), Ablauf `app/contracts/pipeline.py` mit Protokoll `Extractor`. Probe mit dem Hetzner-AVV: Dienst und Typ richtig eingeordnet, 30 Angaben, keine an der Belegprüfung gescheitert, rund 7 Minuten
  - [x] Zusammenführen, Läufe und Endpunkte (10.11.2026): Tabellen `contract_run` (Status, Prompt-Version, Modell, Protokoll je Themenblock) und `contract_finding` (Feld, Wert, Zitat, Seite, Status). Einordnungsvorschlag beim Hochladen, Bestätigung per `PUT …/contracts/{id}`, Lauf im Hintergrund per `POST …/contracts/{id}/runs`, Ergebnis je Dienst mit Widersprüchen als UNKLAR unter `GET …/contracts/results`. Anfragen laufen zu viert parallel
  - [ ] Registerfelder (6.2) und Liste der Unterauftragnehmer, zusammen mit Phase 10
- [ ] 9.5 Prüfansicht: Der Berater bestätigt oder korrigiert jede Aussage
- [ ] 9.6 Bestätigte Vertragsdaten fließen in die Bewertung ein
- [ ] 9.7 Qualität messen: Für die Testverträge eine von Hand erstellte Lösung anlegen und die Trefferquote der KI ausrechnen
  - [x] Messskript und Basismessung (10.11.2026, vorgezogen): `scripts/evaluate_contracts.py`, Vergleich in `app/contracts/evaluation.py`. Ergebnis `vertrag-v1`: 65 % Übereinstimmung, 64 % Genauigkeit, 59 % Trefferquote, 9 % verworfen. Fehler fast nur bei der Einstufung der Prüfpunkte
  - [x] Recherche Prüfmaßstab (10.11.2026): `docs/pruefmassstab-vertraege.md` nach DSGVO Art. 28, Standardvertragsklauseln 2021/915, EDPB-Leitlinien 07/2020, DORA Art. 30 und VO 2025/532
  - [x] Version `vertrag-v2` (10.11.2026): 61 Bestandteile als Ja-Fragen in `fields.py`, Urteil nach Regel in `pipeline.judge`, Bestandteile über Seiten und Dokumente gesammelt, Leistungsbeschreibung bei AVV „nicht geprüft“ statt „fehlt“. Ergebnis 85 % Übereinstimmung (vorher 65 %, ein Lauf mit leicht anderem Prompt ebenfalls 85 %), Genauigkeit 83 %, Trefferquote 80 %, fälschlich nicht gefunden 4 %. Prüfpunkte 43 bzw. 39 von 48 richtig (vorher 28), `dsgvo_28_3_a` bleibt schwach
  - [ ] Stabilität: Ergebnisse schwanken zwischen Läufen je Feld. Mehrere Läufe messen, Fragen je Anfrage verkleinern
  - [ ] Musterlösung durch Jonas prüfen, vor allem die Grenzfälle in `docs/pruefmassstab-vertraege.md`, Abschnitt „Ergebnis von Version 2“

**Fertig, wenn:** Die KI für die Testverträge mindestens 90 % der Angaben richtig findet und jede Angabe auf ihre Fundstelle verweist. Die gemessene Quote ist ein starkes Argument im Interview.

## Phase 10: Stufe 3, DORA-Register und Workshop-Präsentation
- [ ] 10.1 Entwurf des DORA-Informationsregisters aus IT-Bestand und Vertragsdaten erzeugen (Excel)
- [ ] 10.2 Workshop-Präsentation mit python-pptx: Ausgangslage, Heatmap, Top-Risiken, Roadmap, offene Fragen für den Workshop
- [ ] 10.3 Vollständiger Durchlauf der Musterbank durch alle drei Stufen

**Fertig, wenn:** Die Musterbank einen vollständigen Bericht, einen Registerentwurf und eine Präsentation erhält, die ein Berater direkt im Workshop zeigen könnte.

## Phase 11: Für die Bewerbung verpacken
- [x] 11.1 README mit Problem, Lösung, Screenshots, Architektur, Grenzen (24.10.2026, wird bei jedem Commit mit Funktionsänderung mitgepflegt). Am 8.11.2026 neu gefasst: ohne Bezug zur Bewerbung, mit Beispielen aus der Bewertung und vier Seiten des Musterbank-Berichts
- [ ] 11.2 Online stellen (z. B. Render oder Fly.io), damit Recruiter es ausprobieren können
- [ ] 11.3 Demo-Video, 2 bis 3 Minuten
- [ ] 11.4 Einseitige Fallstudie „Musterbank AG“ im Beraterstil
- [ ] 11.5 Zwei bis drei Sätze für Lebenslauf und Anschreiben

---

## Später, nur bei echter Nachfrage
EU-Hosting (z. B. Hetzner oder IONOS), Wechsel auf ein in der EU betriebenes KI-Modell, Benutzerkonten und Bezahlung, n8n-Workflow, der Anbieter regelmäßig auf Änderungen prüft.
