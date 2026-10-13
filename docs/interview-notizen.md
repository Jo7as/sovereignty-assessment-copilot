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
