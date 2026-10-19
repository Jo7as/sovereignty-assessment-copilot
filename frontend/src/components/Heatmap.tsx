"use client";

import { useEffect, useState } from "react";

import { CRITICALITY, LEVELS, OBJECTIVES, levelText } from "@/lib/labels";
import type { AssessedService, Criticality, ObjectiveKey } from "@/lib/types";

import LevelCell from "./LevelCell";
import LevelLegend from "./LevelLegend";

interface Tooltip {
  x: number;
  y: number;
  title: string;
  lines: string[];
}

interface Props {
  services: AssessedService[];
  onSelect: (service: AssessedService) => void;
}

const GROUPS: { key: Criticality; label: string }[] = [
  { key: "HOCH", label: "Hohe Kritikalität" },
  { key: "MITTEL", label: "Mittlere Kritikalität" },
  { key: "GERING", label: "Geringe Kritikalität" },
];

function explain(service: AssessedService, key: ObjectiveKey | "GESAMT") {
  if (key === "GESAMT") {
    return {
      title: `${service.name}: Gesamtstufe`,
      lines: [
        levelText(service.level, service.potential),
        `${LEVELS[service.level].name}. Der schwächste Zielbereich bestimmt die Gesamtstufe.`,
      ],
    };
  }
  const result = service.objectives[key];
  const label = OBJECTIVES.find((objective) => objective.key === key)?.label ?? key;
  const limiting = result.findings.filter((finding) => finding.ceiling === result.level);
  return {
    title: `${service.name}: ${label}`,
    lines: [
      levelText(result.level, result.potential),
      ...(result.level < 4 ? limiting.slice(0, 2).map((finding) => finding.reason) : []),
    ],
  };
}

export default function Heatmap({ services, onSelect }: Props) {
  const [tooltip, setTooltip] = useState<Tooltip | null>(null);

  // Ein fest positionierter Tooltip würde beim Scrollen an der falschen Stelle stehen bleiben
  useEffect(() => {
    if (!tooltip) return;
    const hide = () => setTooltip(null);
    window.addEventListener("scroll", hide, { passive: true, capture: true });
    return () => window.removeEventListener("scroll", hide, { capture: true });
  }, [tooltip]);

  function select(service: AssessedService) {
    setTooltip(null);
    onSelect(service);
  }

  function show(event: React.MouseEvent | React.FocusEvent, service: AssessedService, key: ObjectiveKey | "GESAMT") {
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    setTooltip({ x: rect.left + rect.width / 2, y: rect.bottom + 8, ...explain(service, key) });
  }

  return (
    <section aria-labelledby="heatmap-title">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 id="heatmap-title" className="text-lg font-semibold">
            Heatmap: Dienste und Zielbereiche
          </h2>
          <p className="text-sm text-ink-secondary">
            Stufe 0 bis 4 je Zielbereich. Für Details auf eine Zelle oder einen Dienst klicken.
          </p>
        </div>
        <LevelLegend />
      </div>

      <div className="mt-4 overflow-x-auto border border-hairline bg-surface">
        <table className="w-full min-w-[56rem] border-collapse text-sm">
          <caption className="sr-only">
            Stufe je Dienst und Zielbereich, gesicherte Stufe mit möglicher Stufe bei fehlenden Angaben
          </caption>
          <thead>
            <tr className="border-b border-hairline text-left text-xs text-ink-muted">
              <th scope="col" className="px-3 py-2 font-medium">Dienst</th>
              {OBJECTIVES.map((objective) => (
                <th key={objective.key} scope="col" className="w-20 px-1 py-2 text-center font-medium">
                  <abbr title={`${objective.label}, Gewicht ${objective.weight} %`} className="no-underline">
                    {objective.short}
                  </abbr>
                </th>
              ))}
              <th scope="col" className="w-20 border-l border-hairline px-1 py-2 text-center font-medium">
                Gesamt
              </th>
            </tr>
          </thead>
          {GROUPS.map((group) => {
            const rows = services.filter((service) => service.criticality === group.key);
            if (rows.length === 0) return null;
            return (
              <tbody key={group.key}>
                <tr>
                  <th colSpan={10} scope="colgroup" className="bg-page px-3 py-1.5 text-left text-xs font-medium text-ink-secondary">
                    {group.label} ({rows.length})
                  </th>
                </tr>
                {rows.map((service) => (
                  <tr key={service.service} className="border-t border-hairline">
                    <th scope="row" className="px-3 py-1 text-left font-normal">
                      <button
                        type="button"
                        onClick={() => select(service)}
                        className="text-left hover:underline focus-visible:outline-2 focus-visible:outline-accent"
                      >
                        <span className="font-medium">{service.name}</span>
                        {service.needs_review && (
                          <span className="ml-1 text-xs text-ink-muted" title="Zuordnung ungeprüft">*</span>
                        )}
                        <span className="block text-xs text-ink-muted">
                          {service.provider} · Kritikalität {CRITICALITY[service.criticality]}
                        </span>
                      </button>
                    </th>
                    {OBJECTIVES.map((objective) => {
                      const result = service.objectives[objective.key];
                      return (
                        <td key={objective.key} className="px-1 py-1">
                          <button
                            type="button"
                            className="block w-full focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent"
                            aria-label={`${service.name}, ${objective.label}: ${levelText(result.level, result.potential)}`}
                            onClick={() => select(service)}
                            onMouseEnter={(event) => show(event, service, objective.key)}
                            onMouseLeave={() => setTooltip(null)}
                            onFocus={(event) => show(event, service, objective.key)}
                            onBlur={() => setTooltip(null)}
                          >
                            <LevelCell level={result.level} potential={result.potential} />
                          </button>
                        </td>
                      );
                    })}
                    <td className="border-l border-hairline px-1 py-1">
                      <button
                        type="button"
                        className="block w-full focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent"
                        aria-label={`${service.name}, Gesamtstufe: ${levelText(service.level, service.potential)}`}
                        onClick={() => select(service)}
                        onMouseEnter={(event) => show(event, service, "GESAMT")}
                        onMouseLeave={() => setTooltip(null)}
                        onFocus={(event) => show(event, service, "GESAMT")}
                        onBlur={() => setTooltip(null)}
                      >
                        <LevelCell level={service.level} potential={service.potential} emphasis />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            );
          })}
        </table>
      </div>
      <p className="mt-2 text-xs text-ink-muted">* Zuordnung durch die KI vorgeschlagen, noch nicht geprüft.</p>

      {tooltip && (
        <div
          role="tooltip"
          className="pointer-events-none fixed z-50 max-w-xs -translate-x-1/2 border border-hairline bg-surface px-3 py-2 text-xs shadow-sm"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <p className="font-medium">{tooltip.title}</p>
          {tooltip.lines.map((line) => (
            <p key={line} className="mt-1 text-ink-secondary">{line}</p>
          ))}
        </div>
      )}
    </section>
  );
}
