# Interview-Notizen

Pro Phase: Welche Entscheidung wurde getroffen, und warum? Grundlage für die spätere Fallstudie.

## Phase 0: Projekt aufsetzen

### 0.1 Ordnerstruktur
- **Backend und Frontend getrennt:** Die Bewertungslogik ist über die API unabhängig von der Oberfläche nutzbar, etwa später für den PDF-Bericht oder die PowerPoint-Ausgabe.
- **`data/` außerhalb des Codes:** Die Anbieterdaten sind der eigentliche Wert des Tools. Als YAML/CSV kann sie auch jemand ohne Programmierkenntnisse pflegen und prüfen.
- **`docs/` von Anfang an:** Entscheidungen werden festgehalten, während sie fallen, nicht nachträglich rekonstruiert.

### 0.2 Git und GitHub
- **Versionierung ab dem ersten Tag:** Jeder Schritt ist nachvollziehbar und umkehrbar, die Commit-Historie zeigt, wie das Projekt gewachsen ist.
- **`.env` in der `.gitignore`, bevor es Geheimnisse gibt:** API-Schlüssel und Datenbankpasswort können so nie versehentlich im Repository landen.
- **Repository zunächst privat:** Öffentlich erst in Phase 11, wenn README und Demo stehen, damit niemand ein halbfertiges Projekt sieht.

### 0.3 Python-Umgebung
- **uv statt venv + requirements.txt:** Die Lock-Datei hält die exakten Versionen aller Pakete fest. Jeder, der das Projekt klont, bekommt mit einem Befehl dieselbe Umgebung, auch der Server beim Online-Stellen.
- **Pakete erst bei Bedarf:** Jede Abhängigkeit ist ein Wartungs- und Sicherheitsrisiko. Bei einem Tool, das Abhängigkeiten von Anbietern bewertet, sollte die eigene Liste kurz und begründbar sein.
- **Tests in `backend/tests/`:** Die Python-Tests gehören zum Backend-Projekt, das Frontend bekommt später eigene.

### 0.4 Minimale FastAPI-App
- **Health-Endpunkt als kleinste lauffähige Version:** Der Hosting-Dienst nutzt ihn später, um zu prüfen, ob die Anwendung läuft.
- **Erst der Test, dann der Code:** Der Test beschreibt das gewünschte Verhalten, bevor es existiert. So ist belegt, dass er wirklich etwas prüft.

### Planänderung: KI-Modul
- **Austauschbares KI-Modul schon in Phase 2 statt Phase 9:** Die KI wird bereits für die Zuordnung von Freitext gebraucht. Ein Modul mit fester Schnittstelle verhindert, dass die Anbindung zweimal gebaut wird, und der Anbieter lässt sich wechseln, ohne den Rest anzufassen.

### 0.5 PostgreSQL
- **Datenbank per Docker Compose:** Sie startet mit einem Befehl und ist auf jedem Rechner dieselbe Version (PostgreSQL 17).
- **Zugangsdaten in der Umgebung statt im Code:** Dieselbe Anwendung läuft lokal und später beim Hosting ohne Änderung. Ins Repository kommt nur die Vorlage `.env.example`.
- **Datenbank nur lokal erreichbar:** Der Port ist an `127.0.0.1` gebunden, aus dem Netzwerk kommt niemand heran.
- **Health-Endpunkt prüft die Datenbank mit:** Fällt sie aus, antwortet er mit Status 503 statt 200. Ein Ausfall wird so sofort sichtbar, statt erst beim ersten Nutzer.

### Phase 0 insgesamt
Das Fundament steht, bevor die erste Fachlogik entsteht: Versionierung, reproduzierbare Umgebung, Tests und Datenbank. Jeder spätere Schritt lässt sich dadurch einzeln prüfen und bei Bedarf zurücknehmen.

## Phase 1: Datenmodell und Anbieterdatenbank

### 1.1 Datenmodell
- **Fakten statt Bewertungen speichern:** Ändert sich die Auslegung der Stufen, wird eine Regel angepasst und nicht 150 Einträge. Jede Stufe lässt sich auf belegte Fakten zurückführen.
- **Rechtsraum über die oberste Konzernmutter:** Maßgeblich ist, wessen Recht auf den Konzern durchgreift (CLOUD Act), nicht der Sitz der Tochter oder der Serverstandort.
- **Varianten je Dienst:** Derselbe Dienst schneidet je nach Vertrag und Betreiber unterschiedlich ab. Das macht Verbesserungen ohne Anbieterwechsel sichtbar.
- **Abhängigkeiten als eigene Tabelle:** Sie unterscheiden einen EU-Anbieter auf US-Infrastruktur von einem vollständig europäischen Angebot.
- **„Unbekannt“ ist ein eigener Wert:** Die Bewertung behandelt ihn wie den ungünstigsten Fall. Fehlendes Wissen führt so nie zu einer zu guten Stufe.
- **Nachweis je Feld:** Bei jeder Aussage ist klar, welche Quelle sie stützt. Dieselbe Tabelle nimmt später die Fundstellen aus Verträgen auf.

### 1.2 Modelle und Migrationen
- **Migrationen statt Tabellen von Hand:** Jede Änderung am Datenmodell ist ein versionierter Schritt, der sich nachvollziehen und zurücknehmen lässt. Beim Hosting wird die Datenbank mit demselben Befehl aktualisiert wie lokal.
- **Regeln in der Datenbank statt nur im Code:** Die Daten bleiben auch dann stimmig, wenn ein Import direkt hineinschreibt. Beispiele: höchstens eine Standardvariante je Dienst, „geprüft“ nur mit Prüfdatum, unbekannte Werte einer Werteliste werden abgelehnt.
- **Ein Test vergleicht Migration und Modelle:** Er schlägt fehl, sobald beide auseinanderlaufen. Die automatisch erzeugte Migration hatte jede Werteliste dreifach angelegt, das ist erst durch diesen Test aufgefallen.
- **Eigene Testdatenbank:** Tests laufen nie gegen die echten Daten und verwerfen ihre Änderungen nach jedem Test.

### 1.3 Seed-Format
- **YAML statt CSV:** Ein Dienst hat verschachtelte Angaben (Varianten, darunter Zertifikate und Nachweise). In CSV wären das sechs verknüpfte Tabellen, die niemand gern von Hand pflegt.
- **Eine Datei je Dienst:** Jede Änderung an einem Dienst ist in Git ein eigener, prüfbarer Schritt. Das passt zur Regel, dass ein Mensch jeden KI-Vorschlag bestätigt.
- **Nachweis direkt am Feld:** Wer eine Angabe prüft, sieht die Quelle an derselben Stelle.
- **Weglassen statt raten:** Was nicht recherchiert ist, gilt als unbekannt und wird streng bewertet.

### 1.4 Prüfstatus in drei Stufen
- **Ehrlich ausweisen, wer geprüft hat:** `KI_VORSCHLAG`, `KI_NACHGEPRUEFT`, `GEPRUEFT`. Die Anbieterdaten prüft die KI selbst nach, das Tool behauptet aber nie eine menschliche Prüfung, die nicht stattgefunden hat.
- **Grenze der Selbstprüfung:** Sie findet erfundene und veraltete Fundstellen, aber keine falsche Auslegung. Deshalb bleibt die menschliche Bestätigung als höchste Stufe erhalten, etwa für Dienste mit hoher Kritikalität.
- **Nachprüfung als Skript:** `verify_evidence.py` ruft jede Quelle erneut ab und sucht die Fundstelle im Wortlaut. Es lässt sich jederzeit wiederholen und zeigt damit auch, wenn ein Anbieter seine Seite später ändert.
- **Merkmale beschreiben Möglichkeiten:** Eingetragen ist die beste verfügbare Option einer Variante. Ob ein Unternehmen sie nutzt, klärt der Fragebogen. So trennt das Tool, was der Anbieter kann, von dem, was der Kunde daraus macht.

### 1.4 Erste 20 Dienste
- **Pflichtangaben zuerst:** Konzernmutter, Datenstandort, Schlüsselverwaltung, Zertifikate und Abhängigkeiten bestimmen die Stufe. Alles andere wird später nachgetragen und gilt bis dahin als unbekannt.
- **Nicht belegbar heißt nicht eingetragen:** Zwei Anbieter sperren automatische Abrufe. Sie stehen ohne Merkmale in der Datenbank und werden entsprechend streng bewertet, statt mit Wissen aus dem Gedächtnis der KI gefüllt zu werden.
- **Funde, die nur die Recherche zeigt:** Personio und Atlassian laufen laut eigenen Unterlagen bei AWS, ein Rechenzentrum der IONOS Cloud wird von einem US-Unternehmen betrieben, SAP S/4HANA Cloud wird je nach Bereitstellung bei Microsoft oder Google gehostet. Genau solche Abhängigkeiten sieht ein Außenscan nicht.

### 1.5 Ladeskript
- **Dateien sind die Quelle der Wahrheit, die Datenbank ihr Abbild:** Jede Änderung an den Anbieterdaten läuft über Git und bleibt nachvollziehbar. Die Datenbank lässt sich jederzeit aus den Dateien neu aufbauen.
- **Erst alles prüfen, dann schreiben:** Das Skript sammelt alle Fehler mit Datei und Feld und schreibt bei einem Fehler nichts. Ein halb geladener Stand kann nicht entstehen.
- **Unbekannte Felder werden abgelehnt:** Ein Tippfehler wie `data_lokation` würde sonst still ignoriert, und das Merkmal gälte unbemerkt als unbekannt.
- **Nummern bleiben stabil:** Dienste und Varianten werden aktualisiert statt gelöscht und neu angelegt. Spätere Assessments verweisen auf sie.

## Phase 5: Bewertungslogik

### 5.1 bis 5.3 Regeln, Gesamtstufe, Gesamtwert
- **Am Wortlaut des EU-Rahmenwerks ausgerichtet:** Jedes Kriterium stützt sich auf einen dort genannten Faktor. Was Auslegung ist, steht als Auslegung in der Dokumentation.
- **Obergrenzen statt Punkte:** Jedes Kriterium nennt die Stufe, die es höchstens zulässt, und den Grund. Die Stufe eines Zielbereichs ist die niedrigste Obergrenze. So lässt sich jede Stufe auf eine konkrete Schwäche zurückführen, und das Rahmenwerk schreibt genau das vor.
- **Gesichert und möglich:** Fehlende Angaben zählen einmal als ungünstigster, einmal als günstigster Fall. Das Tool behauptet nichts, was es nicht weiß, und zeigt zugleich, welche Recherche sich lohnt.
- **Regeln ohne Datenbank:** Die Regeln rechnen auf einfachen Fakten. Sie lassen sich dadurch in Millisekunden testen und später unverändert für Vertragsdaten nutzen.
- **Der schwächste kritische Dienst steht neben dem Mittelwert:** Ein Durchschnitt über das Portfolio würde ein schwaches Kernsystem verdecken.
- **Tests, die mehr prüfen als Beispiele:** Zufällig erzeugte Fälle belegen, dass eine bessere Angabe nie zu einer schlechteren Stufe führt und dass die Spanne aus gesichert und möglich hält. Zusätzlich wurde jede Zahl in den Regeln testweise verändert, alle 110 Veränderungen fallen in den Tests auf.
- **Lehre aus der Selbstprüfung:** Die erste Fassung dieser Kontrolle lieferte ein falsches „alles in Ordnung“, weil Python geänderte Dateien nicht neu eingelesen hat. Aufgefallen ist das an einem Ergebnis, das nicht stimmen konnte. Auch eine Prüfung muss geprüft werden.
- **Umwelt aus der Gesamtstufe genommen:** Die Stufen messen Kontrolle durch Nicht-EU-Akteure. Ein Kriterium, das dazu nichts aussagt, soll nicht über die Gesamtstufe entscheiden. Es bleibt im gewichteten Wert, so wie das Rahmenwerk es gewichtet.

### 1.7 Nachtragen mit Selbstprüfung
- **Eine Fundstelle muss den Wert tragen, nicht nur existieren:** DATEV und SAP versichern, dass ihre externen KI-Anbieter keine Kundendaten zum Training nutzen. Über die eigene Nutzung sagen beide nichts. Deshalb ist bei beiden kein Wert eingetragen. Personio dagegen sagt es über sich selbst.
- **Die Recherche findet Abhängigkeiten, die niemand vermutet:** Der KI-Assistent von DATEV läuft auf Microsoft Azure. Das senkt die mögliche Stufe von DATEV im Bereich Lieferkette.
- **Erklärungen gehören zur Prüfung:** Ein Test fiel durch, weil eine Begründung einen bekannten Zulieferer verschwieg. Die Stufe stimmte, die Erklärung war unvollständig. Für ein Beratungswerkzeug zählt beides.
- **Grenze öffentlicher Quellen:** Wo Support-Mitarbeitende sitzen, steht fast nie öffentlich. Solche Angaben gehören in die Tiefenprüfung mit Vertragsunterlagen (Phase 9).

## Phase 2: IT-Bestand und Testdaten

### Planänderung: vom Ergebnis her planen
- **Erst ein vollständiger Durchlauf, dann die Breite:** Statt 150 Dienste auf Vorrat zu recherchieren, legt die Musterbank fest, welche Dienste gebraucht werden. Ein Interviewer bewertet eine Fallstudie, die von Anfang bis Ende trägt, nicht die Größe einer Datenbank.

### 2.1 Vorlage für den IT-Bestand
- **Wenig Pflicht, viel Nutzen:** Nur vier Spalten sind Pflicht. Alles, was sich aus der Anbieterdatenbank ableiten lässt (Datenstandort, Konzernmutter, Zertifikate), fragt die Vorlage gar nicht erst ab. Das senkt die Hürde für den Kunden und ist zugleich das Verkaufsargument des Tools.
- **Anschlussfähig an DORA:** Acht Spalten entsprechen Feldern des DORA-Informationsregisters, mit den amtlichen Wertelisten. Eine Bank füllt die Vorlage einmal aus und hat damit auch einen Teil ihres Registers. Die Feldliste stammt aus dem Dokument der europäischen Aufsichtsbehörden, nicht aus Sekundärquellen.
- **Eine Definition, zwei Verwendungen:** Die Spalten sind einmal im Code beschrieben. Daraus entstehen die Excel-Vorlage und später der Import. Beide können nicht auseinanderlaufen.
- **Keine Beispieldaten im Eingabeblatt:** Beispiele stehen in der Ausfüllhilfe, damit sie nie versehentlich als echter Bestand importiert werden.

### 2.2 Musterbank AG
- **Realistisch statt sauber:** Die 58 Einträge stehen so im Bestand, wie eine Bank sie führt: Abkürzungen („O365“, „SFDC“), Produktnamen („Teams Telefonie“), Schatten-IT, ein Tippfehler und drei Eigenentwicklungen ohne Marktangebot. Nur so zeigt die Zuordnung, was sie kann.
- **Die Lösung liegt getrennt bereit:** Zu jedem Eintrag ist festgehalten, welcher Dienst gemeint ist. Damit lässt sich die Trefferquote der automatischen Zuordnung messen, statt sie zu behaupten.
- **Bewusst gewählte Fälle für die Bewertung:** Kernbankensystem aus der Schweiz mit japanischem Mutterkonzern, US-Zahlungsabwickler, EU-Infrastruktur als Backup, US-Sicherheitsdienste. Die Heatmap soll Unterschiede zeigen, nicht nur Einsen.

### 1.6 Dienste der Musterbank
- **Die Prüfung gegen die Testdaten hat angeschlagen:** Ein Skript vergleicht jede Schreibweise in der Datenbank mit den Einträgen der Musterbank. Drei Schreibweisen hatte ich unbewusst aus den Testdaten übernommen („Okta SSO“, „SAS Risk“, „SuccessFactors Learning“). Sie sind entfernt. Ohne diese Kontrolle wäre die spätere Trefferquote geschönt gewesen.
- **Die Gegenrichtung bleibt eine Schwäche:** Die Musterbank habe ich geschrieben, als die Schreibweisen der ersten 20 Dienste schon feststanden („O365“, „SFDC“). Für diese Dienste ist die gemessene Trefferquote vermutlich zu gut. Ein unabhängiger Testdatensatz, den jemand ohne Kenntnis der Datenbank schreibt, wäre der saubere Nachweis.
- **Nachsehen statt vermuten:** Veeam hätte ich als US-Unternehmen eingetragen. Die Datenschutzerklärung nennt die Schweiz als Sitz der Muttergesellschaft. Gerade die Herkunft entscheidet über die Stufe.
- **Das Modell lernt mit:** Angemessenheitsbeschluss und verbindliche Unternehmensregeln fehlten als Übermittlungsgrundlage, und eine US-Tochter eines EU-Konzerns (SAP Concur) wäre als europäisch durchgegangen. Beides ist jetzt abgebildet, mit Tests.

### 2.3 Import
- **Alle Fehler auf einmal, mit Zeile und Spalte:** Wer eine Datei mit 60 Zeilen hochlädt, will nicht 20-mal korrigieren und neu hochladen. Das Tool meldet jeden Fehler in einem Durchgang.
- **Nachsichtig beim Format, streng beim Inhalt:** Überschriften ohne Sternchen, „HOCH“ statt „hoch“, Semikolon oder Komma, Windows-Zeichensatz: alles wird erkannt. Ein Wert außerhalb der Liste („sehr hoch“) wird dagegen abgelehnt, mit den erlaubten Werten in der Meldung.
- **Sicherheit beim Hochladen:** Größen- und Zeilengrenze, nur zwei Dateitypen, und Excel-Dateien werden mit einem abgesicherten XML-Leser geöffnet. Hochgeladene Dateien kommen von außen und gelten als nicht vertrauenswürdig.
- **Ein Fehlerformat für die ganze API:** Jeder Fehler hat die Form `{"error": {"code", "message"}}`. Die Oberfläche muss nur einen Fall behandeln.

### 2.4 und 2.5 Zuordnung
- **Erst Regeln, dann KI:** Ein Textvergleich ordnet zu, wenn ein Name oder eine Schreibweise als ganze Wortfolge vorkommt, mit Tippfehlern, oder wenn ein Markenwort nur zu einem Dienst passt. Nur was er nicht sicher zuordnet, geht an die KI. Das ist billiger, schneller, nachvollziehbar und bei jedem Lauf gleich.
- **Lieber offen als falsch:** Der Textvergleich ordnet nur bei deutlichem Abstand zum zweitbesten Dienst zu. Ergebnis an der Musterbank: 53 von 58 sicher und richtig (91 %), keine einzige falsche automatische Zuordnung. Ein falscher Treffer, den niemand prüft, wäre schlimmer als ein offener Eintrag.
- **Die KI darf nur aus dem Katalog wählen:** Jede Antwort wird gegen die Datenbank geprüft, erfundene Dienste werden verworfen. KI-Vorschläge sind immer zur Prüfung markiert.
- **Die KI ist nicht deterministisch:** Trotz abgeschalteter Zufälligkeit gab sie beim EBICS-Server einmal „keiner“ und einmal „equensWorldline“ zurück. Deshalb läuft die Messung mehrfach, und KI-Vorschläge werden nie ungeprüft übernommen.
- **Ehrlich zur Messung:** Die Regeln sind entstanden, während die Musterbank schon existierte. Die 91 % sind deshalb eher eine Obergrenze. Der faire Test sind Einträge, die jemand ohne Kenntnis der Datenbank schreibt.
- **Datenschutz bei der KI:** Das gewählte Modell stammt von einem chinesischen Anbieter. Die Anfragen gehen deshalb nur an Rechenzentren, die nichts speichern und nicht trainieren, und enthalten nur Dienstnamen und Zweck, keine personenbezogenen Daten. Für echte Kundendaten wäre ein in der EU betriebenes Modell die konsequente Wahl. Ein Tool für digitale Souveränität sollte seine eigenen Abhängigkeiten kennen.

### Phase 5 abgeschlossen: Bewertung der Musterbank
- **Je Dienst zusammenfassen:** Microsoft 365 steht achtmal im Bestand (O365, Teams, Exchange …). Es zählt einmal, mit der höchsten genannten Kritikalität. Sonst würde ein Anbieter allein durch Mehrfachnennung übergewichtet.
- **Varianten aus dem Bestand erkennen:** „GitHub Enterprise Cloud mit Datenresidenz EU“ wird als die Variante mit Datenresidenz bewertet. Was nicht erkannt wird (etwa „BPaaS“ bei Avaloq), führt zur Standardvariante und einem sichtbaren Hinweis, nicht zu einer stillen Annahme.
- **Kein Ergebnis auf fehlerhaften Daten:** Enthält der Bestand Fehler, verweigert der Endpunkt die Bewertung, statt ein halbes Ergebnis zu liefern.
- **Ehrliche Zwischenbilanz:** Das erste Gesamtbild war technisch richtig, aber für eine Präsentation unbrauchbar. 34 von 47 Diensten standen gesichert auf Stufe 0, fast immer wegen fehlender Angaben. Der Engpass ist nicht die Logik, sondern die Datenlage. Das Ergebnis selbst hat gezeigt, wo die nächste Arbeit liegt.

### Datenrunde für die hoch kritischen Dienste
- **Gezielt statt flächendeckend:** Recherchiert wurden nur die 20 Dienste mit hoher Kritikalität, weil sie das größte Gewicht haben und im Gespräch zuerst angeschaut werden.
- **Ergebnis:** 10 statt 14 dieser Dienste stehen noch gesichert auf Stufe 0. Belegt sind jetzt unter anderem die Datenregionen von Okta, Prisma Access, Splunk und Equinix, die Schlüssel im Eigenbetrieb bei Veeam und die Übermittlungsgrundlagen von GitHub und NICE Actimize.
- **Die Grenze öffentlicher Recherche ist erreicht:** Avaloq, SWIFT, Cisco (Splunk) und weitere sperren automatische Abrufe oder veröffentlichen ihren Datenstandort nicht. Das ist selbst ein Befund: Genau diese Fragen muss eine Bank ihren Anbietern stellen. Das Tool soll sie deshalb als Fragenkatalog ausgeben, statt die Lücke zu verstecken.
- **Werkzeug statt Wegwerfskript:** Das Suchwerkzeug für Fundstellen liegt jetzt im Projekt (`scripts/find_quote.py`) und lädt Seiten genauso wie die Nachprüfung. Eine gefundene Fundstelle besteht damit auch die spätere Kontrolle.

## Phase 6: Roadmap

- **Lücken werden zu Fragen:** Was das Tool nicht weiß, gibt es als Frage an den Anbieter aus. Ein Berater nimmt diese Liste direkt in den Workshop mit. Die Schwäche der Datenlage wird so zu einem Arbeitsergebnis.
- **Kernfragen statt Fragenflut:** Die erste Fassung erzeugte 428 Fragen. Jetzt ist für jeden Anbieter klar, welche Frage die Gesamtstufe tatsächlich bewegt, meist der Datenstandort. Der Rest steht als weitere Fragen dabei.
- **Maßnahmen mit belegter Wirkung:** Jede Maßnahme zeigt, wie sich die gesicherte und die mögliche Stufe ändern. Sinkt die gesicherte Stufe, weil zur Zielvariante Angaben fehlen, steht das dabei. Sonst sähe der Wechsel zur AWS European Sovereign Cloud wie ein Rückschritt aus.
- **Annahmen offen benennen:** Der Aufwand für einen Variantenwechsel (mittel) und für Alternativen ist eingeschätzt, nicht belegt. Das steht in der Methodik.
- **Die Prüfung der Tests fand toten Code:** Die Mutationsprüfung zeigte eine Wellenregel, die nie benutzt wurde, und zwei ungetestete Regeln. Beides ist bereinigt.

### 6.5 EU-Alternativen
- **Nicht jede Lücke braucht eine Alternative:** Für SWIFT, Mastercard, Bloomberg oder ein Kernbankensystem gibt es keinen gleichwertigen europäischen Ersatz. Eine erzwungene Empfehlung wäre unseriös, dort bleibt die Klärung mit dem Anbieter der Hebel.
- **„EU-Anbieter“ heißt nicht „souverän“:** OpenProject läuft bei AWS in Irland, Hawk bei AWS, Matrix42 bietet Hosting auf Azure an. Die Roadmap zeigt deshalb für jeden Wechsel die tatsächliche Wirkung auf die Stufe statt eines pauschalen Versprechens.
- **Ohne Beleg keine Empfehlung:** Bei vier Kandidaten (WithSecure, Logpoint, Brevo, Circula) ließ sich nichts prüfbar belegen. Eine Alternative ohne Belege würde nur eine scheinbare Verbesserung zeigen.
- **Neue Daten können alte Ergebnisse verschlechtern:** Die französische Rechtsform „SAS“ in neuen Firmennamen hat die Zuordnung von „SAS Risk“ unbemerkt zerstört. Die Messung hat es gezeigt, ein neuer Test verhindert die Wiederholung, und ein weiterer Test schützt die Trefferquote auf der Musterbank.

## Phase 7: Oberfläche

- **Farbe nach Aufgabe, nicht nach Geschmack:** Die Stufen sind eine geordnete Größe, also ein Farbton von hell nach dunkel. Ein Rot-Grün-Schema wäre bei Rot-Grün-Schwäche unlesbar. Die Skala wurde mit einem Skript geprüft, nicht nach Augenmaß gewählt, und jede Zelle zeigt zusätzlich die Zahl.
- **Jede Zahl bis zur Quelle verfolgbar:** Ein Klick auf eine Zelle zeigt Kriterien, Begründung und Belege mit Fundstelle. Daran sieht ein Interviewer am schnellsten, dass nichts erfunden ist.
- **Barrierearm gebaut:** Die Heatmap ist eine echte Tabelle mit Zeilen- und Spaltenköpfen, jede Zelle ist per Tastatur erreichbar und für Screenreader beschriftet. Die Detailansicht ist ein nativer Dialog mit Fokusführung und Escape.
- **Ansehen gehört zur Prüfung:** Automatisierte Bildschirmfotos in hell, dunkel und Handyformat haben vier Dinge gezeigt, die kein Test gefunden hätte: gestrichelte Rahmen, die die Heatmap unruhig machten, einen hängenbleibenden Tooltip, eine Fehlermeldung ohne Angabe der fehlerhaften Zeile und ein eigenes Testskript, das sich an einem unsichtbaren Element von Next.js verschluckt hat.
- **Keine Webfonts:** Die Oberfläche nutzt die Systemschrift. Ein Werkzeug für digitale Souveränität sollte keine Schriften von Servern außerhalb der EU laden.

### Zweiter Testsatz für die Zuordnung
- **Gegen Anpassung an die eigenen Testdaten:** Die Musterbank kannte ich beim Anlegen der Schreibweisen, die Quote dort ist geschönt. Deshalb gibt es einen zweiten Testsatz mit 40 Einträgen in der Sprache eines echten IT-Bestands, davon 8 Dienste, die nicht in der Datenbank stehen. Die Lösung wurde committet, bevor die Zuordnung zum ersten Mal lief. Er ist nicht unabhängig im strengen Sinn, weil ich ihn selbst geschrieben habe. Das steht in der Datei.
- **Maßgeblich ist der erste Lauf:** 34 von 40 richtig, 68 % automatisch und richtig, aber **2 stille Fehler**: „1Password Teams“ landete bei Microsoft 365 und „SAP Ariba Einkauf“ bei S/4HANA. Still heißt, ohne Prüfung übernommen. Das ist der gefährlichste Fehler, weil ihn niemand sieht.
- **Vier Ursachen, vier Regeln:** Zwei passende Dienste machen einen Eintrag mehrdeutig, er geht zur Prüfung, statt still entschieden zu werden. Die Schreibweise „SAP“ allein ist entfernt, sie passt auf jedes SAP-Produkt (neue Pflegeregel). Markenwort ist nur das erste Wort eines Namens, nicht „Backup“ aus „Veeam Backup & Replication“. Ein Tippfehler braucht denselben Anfangsbuchstaben, sonst wäre „Suite“ ein Tippfehler von „GSuite“.
- **Ergebnis nach der Korrektur:** In beiden Testsätzen kein stiller Fehler mehr. Ohne KI: Musterbank 52 von 58 automatisch richtig, zweiter Testsatz 27 von 40. Mit KI (drei Durchläufe): 56 von 58 und 38 bis 39 von 40, KI-Vorschläge gehen immer zur Prüfung. Die Zahlen nach der Korrektur sind geschönt, weil ich die Fehler kannte. Ehrlich ist die Zahl des ersten Laufs.
- **Ein Preis wird bewusst bezahlt:** „SAP S/4“ in der Musterbank wird ohne KI nicht mehr automatisch erkannt. Die Schreibweise nachträglich zu ergänzen, wäre genau die Anpassung an die Testdaten, die der zweite Testsatz aufdecken soll. Lieber ein Eintrag mehr in der Prüfliste als ein stiller Fehler.
- **Tests müssen am alten Code scheitern:** Die ersten neuen Tests bestanden auch mit dem fehlerhaften Code, weil er damals einfach den besten Treffer nahm. Sie prüfen jetzt, dass der falsche Dienst die Schwelle gar nicht erst erreicht.

## Phase 4: Fragebogen

- **Reifegrad getrennt von der Souveränität der Anbieter:** 21 der 27 Fragen ergeben einen Reifegrad 0 bis 4 in fünf Handlungsfeldern (Strategie, Anbietersteuerung, Exit, Notfall, Daten und Schlüssel). Sie verändern die SEAL-Stufen nicht. Ein Anbieter wird nicht souveräner, weil die Bank einen Exit-Plan hat, aber ihr Risiko sinkt. Diese Trennung macht beide Aussagen prüfbar.
- **Jede Frage mit Rechtsgrundlage im Wortlaut:** 36 Fundstellen aus DORA, NIS2 und der KMU-Empfehlung, zitiert aus dem amtlichen deutschen Text. Weil EUR-Lex automatische Abrufe sperrt, kommen die Texte vom Cellar-Dienst des Amts für Veröffentlichungen der EU, also aus derselben amtlichen Quelle. Das Prüfskript findet alle 36 Fundstellen wörtlich wieder.
- **Ehrlich, wo es keine Pflicht gibt:** Fragen wie Souveränitätsziele, Risikotoleranz und Zielstufe haben keine Rechtsgrundlage und stehen deshalb ohne. Sie gehören zur Methodik, nicht zum Gesetz.
- **„Weiß nicht“ zählt wie „Nein“:** Das ist dieselbe Regel wie bei den Anbieterdaten, wo eine fehlende Angabe als ungünstigster Fall gilt. Wer es nicht weiß, kann es im Ernstfall auch nicht nutzen.
- **Die Branche bestimmt das Recht:** Kreditinstitute stehen in Anhang I der NIS2, DORA geht ihr aber als Spezialgesetz vor (Art. 4 NIS2). Für NIS2 entscheidet zusätzlich die Größe nach der KMU-Empfehlung. Deshalb fragt das Profil Beschäftigte, Umsatz und Bilanzsumme ab.
- **Das strenge Schema hat sich sofort bezahlt gemacht:** Antworttexte mit Komma zerfielen in der YAML-Kurzschreibweise unbemerkt in mehrere Felder. Weil unbekannte Felder abgelehnt werden, fiel das beim ersten Testlauf auf statt erst in der Oberfläche.

### 4.2 Antworten speichern
- **Fragen als Datei, Antworten in der Datenbank:** Der Fragebogen ändert sich nur mit einer neuen Fassung des Tools und wird wie Code versioniert und geprüft. Jedes Assessment merkt sich die Fassung, mit der es angelegt wurde.
- **Typisiert speichern:** Auswahlantwort und Zahl stehen in getrennten Spalten, eine Datenbankregel erzwingt genau einen Wert. Ein freies Textfeld hätte „180“ und „180,0“ als verschiedene Antworten zugelassen.
- **Alles oder nichts:** Ist eine Antwort ungültig, wird nichts gespeichert, und alle Fehler kommen auf einmal zurück. Das ist dieselbe Regel wie beim Import des IT-Bestands.
- **Mittelwert statt Minimum beim Reifegrad:** Bei einem Dienst entscheidet das schwächste Glied, beim Reifegrad eines Unternehmens nicht. Eine fehlende Schulung der Geschäftsleitung soll das ganze Handlungsfeld nicht auf 0 setzen.
- **Tests finden auch eigene Fehler:** Pythons `round` rundet 0,25 auf 0,2, weil es zur geraden Zahl rundet. Ein Berater erwartet 0,3, deshalb rundet das Tool jetzt kaufmännisch. Ein gezielt gesuchtes Beispiel zeigt außerdem, dass der Gesamtwert aus ungerundeten Werten gebildet werden muss (0,1 statt 0,2). Nebenbei fiel auf, dass der Textvergleich bei leerem Anbieterkatalog abstürzte, und dass ich die Fragen im letzten Schritt falsch gezählt hatte (27 statt 26).

### 4.3 und 5.4 DORA und NIS2
- **Welches Recht gilt, folgt aus drei Angaben:** Sektor, Beschäftigte und Finanzzahlen. Kreditinstitute fallen unter beide Gesetze, DORA geht aber vor. Das steht ausdrücklich in Art. 1 Abs. 2 DORA, den ich im amtlichen Text gefunden habe, und in Art. 4 NIS2.
- **Nicht raten:** Fehlt eine Angabe, sagt das Tool „nicht bestimmbar“. Die Logik arbeitet mit drei Werten (ja, nein, unbekannt). Eine Bank mit 400 Beschäftigten ist auch ohne Finanzzahlen sicher groß, bei 180 Beschäftigten hängt es vom Umsatz ab.
- **Überraschung aus der KMU-Definition:** Eine Bank mit 180 Beschäftigten, 40 Mio. EUR Umsatz und 2,5 Mrd. EUR Bilanzsumme ist ein KMU, weil einer der beiden Finanzwerte reicht. Nach NIS2 wäre sie nur eine wichtige Einrichtung. So steht es in der Empfehlung, und das Tool zeigt die Fundstelle dazu.
- **Hinweise aus dem Bestand sind konkret:** Bei der Musterbank haben 23 von 25 Diensten für kritische Funktionen keinen Exit-Plan (Art. 28 Abs. 8 DORA), 12 sind schwer ersetzbar, und GitHub und Azure gehören zum selben Konzern (Konzentrationsrisiko, Art. 29 DORA). Gemessen wird an der obersten Konzernmutter, nicht am Vertragspartner.
- **Grenzen offen benannt:** keine Aussagen zum deutschen Umsetzungsgesetz, weil sie sich nicht amtlich belegen lassen. Die Hinweise sind eine Vorprüfung, keine Rechtsberatung.
- **Tests, die an Grenzen prüfen:** Eine eigens geschriebene Mutationsprüfung hat die Schwellenwerte (250, 50, 43, 10, 2) und Vergleiche gezielt verändert. Vier Veränderungen blieben zunächst unbemerkt, etwa ein Umsatz von genau 50 Mio. EUR. Jetzt bemerken die Tests 23 von 24. Die verbleibende Veränderung ist gleichwertig und ändert das Verhalten nicht.

### 4.4 IT-Bestand am Assessment
- **Ein Assessment liefert jetzt alles auf einmal:** Heatmap, Roadmap, Reifegrad, Rechtslage und DORA-Hinweise. Die Hinweise aus dem Bestand gelten, wenn der Fragebogen DORA ergibt, und verschwinden, wenn DORA nicht gilt.
- **Originaldatei statt gelesener Werte:** Der Importer bleibt die einzige Stelle, die Dateien liest, und das Original ist als Nachweis da. Das ist im Beratungsalltag wichtig, wenn ein Kunde fragt, worauf ein Ergebnis beruht.
- **Zuordnung speichern, Bewertung neu berechnen:** Das Hochladen der Musterbank dauerte mit KI 25 Sekunden, fast nur wegen der KI-Anfragen. Würde jeder Abruf neu zuordnen, wäre das langsam, teuer und nicht reproduzierbar. Die Bewertung dagegen wird bei jedem Abruf mit dem aktuellen Stand der Anbieterdatenbank berechnet, damit neue Recherchen sofort wirken. Ein Test zählt die KI-Aufrufe und belegt, dass beim Abruf keiner mehr stattfindet.
- **Robust gegen veraltete Daten:** Verschwindet ein Dienst aus der Datenbank, wird seine Zeile als offen gemeldet, statt dass die Bewertung abbricht.

### 7.2 Fragebogen in der Oberfläche
- **Jedes Assessment hat eine eigene Adresse** (`/assessments/7`). Man kann sie als Lesezeichen speichern und später weitermachen, ohne Login und ohne Liste.
- **Speichern ohne Knopf:** Auswahlantworten werden sofort gespeichert, Zahlen beim Verlassen des Felds. Die Speichervorgänge laufen nacheinander in einer Warteschlange. Sonst könnten fünf schnelle Klicks auf dieselbe Frage den Server in falscher Reihenfolge erreichen, und eine ältere Antwort bliebe gespeichert. Der Browsertest klickt genau das und prüft danach den Stand auf dem Server.
- **Rechtsgrundlage zum Aufklappen:** Unter jeder Pflichtfrage steht der Artikel, aufgeklappt mit dem Wortlaut und einem Link zum amtlichen Text. Ein Prüfer sieht so, warum eine Frage gestellt wird.
- **Der Browsertest fand einen stillen Fehler:** „1.500“ Beschäftigte wurde als 1,5 gespeichert, weil der Punkt als Dezimalzeichen galt. Jetzt ist nur das Komma Dezimalzeichen, ein Punkt wird mit Erklärung abgelehnt. Ohne einen Test, der wie ein Mensch tippt, wäre das nicht aufgefallen.
- **Next.js 16 mit Cache Components:** Der Pfadparameter muss hinter einer Suspense-Grenze gelesen werden, sonst meldet Next.js einen Fehler beim Vorrendern. Die Lösung ist eine statische Hülle mit Ladeanzeige, der Inhalt folgt je Aufruf. Gefunden über die Konsole im Browsertest.

### 7.2 Ablauf im Browser geschlossen
- **Drei Schritte, ein Ergebnis:** Fragebogen, IT-Bestand, Ergebnis. Auf der Ergebnisseite stehen Rechtslage und Reifegrad zwischen den Kennzahlen und der Heatmap, weil ein Entscheider zuerst wissen will, welches Recht gilt und wo das Unternehmen steht.
- **Reifegrad als Spanne:** Ein Balken zeigt den gesicherten Wert, eine hellere Verlängerung den möglichen. Die Zahlen stehen immer als Text daneben, nichts hängt allein an der Farbe.
- **Offene Pflichten an einer Stelle:** Lücken aus dem Fragebogen und DORA-Hinweise aus dem Bestand stehen zusammen, jeweils mit Fundstelle zum Aufklappen. Bei der Musterbank sind es 5.
- **Kompletter Durchlauf als Test:** Ein Browsertest legt ein Assessment an, beantwortet Fragen, lädt den Bestand der Musterbank hoch (17 Sekunden mit KI) und prüft Ergebnis, Neuladen, dunkle Ansicht und Handy. Damit ist die Bedingung für den Abschluss von Phase 7 erfüllt.

### 7.6 Startseite
- **Referenz als Muster, nicht als Vorlage:** scan.meetergo.com gliedert in Frage mit Eingabe, Ablauf, Zahlen, Dringlichkeit, häufige Fragen und einen zweiten Aufruf am Ende. Diese Gliederung habe ich übernommen, nicht aber Texte, Farben und die Verkaufssprache mit Verlustangst. Für eine Zielgruppe aus Banken und Beratung wirkt Seriosität stärker.
- **Nur Belegtes auf der Startseite:** Die Vorschau oben zeigt echte Werte aus der Bewertung der Musterbank, die Zahlen sind aus den Daten gezählt, und die Daten zu DORA und NIS2 stehen mit Fundstelle da (Art. 64 DORA, Art. 41 NIS2), ebenfalls vom Prüfskript bestätigt. Eine Annahme über meetergo („prüft auch Mailserver“) habe ich vor dem Commit gestrichen, weil ich sie nicht belegen konnte.
- **Positionierung für Capgemini:** Das Werkzeug ist ein Einstieg vor einem mehrwöchigen Assessment mit Workshops, kein Ersatz dafür. Beratung und Werkzeug ergänzen sich, wie Außenscan und Innenansicht.
- **Eigenes Bildzeichen:** vier Felder der Stufenskala statt EU-Sterne oder Schild, die fast jedes Souveränitätsprodukt nutzt.

## Phase 3: Außenscan

- **Ergänzen statt nachbauen:** meetergo prüft von außen. Wir nutzen den Blick von außen als Starthilfe für die Bewertung von innen. Der Außenscan füllt die Dienstliste vor, die eigentliche Bewertung bleibt beim IT-Bestand.
- **Auch Erkennungsmerkmale brauchen Belege:** Dass ein Mailserver auf Microsoft 365 hinweist, ist eine Behauptung. Sie steht mit Fundstelle aus der Dokumentation von Microsoft in `data/detection.yaml` und wird nachgeprüft. Für Mailchimp, Atlassian, Zoom und Amazon SES fand sich keine eindeutige Fundstelle, also fehlen sie, statt geraten zu werden.
- **Nutzung und Hinweis unterscheiden:** Laufen die E-Mails über Exchange Online, wird Microsoft 365 genutzt. Liegt nur die Website bei Amazon, ist das ein Hinweis, mehr nicht.
- **Sicherheit von Anfang an:** Wer eine Domain eingeben kann, könnte versuchen, über das Tool interne Systeme abzufragen (Server-Side Request Forgery). Deshalb werden nur öffentliche Domains angenommen, und nur öffentliche IP-Adressen gehen weiter. Tests decken `localhost`, private Netze und die Metadatenadresse von Cloud-Servern ab.
- **Ehrlich an echten Domains:** Bei dkb.de erkennt der Scan Microsoft 365 und die Website bei AWS. Bei capgemini.com greift kein Merkmal, die Funde stehen roh da. Das ist richtig so: lieber wenige, belastbare Zuordnungen als viele geratene.

### 3.3 Website laden und meetergo im Vergleich
- **Erst die Konkurrenz verstehen:** Ein automatisierter Durchlauf und ein Video von Jonas haben gezeigt, woher meetergo seine 20 Funde zu capgemini.com hat: zum größten Teil aus den Skripten der Website, dazu aus den Absendern im SPF-Eintrag und deren Netzbetreiber. Diese beiden Quellen fehlten uns.
- **Den Kniff übernehmen, nicht die Bewertung:** Die Absender im SPF-Eintrag werden über ihren Netzbetreiber erkannt, belegt durch RIPEstat. Bei capgemini.com taucht so Salesforce auf. Die Note A bis E übernehmen wir nicht, weil dort ein Werbe-Pixel so viel zählt wie das Hosting.
- **Präzision vor Menge:** Nur was die Seite wirklich lädt, zählt. Moderne Websites packen bloße Links als Daten in ihre Skripte, sonst stünden dort Apple App Store und LinkedIn als „Dienste“. Solche Hosts zählen nur, wenn sie zu einem bekannten Dienst gehören.
- **Kein Browser auf dem Server:** Statt Playwright reicht das HTML. Ein Browser auf dem Server wäre langsamer und eine größere Angriffsfläche, wenn er fremde Seiten ausführt.
- **Sicherheit mit Tests belegt:** Jede Weiterleitung wird neu geprüft, sodass eine öffentliche Seite nicht auf `intern.bank.de` oder die Metadatenadresse eines Cloud-Servers umleiten kann. Die Tests haben zwei echte Fehler gefunden: Eine IP-Adresse als Hostname wurde nur zufällig abgelehnt, und die Größengrenze kürzte nicht, wenn ein großer Block auf einmal kam.

### Website-Werkzeuge in der Datenbank
- **Sieben Werkzeuge mit belegtem Merkmal:** Google Analytics, Google Tag Manager, Microsoft Clarity, etracker, YouTube, Google Fonts und reCAPTCHA. Jedes Merkmal zitiert die Einbau-Anleitung des Anbieters. Für Meta-Pixel, LinkedIn, Hotjar, die Cookie-Banner, Vimeo und Matomo Cloud ließ sich keine Seite automatisch abrufen. Sie erscheinen roh mit ihrem Host, bis eine Fundstelle vorliegt.
- **Der Pfad entscheidet:** Google Analytics und Tag Manager laden vom selben Host, nur `/gtag/js` und `/gtm.js` unterscheiden sie. Ohne Pfad im Merkmal wären beide verwechselt worden.
- **Ein bewusster Zielkonflikt:** Steht ein erkannter Dienst auf einem Host, erscheinen weitere Pfade dort nicht zusätzlich roh. Sonst stünde neben fast jedem Tag Manager sein `ns.html`-Iframe. Der Preis: Google Maps geht unter, wenn auf `www.google.com` auch reCAPTCHA erkannt wird. Das steht im Code und im Test.
- **Ehrlich bei Lücken:** Personio bindet den Tag Manager nur über `ns.html` ein. Diese Variante steht in keiner abrufbaren Google-Dokumentation, also bleibt der Fund roh, obwohl er fast sicher der Tag Manager ist.
- **Keine Nebenwirkung:** Mehr Dienste im Katalog können die Zuordnung des IT-Bestands stören. Die Messung an beiden Testsätzen ist unverändert, ohne stillen Fehler.
- **capgemini.com jetzt:** Google Tag Manager und YouTube auf der Website, Salesforce über den SPF-Eintrag, Hosting bei Automattic (WordPress VIP).

### 3.6 Unternehmensprofil aus der Website
- **Weniger Fragen für den Nutzer:** Aus dem Impressum und GLEIF kommen Firmenname, Registernummer, LEI und Konzernmutter, aus dem Text der Website Vorschläge für Branche und Größe. Der Nutzer bestätigt statt zu tippen.
- **Die Falle der Registernummer:** Unter „HRB 7727“ finden sich bei GLEIF sechs Firmen, weil jedes Amtsgericht eigene Nummern vergibt. Unter „IONOS SE“ drei Einträge. Erst Name und Nummer zusammen sind eindeutig. Ein naiver Abgleich hätte der ING-DiBa die Bilanz einer Spedition zugeordnet.
- **KI mit Belegpflicht:** Die KI darf nur vorschlagen, was sie wörtlich zitieren kann, und das Tool prüft das Zitat. Eine erfundene Begründung oder eine Zahl, die im Zitat nicht vorkommt, fällt heraus. Das ist die technische Umsetzung der Regel „KI-Aussagen immer mit Fundstelle“.
- **Ergebnisse:** ING-DiBa: BaFin-Aufsicht, LEI, Konzernmutter ING Groep (Niederlande). IONOS: LEI, Konzernmutter United Internet. Personio: LEI, keine Konzernmutter gemeldet. Capgemini: kein deutsches Impressum unter capgemini.com, Branche „Beratung“ vorgeschlagen.
- **Realität des Webs:** Websites antworten nur unter www, verlinken ein „Impressum-Generator“-Produkt oder sperren nach mehreren Abrufen. Jeder dieser Fälle hat jetzt eine Regel und einen Test.

### Näher an meetergo: der ganze SPF-Baum
- **Ein Detail mit großer Wirkung:** Der SPF-Eintrag von capgemini.com verweist auf einen Dienst (OnDMARC), der 50 Adressen freigibt. Wir hatten nur die erste ausgewertet. Jetzt wird der ganze Baum durchlaufen, je Netzblock einmal abgefragt, parallel.
- **Ergebnis capgemini.com:** Salesforce, Amazon SES, Mailgun, Rackspace (wie bei meetergo), dazu ServiceNow, Microsoft Azure, BMC, Mailjet, Equinix und Google Cloud, die meetergo nicht zeigt. Außerdem die erlaubten Zertifizierungsstellen (Let's Encrypt, Sectigo, Certigna) und WordPress mit fünf Plugins.
- **Schneller trotz mehr Abfragen:** Statt 32 jetzt 14 Sekunden, weil die Netzbetreiber parallel abgefragt und bekannte Namen zwischengespeichert werden.
- **Bewusst nur Hinweise:** Ein Absender im SPF-Eintrag zeigt, dass ein Dienst E-Mails im Namen der Domain senden darf. Wofür genau, etwa Newsletter oder Ticketsystem, verrät er nicht.

### Container des Tag Managers
- **Wo die meisten Werkzeuge stecken:** Viele Websites binden Tracking nicht direkt ein, sondern über den Google Tag Manager. Die eigentliche Liste steht in dessen Container, einer Javascript-Datei. Capgemini nutzt vier davon. Genau dort fand meetergo Analytics, Ads, Clarity, 6sense, LinkedIn und Terminus.
- **Kennungen statt Vermutungen:** Google Analytics und Google Ads werden an ihren IDs erkannt (`G-…`, `AW-…`), belegt mit dem Format aus der Google-Dokumentation. Das Muster verlangt eine Ziffer, damit eine Zeichenfolge wie „G-SUITEPRO“ nicht zählt.
- **Hinweis statt Nutzung:** Was im Container steht, ist eingerichtet, wird aber meist erst nach Einwilligung geladen.
- **capgemini.com jetzt:** zehn erkannte Dienste (Google Ads, Analytics, Tag Manager, YouTube, Clarity, Salesforce, ServiceNow, AWS, Azure, Equinix) und roh 6sense, LinkedIn, Terminus, TrustArc und Facebook. Damit sind wir bei den Signalen auf dem Stand von meetergo. Es fehlen nur noch Merkmale in der Datenbank, um die rohen Funde zuzuordnen.
- **Tests, die echte Fehler fanden:** Die Container wurden ausgewertet, bevor die Funde der Seite eingetragen waren, sodass TrustArc doppelt erschien. Und im Container maskierte Anführungszeichen hingen als Backslash am Pfad.

### Quellen für Website-Werkzeuge
- **Hartnäckig suchen, bevor man fragt:** Die meisten Anbieter sperren ihre Hilfeseiten für automatische Abrufe. Über eine Websuche fanden sich trotzdem abrufbare Seiten der Anbieter selbst: eine LinkedIn-Hilfeseite mit `snap.licdn.com`, die SDK-Dokumentation von OneTrust mit `cdn.cookielaw.org` und eine Bibliotheksseite von cdnjs. Drittseiten, die den Code nur wiederholen, zählen nicht als Quelle.
- **cdnjs gehört zu Cloudflare** und wird deshalb dem vorhandenen Dienst zugeordnet, als Hinweis: Eine Bibliothek aus einem öffentlichen CDN zu laden, ist etwas anderes als ein Vertrag mit Cloudflare.
- **Eine Falle im Betrieb:** Der Server hatte die Merkmale beim Start zwischengespeichert und übersah neue Einträge in den YAML-Dateien. Er lädt jetzt auch bei Änderungen an den Daten neu.

### 3.5 Schnellcheck in der Oberfläche
- **Wie bei meetergo: zuerst die Website.** Jonas hat beim Testen seine Website-Adresse in das Namensfeld getippt, die Datenbank zeigte das später fünfmal. Das hat die Entscheidung bestätigt: Oben steht jetzt nur noch das Feld für die Website.
- **Ehrlicher Ladebildschirm:** Die sechs Schritte kommen als Datenstrom vom Server (Server-Sent Events), die Liste der Schritte schickt der Server zu Beginn mit. Angezeigt wird, was gerade wirklich passiert, kein Protokoll zur Show.
- **Übergabe ohne Abtippen:** Die erkannten Dienste werden zum Startbestand, über den normalen Importer. Branche und Beschäftigte sind Vorschläge mit Zitat und werden im Fragebogen mit einem Klick übernommen. Ohne belegbares Zitat gibt es keinen Vorschlag, bei Personio kam deshalb diesmal keiner.
- **Lesbarkeit:** Lange SPF-Einträge zeigen nur den Netzbetreiber, Gruppen mit vielen Funden klappen zu, Aussagekräftiges steht zuerst.

### Vergleich mit dem Bericht von meetergo zu capgemini.com
- **Übernommen:** die Kernaussage zum Rechtsraum („13 von 13 erkannten Diensten unterliegen dem Recht eines Staates außerhalb der EU“), Etiketten der betroffenen Dienste, drei Kennzahlen, eine Score-Karte, die drei größten Hebel, eine Tabelle mit Eigentümer und EU-Alternative je Dienst und die technischen Signale (DNSSEC, Zertifikat, Netzbetreiber, Reverse-DNS, Cookies vor Einwilligung). Bei den Signalen stimmen unsere Werte mit denen von meetergo überein.
- **Mit unserer Methodik statt deren:** Die Score-Karte zeigt die Gesamtstufe 0 bis 4 nach dem EU-Rahmenwerk, gewichtet nach Kritikalität, statt einer Note A bis E. Der Rechtsraum folgt der obersten Konzernmutter. Die Hebel sind wie in der Roadmap berechnet (Kritikalität mal Abstand zur Höchststufe) und nennen nur belegte Alternativen aus der Datenbank, sonst die Klärung mit dem Anbieter.
- **Bewusst weggelassen:** Angst-Abschnitte zu Bußgeld, Haftung und Geopolitik, „Auf meetergo migrieren“ als Empfehlung für alles, das E-Mail-Formular für den Bericht, Teilen in sozialen Netzwerken und die Rangliste. Das sind Vertriebsfunktionen. Ebenso Microsoft Teams aus einem bloßen Verweis im Code.
- **Ergebnis bei capgemini.com:** 18 erkannte Dienste, alle unter US-Recht (meetergo: 15 von 20 Tools). Nur bei uns: ServiceNow, Azure, Equinix, Rackspace und Mailgun aus E-Mail- und Netzinfrastruktur sowie Parse.ly. Es fehlt noch Terminus, weil es dafür keine prüfbare Quelle gibt.
- **Pardot über die Kennung statt über den Host:** Jeder Kunde legt den Host für das Pardot-Skript selbst fest. Erkennbar ist Pardot deshalb an der Konto-Kennung `piAId` im Code, wie in der Anleitung von Salesforce. Bei Capgemini greift die Regel.
- **Menschliche Prüfung als zweiter Weg:** Manche Anbieterseiten sperren automatische Abrufe (Meta, Cookiebot). Jonas hat die Fundstellen dort im Browser geprüft, die Angabe trägt dann den Vermerk `verified_by`. Das Prüfskript zählt sie gesondert, die Oberfläche zeigt den Vermerk beim Beleg.
- **Ein Detail mit Wirkung:** Für den Aussteller des TLS-Zertifikats nutzt das Tool denselben Zertifikatsspeicher wie beim Laden der Seite. Der Standard-Speicher von Python unter macOS kennt die Wurzelzertifikate nicht.

### Wartezeit gemessen statt geraten
- **Die Vermutung war falsch:** Geplant war, Schritte parallel laufen zu lassen. Die Messung zeigte: Scan und Impressum brauchen 3 bis 7 Sekunden, der Vorschlag der KI 4 bis 25. Parallelisieren hätte etwa eine Sekunde gebracht.
- **Ursache:** Das Modell denkt vor der Antwort nach, das sind 95 Prozent der erzeugten Tokens (bis 6.000). Kurzes Nachdenken lässt sich anfragen, aber nicht jeder Anbieter hinter OpenRouter hält sich daran. Ganz ohne Nachdenken antwortet es in einer Sekunde, schwankt aber bei der Branche (Capgemini einmal „Beratung“, einmal „IKT-Dienste“).
- **Lösung:** Das Ergebnis kommt sofort, der Vorschlag wird nachgereicht. Die Firmenkarte zeigt so lange „Die KI liest die Website …“. Tempo und Qualität stehen sich nicht mehr im Weg, egal welcher Anbieter antwortet.
- **Nebenbefund:** Die Frist von 60 Sekunden griff nicht, weil sie bei httpx nur zwischen zwei Datenpaketen gilt und OpenRouter beim Nachdenken Lebenszeichen schickt. Jetzt gibt es eine Gesamtfrist von 45 Sekunden.

### Belegstufen statt Alles-oder-nichts
- **Anlass:** Jonas hatte das Gefühl, wir seien zu streng. Für jedes Website-Werkzeug ein Zitat aus der Herstellerdoku zu suchen, kostete eine Stunde Bildschirmfotos für fünf Dienste und skaliert nicht auf 150 Dienste.
- **Abwägung:** Bei der Aussage „Host X gehört zu Anbieter Y“ ist das Risiko klein. Bei Mutterkonzern, Rechtsraum und Datenstandort ist es groß, denn dort entsteht die Bewertung. Strenge Belege bleiben also dort, bei der Erkennung gibt es Stufen.
- **Auswahl der Liste:** DuckDuckGo, Ghostery und Disconnect würden sogar den Mutterkonzern liefern, ihre Lizenz (CC BY-NC-SA) schließt aber kommerzielle Nutzung aus. Gewählt: enthec/webappanalyzer unter GPL-3.0, als eigene Datei mit Lizenz und festem Versionsstand. Die GPL greift erst bei Weitergabe der Software, nicht beim Betrieb als Webdienst.
- **Warum Signaturen nicht bewertet werden:** Hotjar gehört zu Contentsquare aus Frankreich. Der Name allein sagt nichts über den Rechtsraum. Deshalb zeigt das Tool solche Funde als „Erkannt, noch ohne Bewertung“.
- **GLEIF-Detail:** Siemens ist in Berlin und München eingetragen, GLEIF führt nur München. Das Tool prüft jetzt alle Registernummern des Impressums, ein Treffer gilt weiterhin nur, wenn Name und Nummer passen.


### Archiv als zweiter Weg, Mensch als dritter
- **Frage von Jonas:** Ist es nicht widersinnig, in einem automatisierten Tool Belege von Hand zu prüfen? Antwort: Für die reine Erkennung ja, dafür gibt es die Signaturliste. Für Angaben, die die Bewertung tragen, ist ein Mensch der letzte Ausweg, nicht der erste.
- **Reihenfolge im Prüfskript:** Quelle selbst, dann die jüngste Kopie im Internet Archive, dann der Vermerk eines Menschen. Bot-Sperren werden nicht umgangen. Das Archiv ist eine eigene Quelle mit Datum und damit sogar besser nachvollziehbar als eine lebende Seite.
- **Ergebnis:** Drei von acht Handprüfungen bestätigt das Archiv jetzt automatisch (Adobe, Cookiebot, Usercentrics alt).
- **Nebenfund, der den Wert zeigt:** Google hat seine Seite zu Netto-Null umgebaut, die Fundstelle zu erneuerbarer Energie war weg. Statt die alte Fundstelle aus dem Archiv weiterzuverwenden, stützt sich die Angabe jetzt auf den Umweltbericht 2026, denn sie muss heute noch stimmen. Die Aussage gilt weiter: 100 Prozent bilanziell auf das Jahr gerechnet, im neunten Jahr in Folge.
- **Ein Fehler, den die Tests zuerst übersahen:** Der Aufruf beim Archiv war wegen eines doppelt belegten Parameternamens kaputt, die Tests hatten ihn durch eine Attrappe ersetzt. Jetzt gibt es einen Test für den Aufruf selbst, und Störungen des Archivs stehen in der Ausgabe, statt still zu verschwinden.

### PDF-Bericht
- **Technik:** Eine eigene Berichtsseite mit Druck-CSS statt einer PDF-Bibliothek in Python. Heatmap und Roadmap gibt es schon als Komponenten, der Server braucht keine zusätzlichen Programme. Ein serverseitiges PDF ließe sich später mit einem Browser auf dem Server von genau dieser Seite drucken.
- **Management Summary aus festen Regeln, nicht aus einer KI:** Jeder Satz geht auf eine Zahl der Bewertung zurück und ist bei gleichen Daten gleich. Das passt zu „Belege statt Behauptungen“.
- **Die wichtigste fachliche Idee: strukturell oder Klärung.** Bei der Musterbank bleiben 19 kritische Dienste selbst im besten Fall bei Stufe 1, alle wegen eines Mutterkonzerns in den USA. Hier hilft nur ein Wechsel. Bei 14 weiteren fehlen nur Angaben, eine Nachfrage beim Anbieter kann die Stufe heben. Die zwei Gruppen verlangen unterschiedliche Maßnahmen und bestimmen die Wellen der Roadmap.
- **Fragenkatalog kompakt:** 409 Fragen an 44 Anbieter wären unlesbar. Weil es je Thema nur einen Fragetext gibt, steht jede Frage einmal, darunter eine Tabelle, wer welche Fragen bekommt (Kernfrage oder weitere Frage).
- **Fehlersuche:** Die Druckregeln für Fußzeile und Seitenzahl kamen zunächst nicht an. Turbopack verwirft die Randfelder von `@page` beim Übersetzen still und liefert die alte CSS aus. Gefunden durch schrittweises Ausschließen: Datei selbst übersetzt, Tailwind und lightningcss einzeln geprüft, Block testweise entfernt. Lösung: Die Seitenregeln stehen in einem `<style>`-Element der Berichtsseite.

