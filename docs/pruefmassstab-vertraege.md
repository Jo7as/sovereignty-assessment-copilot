# Prüfmaßstab für die Vertragsanalyse

Stand: 10.11.2026, gilt ab Version `vertrag-v2` der [Arbeitsanweisung](tiefenpruefung-ablauf.md). Umgesetzt in `backend/app/contracts/fields.py` (Bestandteile als Ja-Fragen) und `pipeline.judge` (Regel). Dieses Dokument legt fest, **wann** ein Prüfpunkt als erfüllt, teilweise erfüllt oder nicht gefunden gilt. Es ist das, was ein erfahrener Prüfer im Kopf hat und was die KI in Version 1 nicht hatte.

## Warum ein Prüfmaßstab

Eine Fachkraft für Auslagerungs- oder Datenschutzprüfung liest einen Vertrag nicht frei, sondern gegen eine Liste von Pflichtinhalten. Die Liste kommt aus Gesetz, Aufsicht und Musterverträgen. Für jeden Punkt weiß sie, welche **Bestandteile** eine Klausel haben muss und welche **Einschränkungen** typisch sind. Erst daraus ergibt sich das Urteil „erfüllt“ oder „eingeschränkt“.

Version 1 hat der KI je Punkt nur einen Satz Inhalt gegeben und sie selbst entscheiden lassen. Die Messung zeigt den Preis: Die Abweichungen von der Musterlösung liegen fast alle an der Grenze zwischen VORHANDEN und TEILWEISE.

## Befund der Basismessung (Version 1)

Gemessen am 10.11.2026 mit `scripts/evaluate_contracts.py`, vier AVVs, 72 Felder, Ergebnis in `data/testdata/contracts/results/vertrag-v1.json`:

| Kennzahl | Wert |
|---|---|
| Übereinstimmung (alle Felder) | 65 % |
| Genauigkeit (Angaben der KI mit richtigem Wert) | 64 % |
| Trefferquote (Angaben der Musterlösung gefunden) | 59 % |
| Fälschlich nicht gefunden | 11 % |
| Verwerfungsquote (an der Belegprüfung gescheitert) | 9 % |

Von 25 Fehlern sind 16 Prüfpunkte, bei denen die KI etwas gefunden, aber falsch eingestuft hat. Die Bewertungsfakten sind dagegen weitgehend richtig (operations_location, transfer_basis und ai_training je 4 von 4). Zwei Muster:

1. **Gefühlte Einstufung.** Die KI stuft Klauseln als TEILWEISE ein, die alle Pflichtbestandteile enthalten, und umgekehrt. Ohne Maßstab weiß sie nicht, was „vollständig“ heißt.
2. **Teile werden zu Widersprüchen.** Ein Prüfpunkt ist oft über mehrere Stellen verteilt, etwa Prüfungsrechte auf Seite 7 und Inspektionen auf Seite 8. Die KI bewertet jede Stelle für sich („teilweise“, „vorhanden“), und das Zusammenführen macht daraus „unklar“. Bei Prüfpunkten ergänzen sich Stellen aber, sie widersprechen sich nicht. Ein Prüfer würde sie zusammenlesen.

Dazu kommen zwei Fehler bei `data_export`: „kein Export“, wo der Vertrag nur Löschung oder Rückgabe ohne Format regelt.

Die Musterlösung ist selbst noch ein Entwurf. Einzelne Abweichungen können auch an ihr liegen. Das ändert nichts an den Mustern.

## Vorgehen in Version 2: Bestandteile abfragen, Urteil im Code

Statt „Ist der Punkt vorhanden?“ stellt der Ablauf je Prüfpunkt **einzelne Sachfragen** nach den Bestandteilen unten, jeweils mit Zitat. Das Urteil leitet der Code nach einer festen Regel ab:

- **VORHANDEN:** alle Kernbestandteile belegt, keine typische Einschränkung belegt.
- **TEILWEISE:** etwas belegt, aber ein Kernbestandteil fehlt oder eine Einschränkung ist belegt. Auch eine belegte Einschränkung allein reicht: Eine eingeschränkte Regelung ist eine Regelung.
- **NICHT_GEFUNDEN:** nichts belegt.

Gezählt werden nur Bestandteile, nach denen beim vorgelegten Dokumenttyp gefragt wird. Die Leistungsbeschreibung (30(2)a) steht im Rahmenvertrag; bei einem AVV allein heißt sie „nicht geprüft“, nicht „fehlt“. Liegt der Rahmenvertrag später vor, zählt sie mit.

Einschränkungen werden nur als das abgefragt, was im Text steht (etwa „höchstens einmal im Jahr“). Was fehlt, zeigt sich am fehlenden Kernbestandteil, nicht an einer Einschränkung.

Die Bestandteile werden über alle Stellen und Abschnitte eines Dokuments gesammelt, bevor das Urteil fällt. Damit verschwindet das zweite Muster: Seite 7 liefert die Prüfungsrechte, Seite 8 die Inspektionen, zusammen ergibt das VORHANDEN. Ein Widerspruch bleibt nur bei den Bewertungsfakten möglich, wo zwei Stellen wirklich verschiedene Werte nennen.

Das entspricht der Arbeitsweise mit Prüfliste und trennt **„Was steht da?“** (KI, mit Zitat) von **„Reicht das?“** (Regel, nachvollziehbar). Eine enge Sachfrage beantwortet ein kleines Modell zuverlässiger als ein Gesamturteil. Der Berater sieht außerdem, *welcher* Bestandteil fehlt, nicht nur „teilweise“.

## Ergebnis von Version 2

Gemessen am 10.11.2026, gleiche vier AVVs und gleiche Musterlösung wie bei Version 1, Ergebnis in `data/testdata/contracts/results/vertrag-v2.json`:

| Kennzahl | Version 1 | Version 2 |
|---|---|---|
| Übereinstimmung | 65 % | 85 % |
| Genauigkeit | 64 % | 83 % |
| Trefferquote | 59 % | 80 % |
| Fälschlich nicht gefunden | 11 % | 4 % |
| Prüfpunkte richtig | 28 von 48 | 39 von 48 (erster Lauf 43) |

Die Tabelle zeigt den gespeicherten Lauf. Ein Lauf davor, noch mit einem später entfernten Satz zu Übermittlungsgrundlagen, ergab ebenfalls 85 %, aber anders verteilt: mehr richtige Prüfpunkte, weniger richtige Fakten. Die Ergebnisse schwanken also je Feld, auch bei Temperatur 0. Eine belastbare Messung braucht mehrere Läufe.

**Grenzfälle für die Prüfung der Musterlösung.** Bei diesen Abweichungen urteilt die KI nach dem Maßstab strenger als der Entwurf der Musterlösung. Die Musterlösung wurde nicht angepasst, das entscheidet ein Mensch:

- STACKIT, `dsgvo_28_3_h`: Ziffer 11.7 erlaubt dem Anbieter, eine Inspektion nach seiner Wahl durch einen Prüfbericht zu ersetzen. Die Musterlösung wertet das bei DORA 30(3)e als Einschränkung, bei DSGVO h nicht.
- STACKIT, `dsgvo_28_3_a`: Ziffer 2.3 behält dem Anbieter die Verarbeitung nicht anonymisierter Nutzungsdaten für eigene Zwecke vor, „im Rahmen des datenschutzrechtlich Zulässigen“.
- Salesforce, `dsgvo_28_3_a`: Eine Pflicht, den Kunden über eine gesetzliche Pflicht zu anderer Verarbeitung zu informieren, war im Text nicht auffindbar.
- AWS, `dsgvo_28_3_a`: Die Weisungsbindung erwähnt Übermittlungen in Drittländer nicht ausdrücklich.

Echte Fehler der KI sind dagegen etwa die übersehene Unterstützung bei der Folgenabschätzung im Hetzner-AVV (ein Lauf) und eine Einschränkung bei `dsgvo_28_3_c` im AWS-AVV, die aus einer doppelt verneinten Frage entstand.

## DSGVO Art. 28 Abs. 3

Maßstab sind der Wortlaut von Art. 28 Abs. 3, die Standardvertragsklauseln der Kommission für Auftragsverarbeitung (Durchführungsbeschluss (EU) 2021/915, Klauseln 7 bis 10, im Folgenden SCC) und die EDPB-Leitlinien 07/2020 (Rn. 112 ff.). Die EDPB-Leitlinien betonen, dass ein Vertrag die Pflichten nicht nur wiederholen soll, sondern konkret regeln muss, wie sie erfüllt werden (Rn. 112, 126).

| Punkt | Kernbestandteile | Typische Einschränkungen (→ TEILWEISE) | Quelle |
|---|---|---|---|
| a Weisung | Verarbeitung nur auf dokumentierte Weisung; gilt auch für Übermittlungen in Drittländer; Hinweis, wenn eine Rechtspflicht zur Verarbeitung besteht | eigene Zwecke des Anbieters mit personenbezogenen Kundendaten über die Leistung hinaus (anonymisierte Nutzungsdaten zählen nicht) | Art. 28(3)(a), SCC 7.1, 7.8 |
| b Vertraulichkeit | befugte Personen zur Vertraulichkeit verpflichtet oder gesetzlicher Verschwiegenheit unterworfen | nur ein Teil des Personals erfasst | Art. 28(3)(b), SCC 7.4(b) |
| c Sicherheit | Pflicht zu Maßnahmen nach Art. 32; konkrete Maßnahmen im Vertrag oder in einer Anlage | Anbieter darf Maßnahmen ändern, ohne das Schutzniveau zu halten | Art. 28(3)(c), SCC 7.4, Anh. III, EDPB Rn. 126 |
| d Unterauftragsverarbeiter | vorherige gesonderte oder allgemeine Genehmigung; vorherige Information über Änderungen; Widerspruchsrecht (auch als Kündigungsrecht); gleiche Datenschutzpflichten für den Unterauftragsverarbeiter. Die Haftung des Anbieters folgt schon aus Art. 28(4) | fehlende Information oder fehlendes Widerspruchsrecht (zeigt sich am fehlenden Kernbestandteil) | Art. 28(2), (4), SCC 7.7, EDPB Rn. 152 bis 156 |
| e Betroffenenrechte | Unterstützung bei Anträgen betroffener Personen, auch durch technische Funktionen | keine: „soweit möglich“ steht schon im Gesetz und ist keine Einschränkung des Vertrags | Art. 28(3)(e), SCC 8(a)(b) |
| f Art. 32 bis 36 | **Meldung von Verletzungen** an den Kunden; Unterstützung bei Datenschutz-Folgenabschätzung oder vorheriger Konsultation. Die Sicherheit nach Art. 32 deckt Punkt c ab | nur ein Teil davon geregelt (zeigt sich am fehlenden Kernbestandteil) | Art. 28(3)(f), SCC 8(c), 9 |
| g Löschung oder Rückgabe | Rückgabe (auch als Abruf durch den Kunden); Löschung. Beides, weil der Kunde wählen können muss | nur Löschung ohne Rückgabe (zeigt sich am fehlenden Kernbestandteil) | Art. 28(3)(g), SCC 10, EDPB Rn. 139 bis 142 |
| h Nachweise und Prüfungen | Bereitstellung der nötigen Informationen; Prüfungen **einschließlich Inspektionen** durch den Kunden oder einen von ihm beauftragten Prüfer | Prüfung nur über Berichte, Zertifikate oder Prüfer des Anbieters. Eine begrenzte Häufigkeit ist hier **keine** Einschränkung: SCC 7.6(d) verlangt Prüfungen nur „in angemessenen Abständen“. Anders bei DORA 30(3)(e), das „uneingeschränkte“ Rechte verlangt | Art. 28(3)(h), SCC 7.6(c)(d), EDPB Rn. 143 bis 145 |

## DORA Art. 30

Maßstab ist der Wortlaut von Art. 30, für Unterauftragnehmer zusätzlich die Delegierte Verordnung (EU) 2025/532 (Art. 4 bis 6). Amtliche Musterklauseln nach Art. 30 Abs. 4 waren bei der Recherche nicht auffindbar.

| Punkt | Kernbestandteile | Typische Einschränkungen (→ TEILWEISE) | Quelle |
|---|---|---|---|
| 30(2)a Leistung und Unteraufträge | Beschreibung der Leistungen; ob Unteraufträge zulässig sind; Bedingungen dafür | Unteraufträge allgemein erlaubt, ohne Bedingungen | Art. 30(2)(a), VO 2025/532 Art. 4 |
| 30(2)b Orte | Regionen oder Länder der Leistung; Orte der Datenverarbeitung und -speicherung; Pflicht, Änderungen vorab mitzuteilen | Orte genannt, aber keine Mitteilungspflicht, oder umgekehrt | Art. 30(2)(b) |
| 30(2)d Zugang und Rückgabe | Zugang zu den Daten, Wiederherstellung und Rückgabe in leicht zugänglichem Format; auch bei Insolvenz, Abwicklung oder Einstellung | Rückgabe nur bei Vertragsende; kein Format; nur Löschung | Art. 30(2)(d) |
| 30(3)e Zugang, Inspektion, Audit | Zugangs- und Inspektionsrechte des Finanzunternehmens; Prüfung durch einen Prüfer seiner Wahl; Rechte der Aufsicht | Ersatz durch Berichte oder Zertifikate des Anbieters; Häufigkeit begrenzt; Vergütung für Prüfungen | Art. 30(3)(e) |
| 30(3)f Ausstieg | Ausstiegsstrategie; verbindlicher, angemessener Übergangszeitraum mit fortlaufender Leistung | nur eine Frist zum Abholen der Daten | Art. 30(3)(f) |

Die übrigen Punkte aus Art. 30 (c, e, f, g, h, i, 3a bis 3d) und die Kündigungsgründe nach Art. 28(7) sind nach demselben Muster in Bestandteile zerlegt, eng am Wortlaut. Gemessen werden sie erst, wenn die Musterlösung Rahmenverträge und Leistungsbeschreibungen enthält; bisher enthält sie nur AVVs.

### Korrekturen gegenüber dem ersten Entwurf

Beim Umsetzen in Ja-Fragen wurde jede Einschränkung noch einmal an der Quelle geprüft. Gestrichen wurden Einschränkungen, die das Gesetz oder die Standardvertragsklauseln selbst vorsehen: begrenzte Häufigkeit bei DSGVO h (SCC 7.6(d)), „soweit möglich“ bei e (Art. 28(3)(e)), Rückgabe als Abruf durch den Kunden bei g. Die Musterlösung wurde dafür nicht geändert.

## Bewertungsfakten

Für die Fakten gibt es keine Stufe „teilweise“, aber dieselbe Gefahr, aus wenig Text viel zu machen:

- **data_export:** `KEIN_EXPORT` nur, wenn der Vertrag Rückgabe oder Export ausdrücklich ausschließt. `OFFENE_FORMATE` oder `PROPRIETAER` nur mit Angabe des Formats. Rückgabe ohne Format ist `NICHT_GEFUNDEN`, weil sie über das Format nichts sagt.
- **transfer_basis:** Nennt der Vertrag mehrere Grundlagen, wird jede als eigene Angabe gemeldet. „Unklar“ ist dann das richtige Ergebnis.

## Grenzen

- Der Maßstab sagt, was ein Vertrag enthalten **soll**. Ob eine Einschränkung im Einzelfall vertretbar ist (etwa Prüfung über Zertifikate bei einem großen Cloud-Anbieter), bleibt eine Entscheidung des Beraters.
- BaFin und Bundesbank haben ihre Orientierungshilfe zu Cloud-Auslagerungen 2024 als Aufsichtsmitteilung neu gefasst. Für Banken ist sie der nächste Maßstab, vor allem für Prüfungsrechte entlang der Kette der Unterauftragnehmer. Sie ist hier noch nicht Zeile für Zeile eingearbeitet.

## Quellen

- Verordnung (EU) 2016/679 (DSGVO), Art. 28
- Durchführungsbeschluss (EU) 2021/915, Standardvertragsklauseln zwischen Verantwortlichen und Auftragsverarbeitern, Klauseln 7 bis 10, amtliche deutsche Fassung (CELEX 32021D0915)
- EDPB, Guidelines 07/2020 on the concepts of controller and processor in the GDPR, Version 2.1, Rn. 112 bis 156: https://www.edpb.europa.eu/system/files/2023-10/EDPB_guidelines_202007_controllerprocessor_final_en.pdf
- Verordnung (EU) 2022/2554 (DORA), Art. 28 und 30
- Delegierte Verordnung (EU) 2025/532, Unterauftragsvergabe bei IKT-Dienstleistungen für kritische oder wichtige Funktionen, Art. 4 bis 6, amtliche deutsche Fassung (CELEX 32025R0532)
- BaFin/Deutsche Bundesbank, Aufsichtsmitteilung zu Auslagerungen an Cloud-Anbieter (2024), Nachfolger der Orientierungshilfe von 2018
- Praxis der Vertragsprüfung mit Playbooks: je Klausel Soll-Position, Rückfallposition und nicht akzeptable Fassung; Prüfung in getrennten Schritten (Klauseln finden, gegen Playbook prüfen). Zur Forschung: ContractEval (2025), Bewertung von 19 Modellen auf Klauselebene: https://arxiv.org/abs/2508.03080

Die amtlichen Texte wurden am 10.11.2026 über die Schnittstelle des Amts für Veröffentlichungen der EU abgerufen, die EDPB-Leitlinien direkt beim EDPB.
