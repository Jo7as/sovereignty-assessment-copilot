import type { ReportResponse } from "@/lib/types";

import Logo from "../Logo";
import { Sheet } from "./Sheet";

const date = (iso: string) =>
  new Date(iso).toLocaleDateString("de-DE", { day: "numeric", month: "long", year: "numeric" });

const BASIS = [
  "EU Cloud Sovereignty Framework, Version 1.2.1 (Oktober 2025)",
  "DORA, Verordnung (EU) 2022/2554",
  "NIS2, Richtlinie (EU) 2022/2555",
];

// Deckblatt: wer, wann, auf welcher Grundlage
export default function Cover({ data }: { data: ReportResponse }) {
  const { assessment, report } = data;
  const inventory = assessment.inventory.inventory;
  const rows: [string, string][] = [
    ["Bericht erstellt", date(new Date().toISOString())],
    ["Datenstand der Bewertung", date(inventory.assessed_on)],
    ["IT-Bestand", `${inventory.entries} Einträge, ${report.assessed} Dienste bewertet`],
  ];

  return (
    <Sheet label="Deckblatt">
      <div className="flex min-h-[250mm] flex-col print:min-h-[262mm]">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Logo className="h-6 w-6" />
          Sovereignty Assessment Copilot
        </div>

        <div className="mt-[60mm]">
          <p className="text-sm font-medium uppercase tracking-wide text-accent">Digital Sovereignty Assessment</p>
          <h1 className="mt-3 text-5xl font-semibold tracking-tight">{assessment.name}</h1>
          {assessment.domain && <p className="mt-2 font-mono text-base text-ink-secondary">{assessment.domain}</p>}
          <p className="mt-6 max-w-[140mm] text-lg text-ink-secondary">
            Abhängigkeit von IT-Anbietern außerhalb der EU, Rechtslage nach DORA und NIS2 und Roadmap in drei Wellen.
          </p>
        </div>

        <dl className="mt-12 grid max-w-[150mm] grid-cols-[55mm_1fr] gap-x-4 gap-y-2 border-t border-hairline pt-4">
          {rows.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-ink-muted">{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
          <dt className="text-ink-muted">Grundlage</dt>
          <dd>
            <ul>
              {BASIS.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </dd>
        </dl>

        <p className="mt-auto max-w-[150mm] border-l-4 border-accent bg-page px-4 py-3 text-xs text-ink-secondary">
          Automatisch erstellt. Jede Aussage zu einem Anbieter beruht auf einer Fundstelle im Quellenverzeichnis.
          Fehlende Angaben zählen wie der ungünstigste Fall. Die Einordnung zu DORA und NIS2 ist eine Vorprüfung und
          keine Rechtsberatung.
        </p>
      </div>
    </Sheet>
  );
}
