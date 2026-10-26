import { CRITICALITY } from "@/lib/labels";
import type { Report, ReportRisk } from "@/lib/types";

import { levelStyle } from "../LevelCell";
import { JURISDICTION } from "../quickcheck/records";
import { Sheet, SheetTitle } from "./Sheet";

function Level({ risk }: { risk: ReportRisk }) {
  return (
    <span className="tabular inline-flex h-5 min-w-9 items-center justify-center rounded-[2px] px-1 text-[10px]" style={levelStyle(risk.level)}>
      {risk.level}
      {risk.potential > risk.level && <span className="ml-0.5 opacity-80">↗{risk.potential}</span>}
    </span>
  );
}

// Klärungsbedarf als Tabelle: Die letzte Spalte sagt, wonach beim Anbieter zu fragen ist.
function RiskTable({ risks }: { risks: ReportRisk[] }) {
  return (
    <table className="w-full border-collapse text-[11px]">
      <thead>
        <tr className="text-left text-[10px] text-ink-muted">
          <th className="pb-1 font-normal">Dienst</th>
          <th className="pb-1 font-normal">Rechtsraum</th>
          <th className="pb-1 font-normal">Stufe</th>
          <th className="pb-1 font-normal">Offen beim Anbieter</th>
        </tr>
      </thead>
      <tbody>
        {risks.map((risk) => (
          <tr key={risk.service} className="break-inside-avoid border-t border-hairline align-top">
            <td className="w-[44mm] py-1.5 pr-2 leading-tight">
              <span className="block font-medium">{risk.name}</span>
              <span className="block text-[9px] text-ink-muted">Kritikalität {CRITICALITY[risk.criticality]}</span>
            </td>
            <td className="w-[28mm] py-1.5 pr-2">{risk.jurisdiction ? JURISDICTION[risk.jurisdiction] ?? risk.jurisdiction : "–"}</td>
            <td className="w-[14mm] py-1.5 pr-2">
              <Level risk={risk} />
            </td>
            <td className="py-1.5 leading-snug">{risk.open_facts.join(", ") || "–"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// Meist begrenzt derselbe Grund viele Dienste, etwa der Sitz der Konzernmutter in den USA.
// Der Grund steht deshalb einmal als Überschrift, darunter die betroffenen Dienste.
function byCapReason(risks: ReportRisk[]): [string, ReportRisk[]][] {
  const groups = new Map<string, ReportRisk[]>();
  for (const risk of risks) {
    const reason = risk.cap_reason ?? "Ohne genannten Grund";
    groups.set(reason, [...(groups.get(reason) ?? []), risk]);
  }
  return [...groups.entries()];
}

function StructuralGroups({ risks }: { risks: ReportRisk[] }) {
  return (
    <div className="space-y-3">
      {byCapReason(risks).map(([reason, items]) => (
        <div key={reason} className="break-inside-avoid">
          <p className="font-medium">
            Begrenzt durch: {reason} <span className="font-normal text-ink-muted">({items.length})</span>
          </p>
          <ul className="mt-1.5 grid grid-cols-2 gap-x-6 gap-y-1 text-[11px]">
            {items.map((risk) => (
              <li key={risk.service} className="flex items-center justify-between gap-2 border-t border-hairline pt-1">
                <span>
                  {risk.name}
                  <span className="text-[9px] text-ink-muted">
                    {" "}
                    · {CRITICALITY[risk.criticality]}
                    {risk.jurisdiction && ` · ${JURISDICTION[risk.jurisdiction] ?? risk.jurisdiction}`}
                  </span>
                </span>
                <Level risk={risk} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export default function RisksPage({ report }: { report: Report }) {
  const { structural, clarify } = report.risk_groups;
  return (
    <Sheet label="Risiken im Detail">
      <SheetTitle eyebrow="3 · Risiken">Risiken im Detail</SheetTitle>
      <p className="text-ink-secondary">
        Alle Dienste mit hoher oder mittlerer Kritikalität, die gesichert auf Stufe 0 oder 1 stehen. Sie fallen in zwei
        Gruppen, die unterschiedliche Maßnahmen verlangen.
      </p>

      <h3 className="mt-5 text-sm font-semibold">Strukturell: Hier hilft nur ein Wechsel ({structural.length})</h3>
      <p className="mb-2 text-[11px] text-ink-secondary">
        Auch wenn der Anbieter alle offenen Fragen günstig beantwortet, bleibt die Stufe bei 1 oder darunter. Verbessern
        lässt sie sich nur mit einer anderen Variante beim selben Anbieter oder einem Wechsel zu einer EU-Alternative.
      </p>
      {structural.length > 0 ? <StructuralGroups risks={structural} /> : <p>Keine.</p>}

      <h3 className="mt-6 text-sm font-semibold break-after-avoid">Klärungsbedarf: Hier reicht eine Nachfrage ({clarify.length})</h3>
      <p className="mb-2 text-[11px] text-ink-secondary break-after-avoid">
        Die Stufe ist niedrig, weil Angaben fehlen. Beantwortet der Anbieter die offenen Punkte günstig, steigt sie bis
        zur möglichen Stufe. Die Fragen dazu stehen im Fragenkatalog im Anhang.
      </p>
      {clarify.length > 0 ? <RiskTable risks={clarify} /> : <p>Keine.</p>}
    </Sheet>
  );
}
