import { CRITICALITY, EFFORT } from "@/lib/labels";
import type { Assessment, Measure } from "@/lib/types";

import { Sheet, SheetTitle } from "./Sheet";

const SHOWN = 8; // Punkte je Welle im Bericht, der Rest steht in der Anwendung

// Kurzform wie in der Heatmap: „0 ↗2“ heißt gesichert 0, möglich 2
const level = (secured: number, possible: number) => (possible > secured ? `${secured} ↗${possible}` : `${secured}`);
const EFFORT_SHORT: Record<Measure["effort"], string> = { GERING: "gering", MITTEL: "mittel", HOCH: "hoch" };

function measureText(measure: Measure) {
  return measure.kind === "VARIANTE" ? `Variante: ${measure.target}` : `Wechsel zu ${measure.target}`;
}

// Roadmap in drei Wellen und die Wirkung der Maßnahmen auf die Stufe
export default function RoadmapPage({ roadmap }: { roadmap: Assessment["roadmap"] }) {
  return (
    <Sheet label="Roadmap">
      <SheetTitle eyebrow="5 · Roadmap">Roadmap in drei Wellen</SheetTitle>
      <p className="text-ink-secondary">
        Priorität ist Kritikalität mal Abstand zur Höchststufe. Klärungen kommen zuerst, Migrationen mit hohem Aufwand
        zuletzt.
      </p>

      <div className="mt-4 grid grid-cols-3 gap-4">
        {roadmap.waves.map((wave) => (
          <section key={wave.wave} className="break-inside-avoid border-t-2 border-accent pt-2">
            <h3 className="font-semibold">Welle {wave.wave}</h3>
            <p className="text-[10px] text-ink-muted">
              {wave.title} · {wave.items.length} {wave.items.length === 1 ? "Punkt" : "Punkte"}
            </p>
            <ol className="mt-2 space-y-1.5 text-[11px] leading-snug">
              {wave.items.slice(0, SHOWN).map((item) => (
                <li key={item.title}>
                  {item.title}
                  <span className="block text-[9px] text-ink-muted">
                    Kritikalität {CRITICALITY[item.criticality]}
                    {item.effort && ` · ${EFFORT[item.effort]}`}
                  </span>
                </li>
              ))}
            </ol>
            {wave.items.length > SHOWN && (
              <p className="mt-1.5 text-[10px] text-ink-muted">und {wave.items.length - SHOWN} weitere</p>
            )}
          </section>
        ))}
      </div>

      {roadmap.measures.length > 0 && (
        <>
          <h3 className="mt-6 text-sm font-semibold break-after-avoid">Wirkung der Maßnahmen</h3>
          <table className="mt-2 w-full border-collapse text-[11px]">
            <thead>
              <tr className="text-left text-[10px] text-ink-muted">
                <th className="pb-1 font-normal">Dienst</th>
                <th className="pb-1 font-normal">Maßnahme</th>
                <th className="pb-1 font-normal">Stufe vorher → nachher</th>
                <th className="pb-1 font-normal">Aufwand</th>
              </tr>
            </thead>
            <tbody>
              {roadmap.measures.map((measure) => (
                <tr key={`${measure.service}-${measure.target}`} className="break-inside-avoid border-t border-hairline align-top">
                  <td className="w-[36mm] py-1.5 pr-2 font-medium">{measure.service}</td>
                  <td className="py-1.5 pr-2 leading-snug">
                    {measureText(measure)}
                    {measure.note && <span className="block text-[9px] text-ink-muted">{measure.note}</span>}
                  </td>
                  <td className="tabular w-[34mm] whitespace-nowrap py-1.5 pr-2">
                    {level(measure.level_before, measure.potential_before)} → {level(measure.level_after, measure.potential_after)}
                  </td>
                  <td className="w-[16mm] py-1.5">{EFFORT_SHORT[measure.effort]}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-[10px] text-ink-muted">
            „0 ↗2“ heißt gesichert Stufe 0, möglich Stufe 2. Sinkt die gesicherte Stufe nach einem Wechsel, fehlen Angaben zur Zielvariante. Bis zur Klärung zählen sie wie
            der ungünstigste Fall.
          </p>
        </>
      )}
    </Sheet>
  );
}
