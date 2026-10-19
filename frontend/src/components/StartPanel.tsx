"use client";

import { useId, useRef, useState } from "react";

import { API_URL, type ProblemDetail } from "@/lib/api";
import ProblemList from "./ProblemList";

interface Props {
  error?: string;
  details?: ProblemDetail[];
  onCreate: (name: string) => void;
  onDemo: () => void;
  onFile: (file: File) => void;
}

export default function StartPanel({ error, details = [], onCreate, onDemo, onFile }: Props) {
  const inputId = useId();
  const nameId = useId();
  const [name, setName] = useState("");
  const input = useRef<HTMLInputElement>(null);

  return (
    <section aria-labelledby="start-title" className="max-w-3xl">
      <h1 id="start-title" className="text-2xl font-semibold tracking-tight sm:text-3xl">
        Wie abhängig ist Ihr Unternehmen von IT-Anbietern außerhalb der EU?
      </h1>
      <p className="mt-3 text-ink-secondary">
        Das Tool ordnet jeden Eintrag Ihres IT-Bestands einem Dienst zu, bewertet ihn in
        acht Zielbereichen auf einer Stufe von 0 bis 4 und leitet eine Roadmap mit Fragen an
        Ihre Anbieter ab. Ein Fragebogen ergänzt, wie Ihr Unternehmen die Abhängigkeit steuert
        und ob DORA oder NIS2 gilt. Jede Aussage ist mit Quellen belegt.
      </p>

      {error && (
        <div role="alert" className="mt-6 border-l-4 border-critical bg-surface px-4 py-3 text-sm">
          <p className="font-medium">Das hat nicht geklappt.</p>
          <p className="mt-1 text-ink-secondary">{error}</p>
          <ProblemList details={details} />
        </div>
      )}

      <form
        className="mt-8 border border-hairline bg-surface p-5"
        onSubmit={(event) => {
          event.preventDefault();
          if (name.trim()) onCreate(name.trim());
        }}
      >
        <h2 className="font-medium">Assessment anlegen</h2>
        <p className="mt-1 text-sm text-ink-secondary">
          Fragebogen zu Steuerung, Exit-Strategie und Notfallplanung, danach der IT-Bestand.
          Alles wird gespeichert, Sie können jederzeit weitermachen.
        </p>
        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor={nameId} className="block text-sm font-medium">
              Name des Unternehmens
            </label>
            <input
              id={nameId}
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={200}
              required
              placeholder="z. B. Musterbank AG"
              className="mt-1 w-full rounded border border-baseline bg-page px-3 py-2 text-sm placeholder:text-ink-muted focus-visible:outline-2 focus-visible:outline-accent"
            />
          </div>
          <button
            type="submit"
            className="rounded bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Assessment starten
          </button>
        </div>
      </form>

      <h2 className="mt-10 text-sm font-medium text-ink-secondary">Ohne Speichern ausprobieren</h2>
      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div className="border border-hairline bg-surface p-5">
          <h3 className="font-medium">Beispiel ansehen</h3>
          <p className="mt-1 text-sm text-ink-secondary">
            Musterbank AG: fiktive Privatbank mit 58 Einträgen im IT-Bestand.
          </p>
          <button
            type="button"
            onClick={onDemo}
            className="mt-4 rounded border border-baseline px-4 py-2 text-sm font-medium hover:bg-page focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Musterbank bewerten
          </button>
        </div>

        <div className="border border-hairline bg-surface p-5">
          <h3 className="font-medium">Eigenen IT-Bestand bewerten</h3>
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
