"use client";

import { useId, useRef } from "react";

import { API_URL, type RowProblem } from "@/lib/api";

interface Props {
  error?: string;
  details?: RowProblem[];
  onDemo: () => void;
  onFile: (file: File) => void;
}

const MAX_SHOWN = 10;

export default function StartPanel({ error, details = [], onDemo, onFile }: Props) {
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);

  return (
    <section aria-labelledby="start-title" className="max-w-3xl">
      <h1 id="start-title" className="text-2xl font-semibold tracking-tight sm:text-3xl">
        Wie abhängig ist Ihr Unternehmen von IT-Anbietern außerhalb der EU?
      </h1>
      <p className="mt-3 text-ink-secondary">
        Laden Sie Ihren IT-Bestand hoch. Das Tool ordnet jeden Eintrag einem Dienst zu,
        bewertet ihn in acht Zielbereichen auf einer Stufe von 0 bis 4 und leitet eine
        Roadmap mit Fragen an Ihre Anbieter ab. Jede Bewertung ist mit Quellen belegt.
      </p>

      {error && (
        <div role="alert" className="mt-6 border-l-4 border-critical bg-surface px-4 py-3 text-sm">
          <p className="font-medium">Die Bewertung konnte nicht erstellt werden.</p>
          <p className="mt-1 text-ink-secondary">{error}</p>
          {details.length > 0 && (
            <ul className="mt-2 space-y-1 text-ink-secondary">
              {details.slice(0, MAX_SHOWN).map((problem) => (
                <li key={`${problem.row}-${problem.column}`}>
                  Zeile {problem.row}
                  {problem.column ? `, Spalte „${problem.column.replace(" *", "")}“` : ""}: {problem.message}
                </li>
              ))}
              {details.length > MAX_SHOWN && <li>und {details.length - MAX_SHOWN} weitere</li>}
            </ul>
          )}
        </div>
      )}

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <div className="border border-hairline bg-surface p-5">
          <h2 className="font-medium">Beispiel ansehen</h2>
          <p className="mt-1 text-sm text-ink-secondary">
            Musterbank AG: fiktive Privatbank mit 58 Einträgen im IT-Bestand.
          </p>
          <button
            type="button"
            onClick={onDemo}
            className="mt-4 rounded bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Musterbank bewerten
          </button>
        </div>

        <div className="border border-hairline bg-surface p-5">
          <h2 className="font-medium">Eigenen IT-Bestand bewerten</h2>
          <p className="mt-1 text-sm text-ink-secondary">
            Excel-Vorlage oder CSV-Datei, höchstens 5 MB. Es wird nichts gespeichert.
          </p>
          <label htmlFor={inputId} className="sr-only">
            IT-Bestand als Excel- oder CSV-Datei auswählen
          </label>
          <input
            ref={input}
            id={inputId}
            type="file"
            accept=".xlsx,.csv"
            className="sr-only"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onFile(file);
              event.target.value = "";
            }}
          />
          <button
            type="button"
            onClick={() => input.current?.click()}
            className="mt-4 rounded border border-baseline px-4 py-2 text-sm font-medium hover:bg-page focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Datei auswählen
          </button>
          <p className="mt-3 text-xs text-ink-muted">
            Noch keine Datei?{" "}
            <a href={`${API_URL}/inventory/template`} className="underline">
              Excel-Vorlage herunterladen
            </a>
          </p>
        </div>
      </div>
    </section>
  );
}
