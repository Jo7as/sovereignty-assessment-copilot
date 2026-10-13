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
- **Repository zunächst privat:** Öffentlich erst in Phase 9, wenn README und Demo stehen, damit niemand ein halbfertiges Projekt sieht.
