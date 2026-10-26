import { LEVELS, OBJECTIVES } from "@/lib/labels";
import type { AssessedService, Level } from "@/lib/types";

import { levelStyle } from "../LevelCell";
import { Sheet, SheetTitle } from "./Sheet";

// Kompakte Heatmap für Papier: kleine Zellen, keine Tooltips, gesicherte und mögliche Stufe
function Cell({ level, potential, strong = false }: { level: Level; potential: Level; strong?: boolean }) {
  return (
    <span
      className={`tabular flex h-5 items-center justify-center rounded-[2px] text-[10px] ${strong ? "font-semibold" : ""}`}
      style={levelStyle(level)}
    >
      {level}
      {potential > level && <span className="ml-0.5 opacity-80">↗{potential}</span>}
    </span>
  );
}

const SCALE: Level[] = [0, 1, 2, 3, 4];

function Legend() {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[10px] text-ink-secondary">
      {SCALE.map((level) => (
        <span key={level} className="flex items-center gap-1.5">
          <span className="w-5">
            <Cell level={level} potential={level} />
          </span>
          {LEVELS[level].name}
        </span>
      ))}
      <span className="flex items-center gap-1.5">
        <span className="w-8">
          <Cell level={1} potential={3} />
        </span>
        gesichert 1, möglich 3
      </span>
    </div>
  );
}

interface Props {
  eyebrow: string;
  title: string;
  intro: string;
  services: AssessedService[];
}

export default function HeatmapPage({ eyebrow, title, intro, services }: Props) {
  return (
    <Sheet label={title}>
      <SheetTitle eyebrow={eyebrow}>{title}</SheetTitle>
      <p className="mb-4 text-ink-secondary">{intro}</p>
      <Legend />
      <table className="w-full table-fixed border-collapse text-[11px]">
        <thead>
          <tr className="text-left text-[10px] text-ink-muted">
            <th className="w-[46mm] pb-1 font-normal">Dienst</th>
            {OBJECTIVES.map((objective) => (
              <th key={objective.key} className="pb-1 text-center font-normal" title={objective.label}>
                {objective.short}
              </th>
            ))}
            <th className="pb-1 text-center font-medium">Gesamt</th>
          </tr>
        </thead>
        <tbody>
          {services.map((service) => (
            <tr key={`${service.service}-${service.variant}`} className="break-inside-avoid border-t border-hairline">
              <td className="py-1 pr-2 leading-tight">
                <span className="block truncate font-medium">{service.name}</span>
                <span className="block truncate text-[9px] text-ink-muted">{service.provider}</span>
              </td>
              {OBJECTIVES.map((objective) => (
                <td key={objective.key} className="px-0.5 py-1">
                  <Cell level={service.objectives[objective.key].level} potential={service.objectives[objective.key].potential} />
                </td>
              ))}
              <td className="py-1 pl-1">
                <Cell level={service.level} potential={service.potential} strong />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-[10px] text-ink-muted">
        Umwelt zählt nur im Souveränitätswert, nicht in der Gesamtstufe. Die Gesamtstufe ist der schwächste der übrigen
        sieben Zielbereiche.
      </p>
    </Sheet>
  );
}
