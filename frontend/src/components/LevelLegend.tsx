import { LEVELS } from "@/lib/labels";
import type { Level } from "@/lib/types";

import LevelCell from "./LevelCell";

export default function LevelLegend() {
  const levels: Level[] = [0, 1, 2, 3, 4];
  return (
    <div className="flex flex-wrap items-start gap-x-6 gap-y-3 text-xs text-ink-secondary">
      <ul className="flex flex-wrap gap-x-4 gap-y-2" aria-label="Stufen">
        {levels.map((level) => (
          <li key={level} className="flex items-center gap-2">
            <span className="w-9">
              <LevelCell level={level} potential={level} />
            </span>
            <span>{LEVELS[level].name}</span>
          </li>
        ))}
      </ul>
      <p className="flex items-center gap-2">
        <span className="w-12">
          <LevelCell level={1} potential={3} />
        </span>
        <span>
          Gesicherte Stufe 1, möglich wäre Stufe 3. Fehlende Angaben zählen wie der
          ungünstigste Fall.
        </span>
      </p>
    </div>
  );
}
