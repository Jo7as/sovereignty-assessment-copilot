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
5. **Ländercodes in Anführungszeichen:** `"DE"`, `"NO"`. Ohne sie liest YAML den Code `NO` für Norwegen als „nein“.

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

**Ein Nachweis ist Pflicht** für alles, was die Stufe bestimmt:

- Konzernmutter eines Unternehmens (`parent`)
- Datenstandort (`data_location`)
- Schlüsselverwaltung (`key_management`)
- jedes Zertifikat
- jede Abhängigkeit

Als Quelle zählt, was ein Dritter nachprüfen kann: Vertragsunterlagen und Dokumentation des Anbieters, Zertifikatsverzeichnisse, Handelsregister, Geschäftsberichte. Blogbeiträge und Vergleichsportale nur, wenn es nichts Besseres gibt.

## Prüfstatus

Jede Variante trägt einen Prüfstatus:

```yaml
review:
  status: KI_VORSCHLAG
```

Ein Vorschlag der KI bleibt `KI_VORSCHLAG`, bis ein Mensch die Quellen geöffnet und die Angaben bestätigt hat. Erst dann:

```yaml
review:
  status: GEPRUEFT
  date: 2026-10-13
```

Die Bewertung weist ungeprüfte Einträge als solche aus.

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
4. Ladeskript ausführen (kommt in Schritt 1.5). Es meldet jeden Fehler mit Datei und Feld.

## Was das Ladeskript prüft

- Jeder Verweis auf ein Land, ein Unternehmen, eine Kategorie, ein Zertifikat oder einen anderen Dienst existiert.
- Jeder Dienst hat mindestens eine Variante und genau eine mit `default: true`.
- Die Pflichtnachweise sind vorhanden.
- Schreibweisen (`aliases`) kommen über alle Dienste hinweg nur einmal vor, Groß- und Kleinschreibung zählt nicht.
- `GEPRUEFT` steht nie ohne Datum.

Das Laden lässt sich beliebig oft wiederholen: Die Datenbank entspricht danach genau dem Stand der Dateien.
