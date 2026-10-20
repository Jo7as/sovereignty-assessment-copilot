import { CRITICALITY, EFFORT } from "@/lib/labels";
import type { Assessment, Measure } from "@/lib/types";

function change(measure: Measure) {
  const show = (level: number, potential: number) => (level === potential ? `${level}` : `${level} (möglich ${potential})`);
  return `Stufe ${show(measure.level_before, measure.potential_before)} → ${show(measure.level_after, measure.potential_after)}`;
}

export default function Roadmap({ roadmap }: { roadmap: Assessment["roadmap"] }) {
  return (
    <section aria-labelledby="roadmap-title">
      <h2 id="roadmap-title" className="text-xl font-semibold tracking-tight">Roadmap in drei Wellen</h2>
      <p className="text-sm text-ink-secondary">
        Priorität ist Kritikalität mal Abstand zur Höchststufe. Klärungen kommen zuerst, Migrationen mit hohem Aufwand zuletzt.
      </p>

      <ol className="mt-4 grid gap-6 lg:grid-cols-3">
        {roadmap.waves.map((wave) => (
          <li key={wave.wave} className="border-t-2 border-accent pt-3">
            <h3 className="font-medium">Welle {wave.wave}: {wave.title}</h3>
            <p className="text-xs text-ink-muted">{wave.items.length} Punkte</p>
            <ul className="mt-3 space-y-2 text-sm">
              {wave.items.slice(0, 8).map((item) => (
                <li key={item.title} className="flex gap-3">
                  <span className="tabular w-8 shrink-0 text-right text-xs text-ink-muted" title="Priorität">{item.priority}</span>
                  <span>
                    {item.title}
                    <span className="block text-xs text-ink-muted">
                      Kritikalität {CRITICALITY[item.criticality]}
                      {item.effort ? ` · ${EFFORT[item.effort]}` : ""}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
            {wave.items.length > 8 && (
              <p className="mt-2 text-xs text-ink-muted">und {wave.items.length - 8} weitere</p>
            )}
          </li>
        ))}
      </ol>

      {roadmap.measures.length > 0 && (
        <div className="mt-8 overflow-x-auto rounded-lg border border-hairline bg-surface">
          <table className="w-full min-w-[40rem] text-sm">
            <caption className="px-3 py-2 text-left font-medium">Wirkung der Maßnahmen</caption>
            <thead>
              <tr className="border-y border-hairline text-left text-xs text-ink-muted">
                <th scope="col" className="px-3 py-2 font-medium">Dienst</th>
                <th scope="col" className="px-3 py-2 font-medium">Maßnahme</th>
                <th scope="col" className="px-3 py-2 font-medium">Wirkung</th>
                <th scope="col" className="px-3 py-2 font-medium">Aufwand</th>
              </tr>
            </thead>
            <tbody>
              {roadmap.measures.map((measure) => (
                <tr key={`${measure.service}-${measure.target}`} className="border-t border-hairline align-top">
                  <td className="px-3 py-2">{measure.service}</td>
                  <td className="px-3 py-2">
                    {measure.kind === "VARIANTE" ? "Variante: " : "Wechsel zu "}
                    {measure.target}
                    {measure.note && <span className="block text-xs text-ink-muted">{measure.note}</span>}
                  </td>
                  <td className="tabular px-3 py-2">{change(measure)}</td>
                  <td className="px-3 py-2">{EFFORT[measure.effort]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
