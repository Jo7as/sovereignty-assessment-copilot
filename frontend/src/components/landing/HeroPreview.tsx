import { OBJECTIVES } from "@/lib/labels";
import type { Level } from "@/lib/types";

import { levelStyle } from "../LevelCell";

// Echte Zeilen aus der Bewertung der fiktiven Musterbank AG (Demo, Stand 20.10.2026).
// Reihenfolge der Stufen wie OBJECTIVES.
const ROWS: { name: string; overall: Level; levels: Level[] }[] = [
  { name: "Avaloq", overall: 0, levels: [3, 0, 0, 1, 2, 2, 1, 0] },
  { name: "Microsoft 365", overall: 1, levels: [1, 1, 1, 1, 1, 1, 1, 4] },
  { name: "DATEV", overall: 1, levels: [3, 4, 1, 1, 2, 2, 3, 0] },
  { name: "IONOS Cloud", overall: 1, levels: [3, 4, 1, 1, 2, 2, 4, 0] },
  { name: "Nextcloud", overall: 1, levels: [3, 1, 3, 1, 2, 2, 1, 0] },
  { name: "Personio", overall: 1, levels: [3, 1, 3, 1, 2, 2, 3, 0] },
];

export default function HeroPreview() {
  return (
    <figure className="rounded-lg border border-hairline bg-surface p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] sm:p-5">
      <table className="w-full border-separate border-spacing-1 text-xs">
        <caption className="sr-only">Ausschnitt der Heatmap der Musterbank AG</caption>
        <thead>
          <tr>
            <th scope="col" className="text-left font-normal text-ink-muted">
              Dienst
            </th>
            <th scope="col" className="font-normal text-ink-muted">
              Gesamt
            </th>
            {OBJECTIVES.map((objective) => (
              <th key={objective.key} scope="col" className="hidden font-normal text-ink-muted sm:table-cell" title={objective.label}>
                {objective.short}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => (
            <tr key={row.name}>
              <th scope="row" className="whitespace-nowrap pr-2 text-left font-medium">
                {row.name}
              </th>
              <td>
                <span className="tabular flex h-7 items-center justify-center rounded-sm font-semibold" style={levelStyle(row.overall)}>
                  {row.overall}
                </span>
              </td>
              {row.levels.map((level, index) => (
                <td key={OBJECTIVES[index].key} className="hidden sm:table-cell">
                  <span className="tabular flex h-7 items-center justify-center rounded-sm" style={levelStyle(level)}>
                    {level}
                  </span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <figcaption className="mt-3 text-xs text-ink-muted">
        Ausschnitt aus der Bewertung der fiktiven Musterbank AG. Die Gesamtstufe ist der schwächste
        Zielbereich ohne Umwelt.
      </figcaption>
    </figure>
  );
}
