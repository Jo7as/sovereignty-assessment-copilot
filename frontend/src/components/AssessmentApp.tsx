"use client";

import { useState } from "react";

import { ApiError, type RowProblem, assessFile, loadDemo } from "@/lib/api";
import type { Assessment } from "@/lib/types";

import Results from "./Results";
import StartPanel from "./StartPanel";

type State =
  | { kind: "start"; error?: string; details?: RowProblem[] }
  | { kind: "loading"; label: string }
  | { kind: "result"; assessment: Assessment };

export default function AssessmentApp() {
  const [state, setState] = useState<State>({ kind: "start" });

  async function run(label: string, request: () => Promise<Assessment>) {
    setState({ kind: "loading", label });
    try {
      setState({ kind: "result", assessment: await request() });
    } catch (error) {
      if (error instanceof ApiError) {
        setState({ kind: "start", error: error.message, details: error.details });
      } else {
        setState({ kind: "start", error: "Unbekannter Fehler." });
      }
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 sm:px-6 lg:px-8">
      <header className="flex items-baseline justify-between border-b border-hairline py-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">
            Sovereignty Assessment Copilot
          </p>
          <p className="text-sm text-ink-secondary">
            Abhängigkeit von IT-Anbietern außerhalb der EU, bewertet nach dem EU Cloud
            Sovereignty Framework
          </p>
        </div>
        {state.kind === "result" && (
          <button
            type="button"
            onClick={() => setState({ kind: "start" })}
            className="rounded border border-baseline px-3 py-1.5 text-sm hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent"
          >
            Neue Bewertung
          </button>
        )}
      </header>

      <main className="flex-1 py-8">
        {state.kind === "start" && (
          <StartPanel
            error={state.error}
            details={state.details}
            onDemo={() => run("Die Musterbank wird bewertet …", loadDemo)}
            onFile={(file) => run(`„${file.name}“ wird bewertet …`, () => assessFile(file))}
          />
        )}
        {state.kind === "loading" && (
          <p role="status" aria-live="polite" className="py-24 text-center text-ink-secondary">
            {state.label}
          </p>
        )}
        {state.kind === "result" && <Results assessment={state.assessment} />}
      </main>

      <footer className="border-t border-hairline py-5 text-xs text-ink-muted">
        Prototyp für ein Bewerbungsprojekt. Keine Rechtsberatung. Die Angaben zu den
        Anbietern stammen aus öffentlichen Quellen und sind je Dienst belegt. Ob eine
        Angabe von der KI nachgeprüft oder von einem Menschen bestätigt wurde, steht in
        der Detailansicht.
      </footer>
    </div>
  );
}
