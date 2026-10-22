import { CRITICALITY, LEVELS } from "@/lib/labels";
import type { ScannedService } from "@/lib/types";

import LevelCell from "../LevelCell";

const RECORD_LABEL: Record<string, string> = {
  MX: "Mailserver",
  SPF: "SPF-Eintrag",
  SPF_NET: "Netz eines E-Mail-Absenders",
  NS: "Nameserver",
  CAA: "Zertifizierungsstelle",
  CNAME: "Weiterleitung der Website",
  ASN: "Netz der Website",
  WEB: "Von der Website geladen",
  SCRIPT: "Im Tag Manager oder Seitencode",
  TECH: "Technik der Website",
};

interface Props {
  id: string;
  title: string;
  intro: string;
  services: ScannedService[];
}

// Erkannte Dienste mit Stufe, Stärke des Funds und aufklappbarem Beleg
export default function ServiceList({ id, title, intro, services }: Props) {
  if (services.length === 0) return null;
  return (
    <section aria-labelledby={id}>
      <h2 id={id} className="text-xl font-semibold tracking-tight">
        {title} <span className="tabular text-base font-normal text-ink-muted">({services.length})</span>
      </h2>
      <p className="text-sm text-ink-secondary">{intro}</p>
      <ul className="mt-4 divide-y divide-hairline rounded-lg border border-hairline">
        {services.map((service) => (
          <li key={service.service}>
            <details className="group">
              <summary className="grid cursor-pointer list-none grid-cols-[3.5rem_1fr_auto] items-center gap-4 px-4 py-3 hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent">
                <span title={LEVELS[service.level].name}>
                  <LevelCell level={service.level} potential={service.potential} />
                </span>
                <span className="min-w-0">
                  <span className="block font-medium">{service.name}</span>
                  <span className="block truncate text-xs text-ink-muted">{service.provider}</span>
                </span>
                <span className="text-right text-xs">
                  <span className={service.strength === "NUTZUNG" ? "font-medium" : "text-ink-secondary"}>
                    {service.strength === "NUTZUNG" ? "Nutzung belegt" : "Hinweis"}
                  </span>
                  <span className="block text-ink-muted">Kritikalität {CRITICALITY[service.criticality]}</span>
                </span>
              </summary>
              <div className="space-y-3 border-t border-hairline bg-surface px-4 py-3 text-sm">
                <p className="text-ink-secondary">
                  Stufe {service.level}: {LEVELS[service.level].name}
                  {service.potential > service.level && `, möglich wäre Stufe ${service.potential}`}.
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
    </section>
  );
}

export { RECORD_LABEL };
