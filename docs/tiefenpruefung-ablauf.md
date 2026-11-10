# Arbeitsanweisung Tiefenprüfung: Vertragsanalyse

Stand: 9.11.2026, Version `vertrag-v1`. Gilt für Stufe 3 (PLAN.md, Phase 9). Diese Anweisung ist die Spezifikation des Ablaufs: Jeder Schritt im Code (Prompt, Antwortschema, Prüfregel) geht auf einen Abschnitt hier zurück. Ändert sich ein Prompt oder eine Regel, steigt die Version, und jeder Lauf speichert, nach welcher Version er gearbeitet hat.

## 1. Zweck

Die Stufen 1 und 2 bewerten einen Dienst nach den **Standardbedingungen** des Anbieters, so wie sie in der Anbieterdatenbank stehen. Ein Unternehmen hat aber oft eigene Verträge: eine zugesicherte EU-Region, deutsches Recht, eine Exit-Klausel. Die Tiefenprüfung liest diese Verträge aus und setzt die **bestätigten** Angaben für dieses eine Assessment an die Stelle der Katalogwerte.

Zusätzlich prüft sie die Pflichtinhalte nach DORA Art. 30 und DSGVO Art. 28 Abs. 3 und füllt Felder des DORA-Informationsregisters vor.

## 2. Grundsatz: fester Ablauf statt freier Agent

Der Ablauf ist ein **Workflow mit festen Schritten**, kein Agent, der selbst entscheidet, was er als Nächstes tut. Zwischen den Schritten prüft Code das Ergebnis, bevor es weitergeht. Das folgt dem Leitfaden von Anthropic: „Workflows offer predictability and consistency for well-defined tasks“, Agenten lohnen sich erst, wenn sich die Schritte nicht vorhersagen lassen ([Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)). Die Muster heißen dort *Prompt Chaining* (Kette mit Prüfungen dazwischen) und *Routing* (je nach Dokumenttyp ein eigener Weg).

Begründung:

- **Nachvollziehbarkeit.** Eine Prüfung muss bei gleichem Vertrag gleich ausfallen und erklärbar sein. Feste Schritte, Temperatur 0 und gespeicherte Prompt-Version machen das möglich.
- **Kleines Modell.** Wir nutzen DeepSeek V4.1 Flash. Bei einem frei handelnden Agenten schaukeln sich Fehler über die Schritte auf. Kurze, eng gefasste Aufgaben mit festem Antwortschema liegen einem kleinen Modell.
- **Messbarkeit.** Jeder Schritt hat eine eigene Kennzahl (Abschnitt 9).
- **Verantwortung.** Nach DORA Art. 28 Abs. 1 bleibt das Finanzunternehmen voll verantwortlich. Die KI macht Vorschläge, ein Mensch entscheidet.

## 3. Rollen

| Rolle | Aufgabe |
|---|---|
| **KI** (DeepSeek V4.1 Flash über OpenRouter, nur Anbieter ohne Datenspeicherung) | ordnet Dokumente ein, liest Angaben aus, immer mit Zitat und Seite |
| **Code** | liest PDFs, prüft Antwortschema, Werte und Zitate, führt zusammen, schreibt das Protokoll |
| **Berater** | bestätigt die Einordnung, bestätigt, korrigiert oder verwirft jede Angabe, entscheidet über Widersprüche |

## 4. Eingaben

- Ein Assessment mit IT-Bestand (Stufe 2 abgeschlossen oder IT-Bestand hochgeladen).
- Je Dienst ein oder mehrere Vertragsdokumente als PDF mit Textebene: Rahmenvertrag, Auftragsverarbeitungsvertrag (AVV/DPA), Leistungsbeschreibung oder SLA, Standardvertragsklauseln, Anlagen (z. B. Liste der Unterauftragnehmer).
- Höchstgröße und erlaubte Dateitypen wie beim IT-Bestand. Gescannte PDFs ohne Text werden nicht ausgelesen (kein OCR in Version 1).

## 5. Ablauf

| Nr. | Schritt | Wer | Ergebnis | Prüfung, bevor es weitergeht |
|---|---|---|---|---|
| 1 | Aufnehmen | Code | Text je PDF-Seite | Seiten ohne Text werden als „ohne Text“ markiert. Hat das Dokument keine Seite mit Text: Abbruch mit Hinweis |
| 2 | Einordnen | KI, dann Berater | Dokumenttyp und Dienst | Typ aus der Liste in 5.2, Dienst aus dem IT-Bestand des Assessments. Der Berater bestätigt, erst dann Schritt 3 |
| 3 | Auslesen | KI | Angaben je Themenblock | Antwort entspricht dem JSON-Schema, jeder Wert stammt aus der erlaubten Werteliste |
| 4 | Belegprüfung | Code | geprüfte Angaben | Zitat steht wörtlich auf der genannten Seite, sonst verworfen |
| 5 | Zusammenführen | Code | eine Angabe je Feld und Dienst | Widersprüche werden „unklar“ und nicht automatisch aufgelöst |
| 6 | Prüfen | Berater | Status je Angabe | bestätigt, korrigiert oder verworfen |
| 7 | Übernehmen | Code | Bewertung mit Vertragsfakten | nur bestätigte Angaben |

### 5.1 Aufnehmen

- Text seitenweise mit pypdf. **Seite meint immer die physische Seite im PDF, gezählt ab 1**, nicht die aufgedruckte Seitenzahl. Nur so lässt sich das Zitat automatisch wiederfinden. Die Prüfansicht zeigt beides, wenn die aufgedruckte Zahl erkennbar ist.
- Weiche Trennstriche und Zeilenumbrüche innerhalb von Wörtern werden für die Belegprüfung entfernt, der Originaltext bleibt gespeichert.

### 5.2 Einordnen (Routing)

Die KI bekommt die ersten zwei Seiten und wählt einen Dokumenttyp. Der Typ bestimmt, welche Themenblöcke (5.3) ausgelesen werden.

| Dokumenttyp | Themenblöcke |
|---|---|
| `AVV` (Auftragsverarbeitung, DPA) | Datenort, Unterauftragnehmer, Daten und Exit, DSGVO-Prüfliste |
| `RAHMENVERTRAG` (MSA, AGB, Kundenvertrag) | Recht und Laufzeit, Daten und Exit, Betrieb und Aufsicht |
| `LEISTUNGSBESCHREIBUNG` (SLA, Service Description) | Betrieb und Aufsicht, Datenort |
| `STANDARDVERTRAGSKLAUSELN` | Datenort (nur Übermittlungsgrundlage) |
| `UNTERAUFTRAGNEHMER` (Liste als Anlage oder Webseite als PDF) | Unterauftragnehmer |
| `SONSTIGES` | alle Themenblöcke, Hinweis an den Berater |

Außerdem schlägt die KI den Dienst vor, mit Zitat (z. B. der Produktname im Vertrag). Weil Namen kurz sein können („STACKIT“), genügen hier 3 Zeichen statt 10, dafür muss das Zitat den ganzen Namen des Dienstes, eines Alias oder des Anbieters enthalten. Der Berater bestätigt oder wählt um. Ein Dokument kann für mehrere Dienste desselben Anbieters gelten (z. B. ein AVV für alle Microsoft-Onlinedienste). In Version 1 wird ein Dokument genau einem Dienst zugeordnet, für weitere Dienste lädt der Berater es erneut hoch.

Die Prüf- und Auditrechte (DORA 30(3)e) stehen meist im AVV. Sie werden deshalb außer in „Betrieb und Aufsicht“ auch im Block der DSGVO-Prüfliste abgefragt.

### 5.3 Auslesen

- Der Text geht **seitenweise markiert** an die KI (`=== Seite 7 ===`), in Abschnitten von höchstens 12.000 Zeichen. Ist ein Dokument länger, läuft jeder Themenblock über alle Abschnitte, Schritt 5 führt zusammen.
- Je Themenblock eine Anfrage. Kurze, eng gefasste Aufgaben sind für ein kleines Modell zuverlässiger als eine große Anfrage für alles.
- Für jedes Feld antwortet die KI mit `wert`, `zitat` (wörtlich, höchstens 300 Zeichen, aus **einer** Seite, in der Sprache des Vertrags) und `seite`, oder mit `NICHT_GEFUNDEN`. **Raten ist ausdrücklich verboten**: Ohne Zitat gibt es keinen Wert. Das folgt der Empfehlung, die KI erst Zitate suchen und nur aus ihnen antworten zu lassen ([Anthropic, Reduce hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations)).
- Die Antwort wird als JSON-Schema angefordert. Unterstützt der Anbieter das nicht, gilt das bisherige Verfahren: JSON aus der Antwort lesen und im Code gegen dasselbe Schema prüfen.

### 5.4 Belegprüfung

Eine Angabe bleibt nur, wenn alle Bedingungen erfüllt sind:

1. Der Wert steht in der Werteliste des Feldes (Abschnitt 6).
2. Das Zitat hat mindestens 10 Zeichen und steht wörtlich auf der genannten Seite. Leerraum, Zeilenumbrüche und Trennstriche zählen nicht. Dieselbe Prüfung nutzt schon der Schnellcheck für die Vorschläge zu Branche und Größe.
3. Bei Zahlen (Kündigungsfrist, Übergangszeit) steht die Zahl im Zitat.

Steht das Zitat auf einer anderen Seite, wird die Seite **nicht** stillschweigend korrigiert: Die Angabe wird verworfen und im Protokoll mit „Seite falsch“ vermerkt. So bleibt die Kennzahl ehrlich.

### 5.5 Zusammenführen

- Gleicher Wert aus mehreren Stellen: eine Angabe, alle Fundstellen bleiben erhalten.
- **Verschiedene Werte für dasselbe Feld** (zwischen Seiten oder Dokumenten): Status `UNKLAR`, alle Fundstellen werden gezeigt. Der Code löst Widersprüche nicht auf, auch nicht nach Rangfolge der Dokumente. Welche Klausel vorgeht, ist eine rechtliche Frage und gehört dem Berater.
- Felder, für die keine Angabe die Belegprüfung bestanden hat, bleiben `NICHT_GEFUNDEN`.

### 5.6 Prüfen durch den Berater

Je Angabe sieht der Berater Wert, Zitat, Dokument und Seite und entscheidet:

- **bestätigen:** Status `GEPRUEFT`.
- **korrigieren:** anderer Wert aus der Werteliste, Status `GEPRUEFT`, die ursprüngliche KI-Angabe bleibt im Protokoll.
- **verwerfen:** Status `VERWORFEN`, die Angabe zählt nicht.

`NICHT_GEFUNDEN` heißt nur: im vorgelegten Dokument nicht gefunden. Erst der Berater kann daraus „fehlt im Vertrag“ machen. Eine KI kann nicht beweisen, dass etwas nicht im Vertrag steht.

Anders als bei der Anbieterdatenbank gibt es hier keinen Status `KI_NACHGEPRUEFT`: Vertragsangaben sind kundenspezifisch und ändern die Bewertung eines Kunden. Sie brauchen immer eine menschliche Bestätigung.

### 5.7 Übernehmen in die Bewertung

- Bestätigte Angaben zu den Bewertungsfakten (6.1) ersetzen für dieses Assessment den Katalogwert, auch wenn der Vertrag **ungünstiger** ist als der Katalog. Der Vertrag ist für diesen Kunden verbindlich, der Katalog beschreibt nur den Standard.
- Die Bewertung zeigt die Herkunft: „Quelle: Vertrag ‹Datei›, S. ‹n›“ statt der Herstellerseite.
- Eine Frage im Fragenkatalog an den Anbieter entfällt, wenn der Vertrag die Lücke schließt.
- Fehlende Pflichtinhalte (6.3, 6.4) erscheinen als DORA- bzw. DSGVO-Hinweise beim Dienst.
- Die Registerfelder (6.2) gehen in den Entwurf des DORA-Informationsregisters (Phase 10).

## 6. Was ausgelesen wird

### 6.1 Bewertungsfakten

Dieselben Werte wie in der Anbieterdatenbank (`backend/app/models/enums.py`, erklärt in `docs/datenmodell.md`), damit die Bewertungsregeln unverändert bleiben.

| Feld | Werte | Auslegung im Vertrag | Block |
|---|---|---|---|
| `data_location` | `EU_ZUGESICHERT`, `EU_WAEHLBAR`, `EU_UND_ANGEMESSEN`, `NICHT_EU` | Zugesichert nur, wenn der Vertrag Speicherung **ausschließlich** in EU/EWR zusagt. Eine Region, die der Kunde wählen kann, ohne Zusage im Vertrag, ist `EU_WAEHLBAR` | Datenort |
| `operations_location` | `NUR_EU`, `EU_MIT_AUSNAHMEN`, `WELTWEIT` | Ort von Betrieb und Support, z. B. Fernzugriff aus Drittstaaten „follow the sun“ = `WELTWEIT` | Datenort |
| `transfer_basis` | `NICHT_NOETIG`, `STANDARDVERTRAGSKLAUSELN`, `DATA_PRIVACY_FRAMEWORK`, `ANGEMESSENHEITSBESCHLUSS`, `VERBINDLICHE_UNTERNEHMENSREGELN`, `KEINE` | Grundlage für Übermittlungen in Drittländer | Datenort |
| `governing_law` | `EU_EWR`, `ANGEMESSEN`, `USA`, `DRITTSTAAT` | Recht, das für den Vertrag gilt; zusätzlich das Land für das Register (6.2) | Recht und Laufzeit |
| `key_management` | `ANBIETER`, `KUNDE_BEIM_ANBIETER`, `KUNDE_EXTERN` | Wer die Schlüssel verwaltet. Gleiche Regeln wie in der Anbieterdatenbank: wählbares BYOK = `KUNDE_BEIM_ANBIETER` | Daten und Exit |
| `data_export` | `OFFENE_FORMATE`, `PROPRIETAER`, `KEIN_EXPORT` | Herausgabe der Daten bei Vertragsende, Format | Daten und Exit |
| `ai_training_on_customer_data` | `NEIN`, `ABWAEHLBAR`, `JA` | Nutzung von Kundendaten zum Training | Daten und Exit |
| Unterauftragnehmer | Liste: Name, Land, Leistung | wird zu Abhängigkeiten (`UNTERAUFTRAGNEHMER`). Ob eine Abhängigkeit kritisch ist und welcher Konzern dahintersteht, entscheidet der Berater bzw. die Anbieterdatenbank, nicht die KI | Unterauftragnehmer |

### 6.2 Felder des DORA-Informationsregisters

Nach der Durchführungsverordnung (EU) 2024/2956, Vorlage B_02.02 (vertragliche Vereinbarungen, besondere Angaben).

| Feld | Register | Format |
|---|---|---|
| Beginn | B_02.02.0070 | Datum |
| Ende | B_02.02.0080 | Datum, unbefristet = 9999-12-31 |
| Kündigungsfrist Finanzunternehmen | B_02.02.0100 | Kalendertage |
| Kündigungsfrist Anbieter | B_02.02.0110 | Kalendertage |
| Land des maßgebenden Rechts | B_02.02.0120 | ISO 3166-1 Alpha-2 |
| Land der Leistungserbringung | B_02.02.0130 | ISO 3166-1 Alpha-2 |
| Datenspeicherung | B_02.02.0140 | Ja/Nein |
| Länder der Speicherung | B_02.02.0150 | ISO-Codes, mehrere möglich |
| Länder der Verarbeitung | B_02.02.0160 | ISO-Codes, mehrere möglich |

Fristen in Monaten oder Wochen rechnet der Code in Tage um (Monat = 30 Tage), das Zitat bleibt im Original.

### 6.3 Prüfliste DORA Art. 30

Je Punkt: `VORHANDEN`, `TEILWEISE` oder `NICHT_GEFUNDEN`, jeweils mit Zitat. Absatz 3 gilt nur für Dienste, die im IT-Bestand eine kritische oder wichtige Funktion unterstützen (Spalte `critical_function`).

| Punkt | Inhalt (verkürzt) | Block |
|---|---|---|
| 30(2)a | Beschreibung aller Leistungen; ob Unterauftragsvergabe für kritische Funktionen zulässig ist und unter welchen Bedingungen | Unterauftragnehmer |
| 30(2)b | Regionen oder Länder der Leistung und der Datenverarbeitung samt Speicherort; Pflicht, Änderungen vorab mitzuteilen | Datenort |
| 30(2)c | Verfügbarkeit, Authentizität, Integrität und Vertraulichkeit der Daten | Betrieb und Aufsicht |
| 30(2)d | Zugang zu den Daten, Wiederherstellung und Rückgabe in leicht zugänglichem Format bei Insolvenz, Abwicklung, Einstellung oder Vertragsende | Daten und Exit |
| 30(2)e | Beschreibung der Dienstleistungsgüte | Betrieb und Aufsicht |
| 30(2)f | Unterstützung bei IKT-Vorfällen ohne zusätzliche oder zu vorab festgelegten Kosten | Betrieb und Aufsicht |
| 30(2)g | volle Zusammenarbeit mit den zuständigen Behörden | Betrieb und Aufsicht |
| 30(2)h | Kündigungsrechte und Mindestkündigungsfristen | Recht und Laufzeit |
| 30(2)i | Teilnahme an Schulungen zur IKT-Sicherheit und Resilienz | Betrieb und Aufsicht |
| 30(3)a | präzise quantitative und qualitative Leistungsziele | Betrieb und Aufsicht |
| 30(3)b | Kündigungsfristen und Berichtspflichten des Anbieters | Recht und Laufzeit |
| 30(3)c | Notfallpläne, die der Anbieter umsetzt und testet; Sicherheitsmaßnahmen | Betrieb und Aufsicht |
| 30(3)d | Mitwirkung an bedrohungsorientierten Penetrationstests (TLPT) | Betrieb und Aufsicht |
| 30(3)e | uneingeschränkte Zugangs-, Inspektions- und Auditrechte | Betrieb und Aufsicht |
| 30(3)f | Ausstiegsstrategie mit verbindlichem, angemessenem Übergangszeitraum | Daten und Exit |

Ergänzend wird geprüft, ob der Vertrag die Kündigungsgründe nach Art. 28 Abs. 7 abdeckt (erheblicher Verstoß, festgestellte Beeinträchtigung, nachweisliche Schwächen im IKT-Risikomanagement, keine wirksame Aufsicht mehr möglich).

### 6.4 Prüfliste DSGVO Art. 28 Abs. 3 (nur AVV)

Je Punkt `VORHANDEN`, `TEILWEISE` oder `NICHT_GEFUNDEN`, mit Zitat: (a) Verarbeitung nur auf dokumentierte Weisung, auch bei Drittlandübermittlung; (b) Vertraulichkeit der befugten Personen; (c) Maßnahmen nach Art. 32; (d) Bedingungen für weitere Auftragsverarbeiter nach Abs. 2 und 4; (e) Unterstützung bei Rechten der betroffenen Personen; (f) Unterstützung bei Art. 32 bis 36; (g) Löschung oder Rückgabe nach Ende der Leistung; (h) Nachweise und Überprüfungen einschließlich Inspektionen.

## 7. Abbruch- und Ausnahmeregeln

| Fall | Verhalten |
|---|---|
| Dokument ohne Textebene | kein Auslesen, Hinweis „Bitte PDF mit Text hochladen“ |
| Einzelne Seiten ohne Text | Auslesen der übrigen Seiten, Hinweis mit Seitenzahlen |
| Dienst nicht im IT-Bestand | Berater muss zuordnen oder den Dienst zuerst im Bestand ergänzen |
| Antwort verletzt das Schema | eine Wiederholung mit Fehlerhinweis, danach Themenblock „nicht ausgelesen“ |
| KI nicht erreichbar oder Frist überschritten | eine Wiederholung, danach Schritt „nicht gelaufen“. Keine halben Ergebnisse ohne Hinweis |
| Zitat nicht auffindbar oder falsche Seite | Angabe verworfen, im Protokoll gezählt |
| Widerspruch | Status `UNKLAR`, Berater entscheidet |

## 8. Protokoll

Jeder Lauf speichert: Version dieser Anweisung, Modell, Zeitpunkt, Dauer je Schritt, die rohe Antwort der KI je Anfrage, verworfene Angaben mit Grund (Schema, Wert, Zitat, Seite) und die Entscheidungen des Beraters. Damit lässt sich jede Angabe im Bericht bis zur Stelle im Vertrag und zur Entscheidung zurückverfolgen.

## 9. Qualität messen

Für die Testverträge (öffentliche AVVs von Microsoft, AWS, Salesforce und zwei EU-Anbietern) gibt es eine von Hand erstellte Musterlösung: je Feld Wert, Seite und Zitat. Gemessen wird je Feld:

- **Genauigkeit:** Anteil der ausgegebenen Angaben, deren Wert und Seite stimmen.
- **Trefferquote:** Anteil der Angaben der Musterlösung, die die KI gefunden hat.
- **Fälschlich nicht gefunden:** steht im Vertrag, die KI meldet `NICHT_GEFUNDEN`.
- **Verwerfungsquote:** Anteil der KI-Angaben, die an der Belegprüfung scheitern. Eine hohe Quote heißt, die KI erfindet oder verrutscht. Gezeigt wird dem Berater davon nichts.

Ziel: mindestens 90 % Genauigkeit und Trefferquote über alle Felder. Jede Angabe, die der Berater sieht, hat eine geprüfte Fundstelle, das stellt Schritt 4 sicher. Gemessen wird bei jeder Änderung an Prompt, Schema oder Modell. Zum Vergleich: Selbst große Modelle erreichen auf dem Vertragsdatensatz CUAD je nach Klauseltyp sehr unterschiedliche Werte. Deshalb wird je Feld gemessen und nicht nur im Durchschnitt.

## 10. Grenzen

- Keine Rechtsberatung. Die Tiefenprüfung zeigt, was im Vertrag steht, nicht, ob es rechtlich ausreicht.
- Kein OCR, keine Auswertung von Bildern oder Tabellen als Grafik.
- Verweise auf externe Dokumente (z. B. „es gelten die Online Service Terms“) werden nicht verfolgt. Der Berater muss das Dokument zusätzlich hochladen.
- Verträge sind vertraulich. Sie gehen nur an Anbieter ohne Datenspeicherung (`data_collection: deny`). Für echte Kundenverträge ist vor dem Einsatz ein in der EU betriebenes Modell zu prüfen.

## Quellen

- Verordnung (EU) 2022/2554 (DORA), Art. 28 und 30: https://eur-lex.europa.eu/eli/reg/2022/2554/oj
- Verordnung (EU) 2016/679 (DSGVO), Art. 28: https://eur-lex.europa.eu/eli/reg/2016/679/oj
- Durchführungsverordnung (EU) 2024/2956, Vorlagen des Informationsregisters: https://eur-lex.europa.eu/eli/reg_impl/2024/2956/oj
- Anthropic, Building effective agents: https://www.anthropic.com/engineering/building-effective-agents
- Anthropic, Reduce hallucinations: https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations
- CUAD (Contract Understanding Atticus Dataset): https://www.atticusprojectai.org/cuad

Die Wortlaute von DORA, DSGVO und der Durchführungsverordnung wurden am 9.11.2026 an den amtlichen deutschen Fassungen geprüft (abgerufen über die Schnittstelle des Amts für Veröffentlichungen der EU, CELEX 32022R2554, 32016R0679, 32024R2956).
