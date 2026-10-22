"use client";

import { useEffect, useState } from "react";

// Die Schritte kommen vom Server (Ereignis „plan“), damit Anzeige und Backend nie auseinanderlaufen
interface Props {
  domain: string;
  steps: string[];
  current: string | null;
}

export default function ScanProgress({ domain, steps, current }: Props) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);
  const index = current ? steps.indexOf(current) : -1;

  return (
    <section aria-labelledby="progress-title" className="mx-auto max-w-xl rounded-lg border border-hairline bg-surface p-6">
      <div className="flex items-baseline justify-between gap-4">
        <h1 id="progress-title" className="font-semibold">
          {domain} wird geprüft …
        </h1>
        <span className="tabular text-sm text-ink-muted" aria-hidden>
          {seconds} s
        </span>
      </div>
      <ol className="mt-5 space-y-3" aria-live="polite">
        {steps.map((step, position) => {
          const state = position < index ? "done" : position === index ? "active" : "open";
          return (
            <li key={step} className="flex items-center gap-3 text-sm">
              <span
                aria-hidden
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs ${
                  state === "done"
                    ? "border-accent text-accent"
                    : state === "active"
                      ? "animate-pulse border-accent bg-accent text-accent-ink"
                      : "border-baseline text-ink-muted"
                }`}
              >
                {state === "done" ? "✓" : position + 1}
              </span>
              <span className={state === "open" ? "text-ink-muted" : state === "active" ? "font-medium" : ""}>
                {step}
                <span className="sr-only">
                  {state === "done" ? " (erledigt)" : state === "active" ? " (läuft)" : ""}
                </span>
              </span>
            </li>
          );
        })}
      </ol>
      <div className="mt-6 h-1 bg-hairline" aria-hidden>
        <div
          className="h-1 bg-accent transition-[width] duration-500"
          style={{ width: `${(Math.max(index, 0) / Math.max(steps.length, 1)) * 100}%` }}
        />
      </div>
      <p className="mt-3 text-xs text-ink-muted">
        Geprüft werden nur öffentlich sichtbare Angaben: DNS, Website, Impressum und das Register
        GLEIF. Das dauert meist 15 bis 30 Sekunden.
      </p>
    </section>
  );
}
