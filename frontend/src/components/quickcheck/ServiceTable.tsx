import { CRITICALITY, EFFORT, LEVELS } from "@/lib/labels";
import type { ScannedService } from "@/lib/types";

import LevelCell from "../LevelCell";
import { JURISDICTION, RECORD_LABEL } from "./records";

interface Props {
  id: string;
  title: string;
  intro: string;
  services: ScannedService[];
}

const COLUMNS = "md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_minmax(0,1.3fr)_3.5rem_5.5rem_minmax(0,1.2fr)]";

// Jeder Dienst, jeder Eigentümer, jede Alternative. Zeile aufklappen für den Beleg.
export default function ServiceTable({ id, title, intro, services }: Props) {
  if (services.length === 0) return null;
  return (
    <section aria-labelledby={id}>
      <h2 id={id} className="text-xl font-semibold tracking-tight">
        {title} <span className="tabular text-base font-normal text-ink-muted">({services.length})</span>
      </h2>
      <p className="text-sm text-ink-secondary">{intro}</p>
      <div className="mt-4 overflow-hidden rounded-lg border border-hairline">
        <div className={`hidden gap-4 border-b border-hairline bg-surface px-4 py-2 text-xs font-medium uppercase tracking-wide text-ink-muted md:grid ${COLUMNS}`} aria-hidden>
          <span>Dienst</span>
          <span>Kategorie</span>
          <span>Eigentümer</span>
          <span>Stufe</span>
          <span>Kritikalität</span>
          <span>EU-Alternative</span>
        </div>
        <ul className="divide-y divide-hairline">
          {services.map((service) => (
            <li key={service.service}>
              <details className="group">
                <summary className={`grid cursor-pointer list-none grid-cols-[3.5rem_1fr] items-center gap-x-4 gap-y-1 px-4 py-3 hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent ${COLUMNS}`}>
                  <span className="col-span-2 md:col-span-1">
                    <span className="block font-medium">
                      {service.name}
                      <span aria-hidden className="ml-1 text-xs text-ink-muted transition-transform group-open:rotate-90 inline-block">›</span>
                    </span>
                    <span className="block text-xs text-ink-muted">
                      {service.strength === "NUTZUNG" ? "Nutzung belegt" : "Hinweis"} · {RECORD_LABEL[service.findings[0]?.record] ?? ""}
                    </span>
                  </span>
                  <span className="hidden text-sm text-ink-secondary md:block">{service.category}</span>
                  <span className="col-span-2 text-sm md:col-span-1">
                    {service.owner}
                    <span className={`block text-xs ${service.jurisdiction === "EU_EWR" ? "text-ink-muted" : "font-medium text-critical"}`}>
                      {service.owner_country} · {JURISDICTION[service.jurisdiction]}
                    </span>
                  </span>
                  <span title={LEVELS[service.level].name}>
                    <LevelCell level={service.level} potential={service.potential} />
                  </span>
                  <span className="text-sm text-ink-secondary">{CRITICALITY[service.criticality]}</span>
                  <span className="col-span-2 text-sm md:col-span-1">
                    {service.alternatives.length > 0 ? (
                      <>
                        {service.alternatives[0].name}
                        <span className="block text-xs text-ink-muted">
                          {EFFORT[service.alternatives[0].effort]}
                          {service.alternatives.length > 1 && ` · +${service.alternatives.length - 1}`}
                        </span>
                      </>
                    ) : (
                      <span className="text-ink-muted">keine in der Datenbank</span>
                    )}
                  </span>
                </summary>
                <div className="space-y-3 border-t border-hairline bg-surface px-4 py-3 text-sm">
                  <p className="text-ink-secondary">
                    Stufe {service.level}: {LEVELS[service.level].name}
                    {service.potential > service.level && `, möglich wäre Stufe ${service.potential}`}. Anbieter laut
                    Vertrag: {service.provider}.
                  </p>
                  {service.findings.map((finding) => (
                    <div key={`${finding.record}-${finding.value}`}>
                      <p className="font-medium">{RECORD_LABEL[finding.record] ?? finding.record}</p>
                      <p className="break-all font-mono text-xs text-ink-secondary">{finding.value}</p>
                      {finding.meaning && <p className="text-ink-secondary">{finding.meaning}</p>}
                      {finding.evidence && (
                        <p className="mt-1 text-xs text-ink-muted">
                          Beleg: „{finding.evidence.quote}“{" "}
                          <a href={finding.evidence.source} target="_blank" rel="noreferrer" className="underline">
                            Quelle
                          </a>
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </details>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
