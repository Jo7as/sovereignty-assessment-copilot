# Bewertungslogik

Stand: Schritte 5.1 bis 5.3, umgesetzt in `backend/app/scoring/`. Die Auslegung der Stufen ist unsere eigene und noch nicht von Jonas freigegeben (siehe „Offene Entscheidungen“).

## Grundlage

Maßstab ist das **Cloud Sovereignty Framework** der Europäischen Kommission, Version 1.2.1 vom Oktober 2025 ([Quelle](https://commission.europa.eu/document/download/09579818-64a6-4dd5-9577-446ab6219113_en?filename=Cloud-Sovereignty-Framework.pdf)). Es legt fest:

- acht Zielbereiche (SOV-1 bis SOV-8),
- fünf Stufen (SEAL-0 bis SEAL-4),
- zu jedem Zielbereich eine Liste von Einflussfaktoren,
- Gewichte für einen Souveränitätswert.

Das Rahmenwerk legt **nicht** fest, welche Tatsache zu welcher Stufe führt. Die Kommission bewertet das in ihren Ausschreibungen selbst, anhand von Fragebögen. Die Regeln unten sind deshalb unsere Auslegung. Wo wir vom Wortlaut ausgehen, ist er zitiert.

## Die fünf Stufen

| Stufe | Rahmenwerk (Wortlaut) | Unsere Kurzform |
|---|---|---|
| 0 | „No Sovereignty: Service, technology or operations under exclusive control of non-EU third parties, governed entirely in non-EU jurisdictions.“ | Nicht-EU ohne Schutz |
| 1 | „Jurisdictional Sovereignty: EU law formally applies with limited practical enforceability; […] under exclusive control of non-EU third parties.“ | Nicht-EU, EU-Recht gilt formal |
| 2 | „Data Sovereignty: EU law applicable and enforceable, with material non-EU dependencies remaining; […] under indirect control of non-EU third parties.“ | Nicht-EU mit EU-Betriebsgesellschaft, oder EU mit kritischer Nicht-EU-Abhängigkeit |
| 3 | „Digital Resilience: […] EU actors exercising meaningful but not full influence; […] under marginal control of non-EU third parties.“ | EU mit einzelnen, nicht kritischen Nicht-EU-Abhängigkeiten |
| 4 | „Full Digital Sovereignty: Technology and operations under complete EU control, subject only to EU law, with no critical non-EU dependencies.“ | Vollständig EU |

## So entsteht eine Stufe

1. **Kriterien.** Jeder Zielbereich besteht aus ein bis drei Kriterien. Jedes Kriterium nennt die Stufe, die es höchstens zulässt, und den Grund.
2. **Zielbereich.** Die Stufe eines Zielbereichs ist die niedrigste dieser Obergrenzen. Das folgt dem Rahmenwerk: „Material weaknesses identified in one or more contributing factor will result in lowering the overall assurance level recognized for the objective.“
3. **Gesamtstufe.** Die Gesamtstufe eines Dienstes ist der schwächste Zielbereich.
4. **Souveränitätswert.** Zusätzlich ein Wert von 0 bis 100: je Zielbereich die erreichte Stufe geteilt durch 4, mal dem Gewicht des Rahmenwerks.

| Zielbereich | Gewicht |
|---|---|
| Strategisch | 15 % |
| Rechtlich | 10 % |
| Daten und KI | 10 % |
| Operativ | 15 % |
| Lieferkette | 20 % |
| Technologie | 15 % |
| Sicherheit und Compliance | 10 % |
| Umwelt | 5 % |

Stufe und Wert beantworten verschiedene Fragen. Die Stufe zeigt die schwächste Stelle, der Wert die Breite. Das Rahmenwerk nutzt beide: die Stufe als Mindestanforderung, den Wert zur Rangfolge.

## Gesichert und möglich

Fehlt eine Angabe, gibt es zwei Zahlen:

- **Gesichert:** Die fehlende Angabe zählt wie der ungünstigste Fall. Fehlendes Wissen führt so nie zu einer zu guten Stufe.
- **Möglich:** Die fehlende Angabe zählt wie der günstigste Fall. Das ist eine Obergrenze, keine Erwartung.

Die Schreibweise `1(3)` bedeutet: gesichert Stufe 1, möglich Stufe 3. Sind alle Angaben bekannt, sind beide Zahlen gleich. Jede Bewertung listet die fehlenden Angaben auf, damit klar ist, welche Recherche die Stufe heben könnte.

Ein Test stellt sicher, dass die Spanne hält: Wird eine fehlende Angabe durch einen beliebigen bekannten Wert ersetzt, liegt die neue Stufe immer zwischen „gesichert“ und „möglich“.

## Wer kontrolliert den Dienst

Drei Begriffe tragen mehrere Regeln:

- **Verantwortliches Unternehmen:** der Betreiber, falls die Variante einen eigenen hat, sonst der Anbieter. Maßgeblich ist der Rechtsraum der obersten Konzernmutter. Hat der Betreiber selbst seinen Sitz außerhalb der EU, zählt der schwächere der beiden Rechtsräume.
- **EU-Betriebsgesellschaft:** ein eigener Betreiber mit Sitz in der EU.
- **Herkunft der Technologie:** der Rechtsraum der Konzernmutter des Anbieters, unabhängig vom Betreiber.

Daraus ergibt sich die **Rechtsraum-Obergrenze**:

| Rechtsraum | Obergrenze |
|---|---|
| EU/EWR | 4 |
| Drittstaat mit Angemessenheitsbeschluss | 3 |
| Sonstiger Drittstaat mit EU-Betriebsgesellschaft | 2 |
| Sonstiger Drittstaat ohne EU-Betriebsgesellschaft | 1 |

Beispiel Delos Cloud: Verantwortlich ist eine SAP-Tochter (EU), die Technologie stammt von Microsoft (USA). Die Entscheidungsgewalt liegt in der EU, die Herkunft der Technologie nicht.

## Die Regeln je Zielbereich

In Klammern steht jeweils der Faktor aus dem Rahmenwerk, auf den sich das Kriterium stützt.

### Strategisch (SOV-1)

| Kriterium | Regel |
|---|---|
| Entscheidungsgewalt („bodies having decisive authority over your services are located within EU jurisdiction“) | Rechtsraum-Obergrenze des verantwortlichen Unternehmens |
| Fortbestand ohne Nicht-EU-Zulieferer („ability to sustain secure operations […] if vendor support is withdrawn“) | Kritischer Zulieferer außerhalb der EU: höchstens 3 |

### Rechtlich (SOV-2)

| Kriterium | Regel |
|---|---|
| Zugriff fremder Behörden („exposure to non-EU laws with cross-border reach (e.g., US CLOUD Act)“) | Rechtsraum-Obergrenze des verantwortlichen Unternehmens |
| Vertragsrecht („the national legal system governing the provider's operations and contracts“) | EU 4, Angemessenheitsbeschluss 3, sonst 1 |
| Übermittlungsgrundlage | Nur relevant, wenn das verantwortliche Unternehmen außerhalb der EU kontrolliert wird oder die Daten außerhalb der EU liegen. Standardvertragsklauseln oder Data Privacy Framework: keine Einschränkung. Keine Grundlage: 0 |

### Daten und KI (SOV-3)

| Kriterium | Regel |
|---|---|
| Datenstandort („strict confinement of storage and processing to European jurisdictions“) | EU zugesichert 4, EU wählbar 3, außerhalb der EU 0 |
| Schlüsselverwaltung („only the customer, not the provider, has effective control over cryptographic access“) | siehe Tabelle unten |
| KI-Training mit Kundendaten | Nein 4, abwählbar 3, ja 1 |

Schlüsselverwaltung, abhängig davon, wem die Herausgabe befohlen werden könnte:

| | Kontrolle in der EU | Angemessenheitsbeschluss | Sonstiger Drittstaat |
|---|---|---|---|
| Schlüssel beim Kunden, außerhalb des Anbieters | 4 | 4 | 4 |
| Kunde steuert, Schlüssel liegen beim Anbieter | 4 | 3 | 2 |
| Anbieter verwaltet die Schlüssel | 3 | 2 | 1 |

### Operativ (SOV-4)

| Kriterium | Regel |
|---|---|
| Ort von Betrieb und Support („operational support is delivered from within the EU“) | Nur EU 4, EU mit Ausnahmen 2, weltweit 1 |
| Wechselfähigkeit („ease of migrating workloads […] without vendor lock-in“) | Offene Formate 4, Format des Anbieters 2, kein Export 1 |
| Betrieb ohne Nicht-EU-Zulieferer („location and legal control of critical suppliers“) | Kritischer Zulieferer außerhalb der EU: höchstens 2 |

### Lieferkette (SOV-5)

| Kriterium | Regel |
|---|---|
| Herkunft der Technologie („origin of software: where and by whom software is architected and programmed“) | Rechtsraum-Obergrenze nach Herkunft |
| Zulieferer außerhalb der EU („degree of reliance on non-EU vendors“) | Kritischer Zulieferer: 2. Nur nicht kritische: 3. Keiner: 4 |

Die 4 gibt es nur, wenn die Zulieferer **vollständig geprüft** sind (Feld `dependencies_complete`). Sonst gilt gesichert die 2, denn ein leerer Eintrag belegt nicht, dass es keine Abhängigkeit gibt.

### Technologie (SOV-6)

| Kriterium | Regel |
|---|---|
| Offenheit („software is accessible under open licenses, with rights to audit, modify, and redistribute“) | siehe Tabelle unten |
| Technologie von Nicht-EU-Zulieferern | Kritische Technologie-Abhängigkeit außerhalb der EU: höchstens 2 |

| | Herkunft EU | Angemessenheitsbeschluss | Drittstaat mit EU-Betriebsgesellschaft | Drittstaat |
|---|---|---|---|---|
| Open Source | 4 | 4 | 4 | 4 |
| Offene Standards | 4 | 3 | 2 | 2 |
| Proprietär | 3 | 3 | 2 | 1 |

Open Source erreicht unabhängig von der Herkunft die 4, weil sich der Code prüfen, ändern und selbst betreiben lässt.

### Sicherheit und Compliance (SOV-7)

| Kriterium | Regel |
|---|---|
| Sicherheitsbetrieb unter EU-Recht („security operations centres and response teams operating exclusively under EU jurisdiction“) | Rechtsraum-Obergrenze des verantwortlichen Unternehmens |
| Zertifikate („attainment of EU and internationally recognized certifications“) | In der EU anerkanntes Testat (BSI C5) 4, nur ISO/IEC 27001: 3, keines belegt: gesichert 1 |

Abgelaufene Zertifikate zählen nicht.

### Umwelt (SOV-8)

| Kriterium | Regel |
|---|---|
| Erneuerbare Energie („sourcing of renewable or low-carbon energy“) | Nachgewiesen 4, zugesagt 2, keine Angabe: gesichert 0 |

## Gesamtwert für ein Unternehmen

Jeder Dienst geht mit seiner Kritikalität ein: gering 1, mittel 2, hoch 3. Ausgegeben werden

- die gewichtete mittlere Stufe, gesamt und je Zielbereich,
- der gewichtete mittlere Souveränitätswert,
- die **schwächste Stufe unter den Diensten mit hoher Kritikalität** und die betroffenen Dienste. Ein Mittelwert darf ein schwaches Kernsystem nicht verdecken,
- die Verteilung der Dienste auf die Stufen und die Zahl der Dienste mit fehlenden Angaben.

## Prüfung an den fünf Stufen der CLAUDE.md

Ein Test je Stufe belegt, dass die Regeln die vereinbarte Auslegung ergeben:

| Stufe | Beispiel im Test | Ergebnis |
|---|---|---|
| 0 | US-Anbieter, Daten außerhalb der EU, keine Übermittlungsgrundlage | 0 |
| 1 | US-Anbieter, EU-Rechenzentrum wählbar, Standardvertragsklauseln, Schlüssel beim Anbieter | 1 |
| 2 | US-Anbieter mit EU-Betriebsgesellschaft, Schlüssel beim Kunden, Export in offenen Formaten | 2 |
| 3 | EU-Anbieter mit einem nicht kritischen Zulieferer außerhalb der EU | 3 |
| 4 | EU-Anbieter, Open Source, alles belegt, keine Abhängigkeit außerhalb der EU | 4 |

## Abweichungen von der CLAUDE.md

Drei Stellen sind strenger oder genauer als die Kurzbeschreibung dort. Alle folgen dem Wortlaut des Rahmenwerks:

1. **Kritische Abhängigkeit ergibt Stufe 2, nicht 3.** Die CLAUDE.md nennt für Stufe 3 „einzelne Nicht-EU-Abhängigkeiten“. Fällt der Dienst ohne den Zulieferer aus, ist das laut Rahmenwerk eine „material non-EU dependency“ (Stufe 2). Beispiel: Personio bei AWS.
2. **Proprietäre EU-Software erreicht höchstens Stufe 3.** Die CLAUDE.md nennt für Stufe 4 „vollständig EU“. Das Rahmenwerk verlangt im Zielbereich Technologie zusätzlich Offenheit. Beispiel: DATEV.
3. **Delos Cloud erreicht Stufe 2.** Die offene Frage aus dem Datenmodell ist damit entschieden: EU-Betreiber, aber eine kritische Technologie-Abhängigkeit von Microsoft.

## Grenzen

- **Wenige Kriterien je Zielbereich.** Das Rahmenwerk nennt je Zielbereich vier bis sechs Faktoren, wir bilden ein bis drei ab. Nicht erfasst sind unter anderem Finanzierung und Wertschöpfung in der EU, Ort der Softwareentwicklung, Herkunft der Hardware, Standort der Sicherheitszentren, Energieeffizienz und Kreislaufwirtschaft.
- **Die Schwellen sind Setzungen.** Dass „EU wählbar“ eine 3 ergibt oder „zugesagt“ eine 2, steht nicht im Rahmenwerk. Sie sind begründet, aber nicht geeicht.
- **Der Rechtsraum wirkt mehrfach.** Wer den Dienst kontrolliert, begrenzt fünf der acht Zielbereiche. US-Anbieter liegen deshalb fast überall bei 1 oder 2. Das entspricht der Logik des Rahmenwerks, macht die Heatmap für diese Anbieter aber gleichförmig, und der Souveränitätswert zählt denselben Umstand mehrfach.
- **„Möglich“ ist eine Obergrenze.** Sie nimmt für jede fehlende Angabe den besten Fall an, auch einen unwahrscheinlichen.
- **Was der Kunde daraus macht, fehlt noch.** Die Regeln bewerten, was ein Dienst ermöglicht. Ob ein Unternehmen eigene Schlüssel wirklich einsetzt oder eine Exit-Strategie hat, kommt mit dem Fragebogen (Phase 4).
- **Keine unabhängige Eichung.** Die Regeln sind nicht gegen Bewertungen Dritter geprüft, etwa gegen Ergebnisse aus Ausschreibungen der Kommission.

## Offene Entscheidungen

1. **Soll der Zielbereich Umwelt in die Gesamtstufe eingehen?** Derzeit ja, wie in der CLAUDE.md festgelegt. Die Folge: Ohne Angabe zur Energieversorgung ist die gesicherte Gesamtstufe 0, auch bei einem sonst vollständig europäischen Dienst. Empfehlung: Umwelt nur im Souveränitätswert zählen (dort mit 5 %), nicht in der Gesamtstufe. Die Stufen des Rahmenwerks beschreiben Kontrolle durch Nicht-EU-Akteure, und dazu sagt die Energieversorgung nichts.
2. **Sind die drei Abweichungen oben gewollt?** Falls nicht, lassen sie sich an je einer Stelle in `rules.py` ändern.

## Ausprobieren

```
cd backend
uv run python -m app.scoring              # Heatmap aller Dienste
uv run python -m app.scoring personio     # Begründung für einen Dienst
```
