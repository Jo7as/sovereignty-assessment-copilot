"use client";

import { useEffect, useRef } from "react";

import { CRITICALITY, OBJECTIVES, REVIEW_STATUS, attributeLabel, levelText } from "@/lib/labels";
import type { AssessedService } from "@/lib/types";

import LevelCell from "./LevelCell";

interface Props {
  service: AssessedService | null;
  onClose: () => void;
}

export default function ServiceDetail({ service, onClose }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (service && !element.open) element.showModal();
    if (!service && element.open) element.close();
  }, [service]);

  return (
    <dialog
      ref={dialog}
      onClose={onClose}
      aria-labelledby="detail-title"
      className="m-0 ml-auto h-full max-h-none w-full max-w-2xl border-l border-hairline bg-surface p-0 text-ink backdrop:bg-black/30"
    >
      {service && (
        <div className="flex h-full flex-col">
          <div className="flex items-start justify-between gap-4 border-b border-hairline px-6 py-4">
            <div>
              <h2 id="detail-title" className="text-lg font-semibold">{service.name}</h2>
              <p className="text-sm text-ink-secondary">
                {service.provider} · Variante „{service.variant_name}“ · Kritikalität {CRITICALITY[service.criticality]}
              </p>
              <p className="mt-1 text-xs text-ink-muted">
                {REVIEW_STATUS[service.review_status]} · Zeilen {service.rows.join(", ")} im IT-Bestand
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-baseline px-3 py-1 text-sm focus-visible:outline-2 focus-visible:outline-accent"
            >
              Schließen
            </button>
          </div>

          <div className="flex-1 space-y-6 overflow-y-auto px-6 py-5">
            <p className="text-sm">
              Gesamt: <strong>{levelText(service.level, service.potential)}</strong>, Souveränitätswert{" "}
              {Math.round(service.score)} von 100
            </p>
            {service.notes.map((note) => (
              <p key={note} className="border-l-2 border-baseline pl-3 text-sm text-ink-secondary">{note}</p>
            ))}

            {OBJECTIVES.map((objective) => {
              const result = service.objectives[objective.key];
              return (
                <section key={objective.key} aria-labelledby={`objective-${objective.key}`}>
                  <div className="flex items-center gap-3">
                    <span className="w-12"><LevelCell level={result.level} potential={result.potential} /></span>
                    <h3 id={`objective-${objective.key}`} className="font-medium">{objective.label}</h3>
                  </div>
                  <ul className="mt-2 space-y-1.5 text-sm">
                    {result.findings.map((finding) => (
                      <li key={finding.criterion} className="flex gap-3">
                        <span className="tabular w-24 shrink-0 text-xs text-ink-muted">
                          höchstens {finding.ceiling}
                          {finding.is_gap ? ` (möglich ${finding.potential})` : ""}
                        </span>
                        <span>
                          <span className="font-medium">{finding.criterion}:</span> {finding.reason}
                        </span>
                      </li>
                    ))}
                  </ul>
                </section>
              );
            })}

            <section aria-labelledby="evidence-title">
              <h3 id="evidence-title" className="font-medium">Belege</h3>
              {service.evidence.length === 0 ? (
                <p className="mt-2 text-sm text-ink-secondary">Für diesen Dienst sind noch keine Belege erfasst.</p>
              ) : (
                <ul className="mt-2 space-y-3 text-sm">
                  {service.evidence.map((item, index) => (
                    <li key={`${item.attribute}-${index}`} className="border-l-2 border-hairline pl-3">
                      <p className="font-medium">{attributeLabel(item.attribute)}</p>
                      {item.quote && <p className="mt-0.5 text-ink-secondary">„{item.quote}“</p>}
                      <p className="mt-0.5 text-xs text-ink-muted">
                        <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="underline">
                          {new URL(item.source_url).hostname}
                        </a>
                        , abgerufen am {new Date(item.retrieved_at).toLocaleDateString("de-DE")}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>
      )}
    </dialog>
  );
}
