import { CRITICALITY, EFFORT, LEVELS } from "@/lib/labels";
import type { QuickCheckResult } from "@/lib/types";

import LevelCell from "../LevelCell";

// Die Dienste, bei denen ein Wechsel am meisten bringt, wie in der Roadmap berechnet
export default function Levers({ levers }: { levers: QuickCheckResult["levers"] }) {
  if (levers.length === 0) return null;
  return (
    <section aria-labelledby="levers-title">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Die größten Hebel</p>
      <h2 id="levers-title" className="mt-1 text-2xl font-semibold tracking-tight">
        Hier bringt ein Wechsel am meisten.
      </h2>
      <p className="mt-1 max-w-2xl text-sm text-ink-secondary">
        Sortiert nach Kritikalität mal Abstand zur Höchststufe. Wo es keine belegte EU-Alternative gibt, ist die Klärung
        mit dem Anbieter der erste Schritt.
      </p>
      <ol className="mt-5 grid gap-4 md:grid-cols-3">
        {levers.map((lever, index) => (
          <li key={lever.service} className="flex flex-col rounded-lg border border-hairline bg-surface p-5">
            <div className="flex items-center justify-between gap-3">
              <span className="tabular flex h-7 w-7 items-center justify-center rounded-full border border-baseline text-sm">
                {index + 1}
              </span>
              <span className="w-12">
                <LevelCell level={lever.level} potential={lever.level} />
              </span>
            </div>
            <h3 className="mt-3 font-semibold">{lever.name}</h3>
            <p className="text-xs text-ink-muted">
              {LEVELS[lever.level].name} · Kritikalität {CRITICALITY[lever.criticality]}
            </p>
            <div className="mt-4 flex-1 rounded-md border border-hairline bg-page p-3 text-sm">
              {lever.alternative ? (
                <>
                  <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Stattdessen</p>
                  <p className="mt-1 font-medium">{lever.alternative.name}</p>
                  <p className="text-xs text-ink-secondary">
                    {EFFORT[lever.alternative.effort]}
                    {lever.alternative.note && ` · ${lever.alternative.note}`}
                  </p>
                </>
              ) : (
                <p className="text-ink-secondary">
                  Keine belegte EU-Alternative in der Datenbank. Erster Schritt: Datenstandort, Schlüssel und Vertrag mit
                  dem Anbieter klären.
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
