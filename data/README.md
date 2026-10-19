# Anbieterdaten pflegen

Dieser Ordner enthält die Anbieterdatenbank als YAML-Dateien. Sie lassen sich in jedem Texteditor bearbeiten, Programmierkenntnisse sind nicht nötig. Ein Ladeskript überträgt sie in die Datenbank.

Was die Felder bedeuten und warum es sie gibt, steht in [docs/datenmodell.md](../docs/datenmodell.md).

## Aufbau

```
data/
├── countries.yaml        Länder mit Rechtsraum
├── organizations.yaml    Unternehmen mit Konzernmutter
├── categories.yaml       Kategorien
├── certificates.yaml     Zertifikate
└── services/
    ├── _vorlage.yaml     Vorlage zum Kopieren, wird nicht geladen
    └── <slug>.yaml       eine Datei je Dienst
```

Dateien, deren Name mit `_` beginnt, überspringt das Ladeskript.

## Grundregeln

1. **Verweise laufen über den `slug`.** Das ist ein fester Kurzname in Kleinbuchstaben mit Bindestrichen, zum Beispiel `microsoft-365`. Ein Dienst nennt seinen Anbieter als `provider: microsoft-ireland`, und dieses Unternehmen muss in `organizations.yaml` stehen.
2. **Der Dateiname eines Dienstes ist sein `slug`.** `services/microsoft-365.yaml` enthält `slug: microsoft-365`.
3. **Wertelisten in Großbuchstaben** wie in der Vorlage. Ein Tippfehler wird beim Laden abgelehnt.
4. **Was nicht recherchiert ist, bleibt weg.** Fehlende Merkmale gelten als `UNBEKANNT`, und die Bewertung behandelt sie wie den ungünstigsten Fall. Nichts raten.
5. **Keine Schreibweise, die nur den Herstellernamen wiederholt**, wenn der Hersteller mehrere Produkte anbietet. „SAP“ als Schreibweise für SAP S/4HANA hätte auch SAP Ariba oder SAP Concur angezogen.
6. **Ländercodes in Anführungszeichen:** `"DE"`, `"NO"`. Ohne sie liest YAML den Code `NO` für Norwegen als „nein“.

## Angaben mit Nachweis

Ein Merkmal lässt sich kurz oder mit Nachweis schreiben.

Kurz, ohne Nachweis:

```yaml
openness: PROPRIETAER
```

Mit Nachweis:

```yaml
data_location:
  value: EU_ZUGESICHERT
  source: https://beispiel.example/datenschutz
  quote: "Alle Kundendaten werden in Rechenzentren in Frankfurt gespeichert."
  retrieved: 2026-10-13
```

| Feld | Bedeutung | Pflicht |
|---|---|---|
| `value` | der Wert | ja |
| `source` | Adresse der Quelle, möglichst die Seite des Anbieters | ja |
| `quote` | Fundstelle im Wortlaut oder Abschnitt, bei Verträgen mit Seitenzahl | empfohlen |
| `retrieved` | Abrufdatum als `JJJJ-MM-TT` | ja |

**Ein Nachweis ist Pflicht** für alles, was die Stufe bestimmt. Ist eine dieser Angaben nicht belegbar, bleibt sie weg und gilt als unbekannt:

- Konzernmutter eines Unternehmens (`parent`)
- Datenstandort (`data_location`)
- Schlüsselverwaltung (`key_management`)
- jedes Zertifikat
- jede Abhängigkeit

Sind alle Zulieferer einer Variante geprüft, etwa anhand der Liste der Unterauftragnehmer, steht bei der Variante `dependencies_complete: true`. Ohne diesen Eintrag geht die Bewertung davon aus, dass ein kritischer Zulieferer außerhalb der EU nicht auszuschließen ist.

Als Quelle zählt, was ein Dritter nachprüfen kann: Vertragsunterlagen und Dokumentation des Anbieters, Zertifikatsverzeichnisse, Handelsregister, Geschäftsberichte. Blogbeiträge und Vergleichsportale nur, wenn es nichts Besseres gibt.

## Was ein Merkmal aussagt

Eingetragen wird, was die Variante **ermöglicht**, also die beste verfügbare Option. Bietet ein Dienst kundeneigene Schlüssel nur in einer teureren Edition an, steht trotzdem `KUNDE_BEIM_ANBIETER` oder `KUNDE_EXTERN`, mit einem Kommentar zur Einschränkung. Ob ein Unternehmen die Option nutzt, klärt der Fragebogen.

## Nachweise nachprüfen

```
cd backend
uv run python scripts/verify_evidence.py
```

Das Skript ruft jede Quelle ab und kontrolliert, ob die Fundstelle dort wörtlich steht. Es meldet Fundstellen, die nicht mehr auffindbar sind, und Quellen, die sich nicht abrufen lassen.

## Prüfstatus

Jede Variante trägt einen Prüfstatus:

```yaml
review:
  status: KI_VORSCHLAG
```

| Status | Bedeutung |
|---|---|
| `KI_VORSCHLAG` | Von der KI recherchiert, noch nicht nachgeprüft |
| `KI_NACHGEPRUEFT` | Die KI hat jede Quelle ein zweites Mal abgerufen und die Fundstelle dort wiedergefunden |
| `GEPRUEFT` | Ein Mensch hat die Quellen geöffnet und die Angaben bestätigt |

Ab `KI_NACHGEPRUEFT` gehört das Prüfdatum dazu:

```yaml
review:
  status: KI_NACHGEPRUEFT
  date: 2026-10-13
```

Die Nachprüfung findet erfundene und veraltete Fundstellen. Ob eine Fundstelle richtig ausgelegt wurde, kann nur ein Mensch bestätigen. Die Bewertung weist den Status jedes Eintrags aus.

## Stammdateien

`countries.yaml`:

```yaml
- code: "DE"
  name: Deutschland
  jurisdiction: EU_EWR
```

`organizations.yaml`, mit und ohne Konzernmutter:

```yaml
- slug: beispiel-holding
  name: Beispiel Holding Inc.
  country: "US"

- slug: beispiel-gmbh
  name: Beispiel GmbH
  country: "DE"
  parent:
    value: beispiel-holding
    source: https://beispiel.example/impressum
    retrieved: 2026-10-13
```

Bei `parent` steht immer die oberste Konzernmutter, keine Zwischengesellschaft.

`categories.yaml` und `certificates.yaml`:

```yaml
- slug: collaboration
  name: Büro und Zusammenarbeit
```

```yaml
- slug: bsi-c5
  name: BSI C5
  issuer: BSI
```

## Einen Dienst anlegen

1. `services/_vorlage.yaml` kopieren und nach dem `slug` des Dienstes benennen.
2. Anbieter und, falls nötig, Konzernmutter in `organizations.yaml` ergänzen.
3. Merkmale recherchieren und mit Nachweis eintragen.
4. Ladeskript ausführen (siehe unten). Es meldet jeden Fehler mit Datei und Feld.

## In die Datenbank laden

```
cd backend
uv run python -m app.seed
```

Die Datenbank muss dafür laufen (`docker compose up -d` im Projektordner). Bei einem Fehler in den Dateien wird nichts geschrieben.

## Was das Ladeskript prüft

- Jeder Verweis auf ein Land, ein Unternehmen, eine Kategorie, ein Zertifikat oder einen anderen Dienst existiert.
- Jeder Dienst hat mindestens eine Variante und genau eine mit `default: true`.
- Die Pflichtnachweise sind vorhanden.
- Schreibweisen (`aliases`) kommen über alle Dienste hinweg nur einmal vor, Groß- und Kleinschreibung zählt nicht.
- `KI_NACHGEPRUEFT` und `GEPRUEFT` stehen nie ohne Datum.

Das Laden lässt sich beliebig oft wiederholen: Die Datenbank entspricht danach genau dem Stand der Dateien. Was aus den Dateien entfernt wurde, verschwindet auch aus der Datenbank. Bestehende Dienste und Varianten behalten ihre interne Nummer, damit spätere Assessments weiter auf sie verweisen können.

## Fragebogen

`questionnaire.yaml` enthält die Fragen des Assessments. Die Fragen im Abschnitt „Unternehmen“ bestimmen, ob DORA oder NIS2 gilt. Alle anderen Fragen ergeben einen Reifegrad 0 bis 4 je Handlungsfeld. Er steht neben den Stufen der Anbieter und verändert sie nicht.

- Jede Antwort einer Reifegrad-Frage hat eine Stufe (`level`), und „Weiß nicht“ (`UNBEKANNT`) zählt wie „Nein“.
- Jede Rechtsgrundlage (`basis`) zitiert den amtlichen deutschen Text und wird wie die Anbieterdaten mit `verify_evidence.py` nachgeprüft. Fragen ohne `basis` beruhen auf der Methodik des Tools.
- Antworttexte mit Komma stehen in Anführungszeichen, sonst liest YAML sie als mehrere Felder. Das Schema lehnt solche Fehler beim Laden ab.

## Regeln für DORA und NIS2

`compliance.yaml` enthält die Fundstellen, mit denen das Tool bestimmt, ob DORA oder NIS2 gilt, und die Hinweise, die aus dem IT-Bestand folgen. Die Logik steht in `backend/app/compliance/`, erklärt in [docs/bewertungslogik.md](../docs/bewertungslogik.md). Auch diese Fundstellen prüft `verify_evidence.py`.

## Vorlage für den IT-Bestand

`templates/it-bestand-vorlage.xlsx` ist die Vorlage, mit der ein Unternehmen seinen IT-Bestand einreicht. Das Blatt „Ausfüllhilfe“ erklärt jede Spalte. Pflicht sind nur Dienst, Zweck, Kritikalität und die Angabe, ob eine kritische oder wichtige Funktion im Sinne von DORA unterstützt wird.

Die Spalten mit DORA-Bezug folgen dem Informationsregister nach der Durchführungsverordnung (EU) 2024/2956 (Feldnamen und Wertelisten aus dem ESA-Dokument JC 2024 79). Datenstandort, Konzernmutter, Vertragsrecht und Zertifikate fragt die Vorlage bewusst nicht ab: Sie kommen aus der Anbieterdatenbank.

Die Datei wird aus dem Code erzeugt, Änderungen gehören deshalb nach `backend/app/inventory/template.py`:

```
cd backend
uv run python -m app.inventory
```

## IT-Bestand importieren

Der Endpunkt `POST /inventory/import` nimmt eine ausgefüllte Vorlage (`.xlsx`) oder eine CSV-Datei entgegen und gibt die gelesenen Einträge zurück. Alle Fehler kommen auf einmal, jeweils mit Zeile und Spalte, damit sich die Datei in einem Durchgang korrigieren lässt.

- Spaltenüberschriften dürfen ohne Sternchen, in anderer Groß- und Kleinschreibung oder als Kurzname (`service`, `purpose`) geschrieben sein.
- Werte aus den Auswahllisten werden unabhängig von Groß- und Kleinschreibung erkannt („HOCH“, „Ja“).
- CSV-Dateien dürfen Semikolon oder Komma als Trenner nutzen, in UTF-8 oder im Windows-Zeichensatz.
- Unbekannte Spalten werden mit einem Hinweis ignoriert, leere Zeilen übersprungen.
- Grenzen: höchstens 5 MB und 5000 Zeilen.

`POST /inventory/import` speichert nichts. Gespeichert wird der Bestand am Assessment über `PUT /assessments/{id}/inventory`, als Originaldatei zusammen mit der Zuordnung jeder Zeile. Ein neuer Bestand ersetzt den alten.
