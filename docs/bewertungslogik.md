# Bewertungslogik

Stand: Schritte 5.1 bis 5.3, umgesetzt in `backend/app/scoring/`. Die Auslegung der Stufen ist unsere eigene, Jonas hat sie am 14.10.2026 freigegeben.

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
3. **Gesamtstufe.** Die Gesamtstufe eines Dienstes ist der schwächste Zielbereich, ohne Umwelt (siehe „Getroffene Entscheidungen“).
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

Umwelt geht nur in den Wert ein, nicht in die Gesamtstufe. Stufe und Wert beantworten verschiedene Fragen. Die Stufe zeigt die schwächste Stelle, der Wert die Breite. Das Rahmenwerk nutzt beide: die Stufe als Mindestanforderung, den Wert zur Rangfolge.

## Gesichert und möglich

Fehlt eine Angabe, gibt es zwei Zahlen:

- **Gesichert:** Die fehlende Angabe zählt wie der ungünstigste Fall. Fehlendes Wissen führt so nie zu einer zu guten Stufe.
- **Möglich:** Die fehlende Angabe zählt wie der günstigste Fall. Das ist eine Obergrenze, keine Erwartung.

Die Schreibweise `1(3)` bedeutet: gesichert Stufe 1, möglich Stufe 3. Sind alle Angaben bekannt, sind beide Zahlen gleich. Jede Bewertung listet die fehlenden Angaben auf, damit klar ist, welche Recherche die Stufe heben könnte.

Ein Test stellt sicher, dass die Spanne hält: Wird eine fehlende Angabe durch einen beliebigen bekannten Wert ersetzt, liegt die neue Stufe immer zwischen „gesichert“ und „möglich“.

## Wer kontrolliert den Dienst

Drei Begriffe tragen mehrere Regeln:

- **Verantwortliches Unternehmen:** der Betreiber, falls die Variante einen eigenen hat, sonst der Anbieter. Maßgeblich ist der schwächere Rechtsraum aus dem eigenen Sitz und dem Sitz der obersten Konzernmutter. Eine EU-Tochter eines US-Konzerns unterliegt dem CLOUD Act über die Mutter, eine US-Tochter eines EU-Konzerns (Beispiel SAP Concur) über den eigenen Sitz. Dasselbe gilt für Zulieferer.
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
| Übermittlungsgrundlage | Nur relevant, wenn das verantwortliche Unternehmen in einem Drittstaat ohne Angemessenheitsbeschluss sitzt oder die Daten außerhalb der EU liegen. Für einen Staat mit Angemessenheitsbeschluss genügt dieser (Art. 45 DSGVO). Standardvertragsklauseln, Data Privacy Framework, Angemessenheitsbeschluss oder verbindliche Unternehmensregeln: keine Einschränkung. Keine Grundlage: 0 |

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

## Präzisierungen gegenüber der ersten Kurzbeschreibung

Drei Stellen sind strenger oder genauer als die ursprüngliche Kurzbeschreibung in der CLAUDE.md. Alle folgen dem Wortlaut des Rahmenwerks, Jonas hat sie freigegeben, und die CLAUDE.md ist angepasst:

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

## Getroffene Entscheidungen

1. **Umwelt zählt nicht in der Gesamtstufe** (Entscheidung vom 14.10.2026). Die Stufen des Rahmenwerks beschreiben Kontrolle durch Nicht-EU-Akteure, und dazu sagt die Energieversorgung nichts. Sonst würde eine fehlende Angabe zum Ökostrom die Gesamtstufe eines sonst europäischen Dienstes auf 0 setzen. Umwelt bleibt im Souveränitätswert mit 5 % und in der Heatmap sichtbar.
2. **Die drei Präzisierungen oben gelten** (Entscheidung vom 14.10.2026).

## Von der Bewertung zur Roadmap

Umgesetzt in `backend/app/roadmap/`.

**Fragen an die Anbieter.** Jede fehlende Angabe wird zu einer Frage an den Anbieter, etwa „Wo werden unsere Daten gespeichert und verarbeitet?“. **Kernfragen** sind die Lücken, die einen der schwächsten Zielbereiche begrenzen und damit die Gesamtstufe unten halten. Alle anderen Fragen verbessern nur Teilbereiche oder den Souveränitätswert. Zu jeder Frage wird berechnet, wie weit eine günstige Antwort den Dienst allein heben würde.

**Maßnahmen.** Zwei Arten:

- **Wechsel der Variante** beim selben Anbieter, etwa von Microsoft 365 zur Delos Cloud. Der Aufwand gilt pauschal als mittel, weil meist nur der Vertrag wechselt. Das ist eine Annahme.
- **Wechsel zu einer EU-Alternative** aus der Datenbank, mit dem dort hinterlegten groben Aufwand. Auch dieser Aufwand ist eine Einschätzung, keine belegte Angabe.

Aufgenommen wird nur, was die gesicherte oder die mögliche Stufe verbessert. Sinkt die gesicherte Stufe, weil zur Zielvariante Angaben fehlen, steht das als Hinweis dabei.

**Priorität.** Kritikalität (gering 1, mittel 2, hoch 3) mal Abstand zur Höchststufe. Bei gleicher Priorität kommt zuerst, was die Stufe am stärksten heben kann.

**Wellen.**

| Welle | Inhalt |
|---|---|
| 1, schnelle Erfolge (0 bis 6 Monate) | Klärungen mit den Anbietern, Maßnahmen mit geringem Aufwand |
| 2, mittelfristig (6 bis 18 Monate) | Maßnahmen mit mittlerem Aufwand, Wechsel der Variante |
| 3, strategisch (ab 18 Monaten) | Maßnahmen mit hohem Aufwand, etwa Migrationen |

**Grenze.** Maßnahmen gibt es nur, wo die Datenbank eine Alternative oder eine bessere Variante kennt. Für viele Bankdienstleister (SWIFT, Avaloq) gibt es keine oder kaum Alternativen. Dort bleibt die Klärung mit dem Anbieter der einzige Hebel, und das ist auch in der Praxis so.

## Reifegrad des Unternehmens

Umgesetzt in `backend/app/questionnaire/`, Fragen in `data/questionnaire.yaml`.

Der Fragebogen misst, wie gut ein Unternehmen seine Abhängigkeit von Anbietern steuert. 21 Fragen ergeben einen **Reifegrad 0 bis 4** in fünf Handlungsfeldern: Strategie und Steuerung, Steuerung der Anbieter, Exit und Ersetzbarkeit, Notfall und Wiederherstellung, Daten und Schlüssel.

- **Getrennt von den Stufen der Anbieter.** Der Reifegrad verändert keine SEAL-Stufe. Ein Anbieter unterliegt dem CLOUD Act, ob die Bank einen Exit-Plan hat oder nicht. Der Exit-Plan senkt aber ihr Risiko. Beide Aussagen stehen deshalb nebeneinander.
- **Mittelwert statt Minimum.** Der Reifegrad eines Handlungsfelds ist der Mittelwert seiner Fragen. Bei einem Dienst entscheidet das schwächste Glied, weil eine einzige Lücke den Zugriff von außen ermöglicht. Der Reifegrad beschreibt dagegen, wie weit ein Unternehmen insgesamt ist, und eine einzelne schwache Antwort soll das Feld nicht auf 0 setzen. Der Gesamtwert ist der Mittelwert der fünf Felder.
- **Gesichert und möglich** wie bei den Anbietern: Offene Fragen zählen im gesicherten Wert mit 0, im möglichen mit 4. „Weiß nicht“ ist eine Antwort und zählt in beiden Werten mit 0.
- **Rundung** auf eine Stelle, kaufmännisch (0,25 wird 0,3), und erst am Ende. Der Gesamtwert wird aus den ungerundeten Feldwerten gebildet.
- **Profilfragen** (Sektor, Beschäftigte, Umsatz, Bilanzsumme) und die Fragen zu Risikotoleranz und Zielstufe zählen nicht zum Reifegrad.

Jede Frage mit Rechtspflicht nennt ihre Grundlage in DORA oder NIS2 mit wörtlicher Fundstelle aus dem amtlichen Text.

## DORA und NIS2

Umgesetzt in `backend/app/compliance/`, Fundstellen in `data/compliance.yaml` und `data/questionnaire.yaml`, alle wörtlich aus dem amtlichen deutschen Text.

**Welches Recht gilt.** Aus den Profilantworten:

| Recht | Gilt, wenn | Fundstelle |
|---|---|---|
| DORA | der Sektor ein Finanzunternehmen ist | Art. 2 Abs. 1 DORA |
| NIS2 | der Sektor in Anhang I oder II steht und das Unternehmen mindestens mittelgroß ist | Art. 2 Abs. 1 NIS2 |
| NIS2, wesentliche Einrichtung | Anhang I und Schwellenwerte für mittlere Unternehmen überschritten | Art. 3 Abs. 1 Buchst. a NIS2 |
| NIS2, wichtige Einrichtung | alle anderen Fälle in Anhang I oder II | Art. 3 Abs. 2 NIS2 |

Die Größe folgt der KMU-Empfehlung 2003/361/EG: KMU sind Unternehmen mit weniger als 250 Beschäftigten und entweder höchstens 50 Mio. EUR Umsatz oder höchstens 43 Mio. EUR Bilanzsumme. Klein sind Unternehmen mit weniger als 50 Beschäftigten, bei denen Umsatz oder Bilanzsumme höchstens 10 Mio. EUR beträgt.

Gelten beide Gesetze, wie bei Kreditinstituten, geht DORA vor (Art. 1 Abs. 2 DORA, Art. 4 NIS2). Hinweise stützen sich dann nur auf DORA. Fehlt eine Angabe, die über die Anwendbarkeit entscheidet, lautet das Ergebnis „nicht bestimmbar“.

**Hinweise aus dem Fragebogen.** Jede Reifegrad-Frage mit einer Grundlage im geltenden Recht wird zum Hinweis, wenn die Antwort unter Stufe 3 („schriftlich festgelegt“) liegt: Stufe 0 ist eine Lücke, Stufe 1 und 2 sind teilweise erfüllt. Unbeantwortete Pflichtfragen werden getrennt aufgelistet.

**Hinweise aus dem IT-Bestand** (wenn DORA gilt), jeweils nur für Dienste, die kritische oder wichtige Funktionen unterstützen:

- kein Exit-Plan angegeben (Art. 28 Abs. 8 DORA). Ein Dienst mit mehreren Einträgen hat nur dann einen Exit-Plan, wenn jeder Eintrag ihn nennt.
- mindestens zwei solcher Dienste beim selben Konzern, gemessen an der obersten Konzernmutter (Art. 29 Abs. 1 Buchst. b DORA)
- laut Bestand „nicht ersetzbar“ oder „sehr komplex“ zu ersetzen (Art. 29 Abs. 1 Buchst. a DORA: „nicht ohne Weiteres ersetzbar“)

**Grenzen.** Nicht abgebildet sind nationale Umsetzungsgesetze der NIS2, Einrichtungen, die NIS2 unabhängig von der Größe erfasst (Art. 2 Abs. 2), und Partner- oder verbundene Unternehmen bei der Größe. Die Hinweise sind eine Vorprüfung und ersetzen keine Rechtsberatung.

## Außenscan

Umgesetzt in `backend/app/scan/`, Erkennungsmerkmale mit Quelle in `data/detection.yaml`.

Aus einer Domain liest das Tool, was von außen sichtbar ist, in vier Schritten:

1. **E-Mail und Domain:** Mailserver (MX), die Absender im SPF-Eintrag, die Nameserver (NS) und die Zertifizierungsstellen im CAA-Eintrag.
2. **Absender im SPF-Eintrag:** Der ganze SPF-Baum wird durchlaufen (include und redirect, höchstens 20 Abfragen, ohne Schleifen). Für alle öffentlichen Adressen wird der Netzbetreiber bei RIPEstat abgefragt, je Netzblock einmal, höchstens 60, parallel. So werden Versanddienste wie Amazon SES, Mailgun oder Salesforce erkannt, ohne dass ein eigenes Merkmal nötig ist. Absender, die schon über ein Merkmal erkannt sind (etwa Microsoft 365), werden nicht noch einmal aufgelöst.
3. **Hosting:** die CNAME-Kette von `www.<domain>` und der Netzbetreiber der Website.
4. **Website:** Startseite laden und auswerten, was sie tatsächlich lädt (Skripte, Iframes, Stylesheets, Vorverbindungen, Bilder). Ein Link zu LinkedIn im Fußbereich ist kein eingebundener Dienst. Hosts, die nur in eingebetteten Skripten stehen, zählen nur, wenn sie zu einem bekannten Dienst gehören, weil dort oft bloße Links als Daten stehen. Dazu wird der Link zum Impressum gesucht. WordPress und seine Plugins werden an den typischen Pfaden erkannt (`/wp-content/plugins/<name>/`). Sie sind Technik, kein Anbieter, und erscheinen ohne Dienst.

Erkannte Dienste werden in **Unternehmensdienste** (E-Mail, Domain, Hosting) und **Website-Werkzeuge** (nur auf der Website gefunden, etwa Tracking) getrennt. Website-Werkzeuge haben für die Souveränität eines Unternehmens meist geringe Kritikalität.

- **Merkmale sind Daten mit Beleg.** Dass `*.mail.protection.outlook.com` auf Microsoft 365 hinweist, steht in der Dokumentation von Microsoft. Diese Fundstelle wird wie jede andere nachgeprüft.
- **Zwei Stärken.** `NUTZUNG`: Der Dienst wird nachweislich genutzt, etwa weil die E-Mails über ihn laufen. `HINWEIS`: Der Fund deutet auf den Dienst hin, etwa eine Website im Netz von Amazon. Das heißt nicht, dass das Unternehmen sonst AWS nutzt.
- **Nicht raten.** Funde ohne belegtes Merkmal erscheinen roh, etwa „Website im Netz der Hetzner Online GmbH“. Netze, die zu mehreren Produkten eines Anbieters passen (Google, IONOS), werden keinem Dienst zugeordnet.
- **Schutz interner Systeme.** Nur öffentliche Domains werden angenommen, und nur öffentliche IP-Adressen gehen an RIPEstat. Beim Laden der Website gilt für jede Anfrage und jede Weiterleitung: nur http und https, nur Standardports, keine IP-Adressen, und der Hostname muss ausschließlich auf öffentliche Adressen zeigen. Dazu kommen Grenzen für Zeit (8 Sekunden), Größe (3 MB) und Weiterleitungen (4). Verbleibende Lücke ist DNS-Rebinding, für den Betrieb gehört der Abruf deshalb in eine abgeschottete Umgebung.
- **Grenze.** Der Außenscan sieht nur, was ein Unternehmen nach außen zeigt. Kernbanksystem, Backup oder Meldewesen tauchen dort nie auf. Er ist deshalb ein Einstieg in das Assessment, nie die ganze Bewertung.

## Unternehmensprofil aus der Website

Umgesetzt in `backend/app/scan/profile.py`, `suggest.py` und `quick.py`.

- **Impressum:** gefunden über den Link der Startseite, gereiht nach Sicherheit (Linktext „Impressum“ vor einer Adresse auf `/impressum` vor einer bloßen Erwähnung), sonst über die üblichen Adressen. Eine Seite gilt nur als Impressum, wenn sie Registernummer, USt-ID oder § 5 nennt. Ausgelesen werden Firmenname, Registergericht und Nummer, USt-ID und ein Hinweis auf die BaFin, jeweils mit wörtlichem Ausschnitt.
- **GLEIF:** Ein Eintrag gilt nur, wenn Name und Registernummer zusammenpassen. Die Nummer allein ist nicht eindeutig (für „HRB 7727“ gibt es sechs Firmen bei verschiedenen Amtsgerichten), der Name allein auch nicht (drei Einträge für „IONOS SE“). Aus dem Eintrag kommen LEI und oberste Konzernmutter.
- **Vorschläge der KI** für Branche und Beschäftigte: Jede Angabe muss ein wörtliches Zitat aus der Website haben. Das Tool prüft es. Steht das Zitat nicht so im Text oder kommt die Zahl darin nicht vor, wird der Vorschlag verworfen. Die Branche darf nur aus der Liste des Fragebogens stammen. Vorschläge werden im Fragebogen bestätigt.
- **Grenzen:** Manche Websites sperren automatische Abrufe (die Bank ING etwa hielt nach mehreren Testabrufen jede Anfrage hin). Handelsregister und BaFin-Datenbank haben keine Schnittstelle und werden nicht automatisch abgefragt.

## Ausprobieren

```
cd backend
uv run python -m app.scoring              # Heatmap aller Dienste
uv run python -m app.scoring personio     # Begründung für einen Dienst
```
