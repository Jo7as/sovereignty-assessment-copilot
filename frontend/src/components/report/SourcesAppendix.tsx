import type { Report } from "@/lib/types";

import { Sheet, SheetTitle } from "./Sheet";

const date = (iso: string) => new Date(iso).toLocaleDateString("de-DE");

// Quellenverzeichnis: jede Fundstelle einmal, mit den Diensten, deren Bewertung sie stützt
export default function SourcesAppendix({ sources }: { sources: Report["sources"] }) {
  return (
    <Sheet label="Quellenverzeichnis">
      <SheetTitle eyebrow="Anhang C">Quellenverzeichnis</SheetTitle>
      <p className="mb-4 text-ink-secondary">
        {sources.length} Fundstellen, nach Adresse sortiert. Jede steht wörtlich in der genannten Quelle, abgerufen am
        angegebenen Tag.
      </p>
      <ol className="space-y-2 text-[10px] leading-snug">
        {sources.map((source, index) => (
          <li key={`${source.url}-${source.quote}`} className="grid break-inside-avoid grid-cols-[8mm_1fr] gap-2 border-t border-hairline pt-1.5">
            <span className="tabular text-ink-muted">[{index + 1}]</span>
            <div>
              <p className="text-ink">„{source.quote}“</p>
              <p className="mt-0.5 break-all font-mono text-[9px] text-ink-secondary">{source.url}</p>
              <p className="mt-0.5 text-[9px] text-ink-muted">
                Abgerufen am {date(source.retrieved_at)} · stützt {source.services.join(", ")}
              </p>
            </div>
          </li>
        ))}
      </ol>
    </Sheet>
  );
}
