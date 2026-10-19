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
