# Oberfläche

Next.js 16 mit TypeScript und Tailwind CSS. Die Oberfläche ruft die API im Ordner `backend/` auf und speichert selbst nichts.

## Starten

Voraussetzung: Datenbank und Backend laufen.

```
# im Projektordner
docker compose up -d

# im Ordner backend/
uv run uvicorn app.main:app --port 8000

# im Ordner frontend/
npm install
npm run dev
```

Dann im Browser http://localhost:3000 öffnen und „Musterbank bewerten“ wählen.

Läuft die API unter einer anderen Adresse, wird sie über `NEXT_PUBLIC_API_URL` gesetzt. Das Backend lässt Browser-Anfragen nur von der Adresse in `FRONTEND_ORIGIN` zu (Voreinstellung http://localhost:3000).

## Aufbau

| Datei | Inhalt |
|---|---|
| `src/components/AssessmentApp.tsx` | Ablauf: Start, Laden, Fehler, Ergebnis |
| `src/components/Heatmap.tsx` | Dienste mal Zielbereiche, als echte Tabelle für Screenreader |
| `src/components/ServiceDetail.tsx` | Kriterien, Begründungen und Belege je Dienst |
| `src/components/Roadmap.tsx` | Drei Wellen und Wirkung der Maßnahmen |
| `src/components/QuestionCatalog.tsx` | Fragen an die Anbieter, Kernfragen zuerst |
| `src/lib/types.ts` | Typen der API-Antwort |

## Gestaltung

- Die Stufen 0 bis 4 sind ein Farbton von hell nach dunkel. Die Skala ist für den hellen und den dunklen Modus mit dem Validierungsskript des Datenvisualisierungs-Skills geprüft. Ein Ampelschema aus Rot und Grün wäre bei Rot-Grün-Schwäche nicht lesbar.
- Jede Zelle zeigt die Zahl, die Farbe trägt nie allein. Ist eine höhere Stufe möglich, steht sie klein daneben („↗3“).
- Systemschrift statt Webfonts: Ein Werkzeug für digitale Souveränität lädt keine Schriften von Servern außerhalb der EU.

## Bekannte Punkte

- `npm audit` meldet Lücken in Entwicklungswerkzeugen (Paket `braces`). Die ausgelieferten Pakete sind laut `npm audit --omit=dev` frei von bekannten Lücken.
