import { CRITICALITY } from "@/lib/labels";
import type { Report, ReportRisk } from "@/lib/types";

import LevelCell from "../LevelCell";
import { JURISDICTION } from "../quickcheck/records";
import { Sheet, SheetTitle } from "./Sheet";

// Management Summary auf einer Seite: Kernaussage, Kennzahlen, Rechtslage, Risiken, Maßnahmen
export default function Summary({ report }: { report: Report }) {
  return (
    <Sheet label="Management Summary">
      <SheetTitle eyebrow="1 · Auf einen Blick">Management Summary</SheetTitle>

      <p className="text-lg font-semibold leading-snug tracking-tight text-balance">{report.headline}</p>

      <ul className="mt-3 space-y-1">
        {report.key_figures.map((figure) => (
          <li key={figure} className="border-l-2 border-accent pl-3">
            {figure}
          </li>
        ))}
      </ul>

      <h3 className="mt-5 text-sm font-semibold">Rechtslage</h3>
      <p className="mt-1">{report.regulation}</p>

      {report.top_risks.length > 0 && (
        <>
          <h3 className="mt-5 text-sm font-semibold">Die {report.top_risks.length} größten Risiken</h3>
          <ol className="mt-2 space-y-2">
            {report.top_risks.map((risk, index) => (
              <Risk key={risk.service} risk={risk} rank={index + 1} />
            ))}
          </ol>
        </>
      )}

      {report.actions.length > 0 && (
        <>
          <h3 className="mt-5 text-sm font-semibold">Was jetzt zu tun ist</h3>
          <ol className="mt-2 grid break-inside-avoid grid-cols-3 gap-3">
            {report.actions.map((action) => (
              <li key={action.wave} className="break-inside-avoid border-t-2 border-accent pt-2">
                <p className="font-medium">Welle {action.wave}</p>
                <p className="text-[11px] text-ink-muted">
                  {action.title} · {action.count} {action.count === 1 ? "Punkt" : "Punkte"}
                </p>
                <p className="mt-1">Zuerst: {action.first}</p>
              </li>
            ))}
          </ol>
        </>
      )}
    </Sheet>
  );
}

function Risk({ risk, rank }: { risk: ReportRisk; rank: number }) {
  const jurisdiction = risk.jurisdiction ? JURISDICTION[risk.jurisdiction] ?? risk.jurisdiction : null;
  return (
    <li className="grid grid-cols-[1.5rem_1fr_3rem] gap-3 break-inside-avoid rounded-md border border-hairline px-3 py-2 leading-snug">
      <span className="tabular text-ink-muted">{rank}</span>
      <div>
        <p className="font-semibold">{risk.name}</p>
        <p className="text-[11px] text-ink-muted">
          {risk.provider}
          {jurisdiction && ` · ${jurisdiction}`} · Kritikalität {CRITICALITY[risk.criticality]}
        </p>
        {risk.cap && <p className="mt-1">{risk.cap}</p>}
        {risk.reasons.length > 0 && (
          <p className="mt-0.5 text-ink-secondary">
            {risk.cap ? "Heute zusätzlich: " : "Heute: "}
            {risk.reasons.join(" ")}
          </p>
        )}
        {risk.open_facts.length > 0 && (
          <p className="mt-0.5 text-[11px] text-ink-muted">Offen beim Anbieter: {risk.open_facts.join(", ")}</p>
        )}
      </div>
      <span className="self-start">
        <LevelCell level={risk.level} potential={risk.potential} />
      </span>
    </li>
  );
}
