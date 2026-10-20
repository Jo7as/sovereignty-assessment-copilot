"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, loadDemo } from "@/lib/api";
import type { Assessment } from "@/lib/types";

import Results from "./Results";
import Shell from "./Shell";

type State = { kind: "loading" } | { kind: "error"; message: string } | { kind: "ready"; assessment: Assessment };

// Bewertung der fiktiven Musterbank AG, ohne Fragebogen und ohne Speichern
export default function DemoView() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    loadDemo()
      .then((assessment) => active && setState({ kind: "ready", assessment }))
      .catch((error: unknown) => {
        if (active) setState({ kind: "error", message: error instanceof ApiError ? error.message : "Unbekannter Fehler." });
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <Shell
      actions={
        <Link
          href="/#start"
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-ink hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Eigenes Assessment starten
        </Link>
      }
    >
      <p className="mb-8 max-w-3xl border-l-4 border-accent bg-surface px-4 py-3 text-sm text-ink-secondary">
        Beispiel: die fiktive Musterbank AG mit 58 Einträgen im IT-Bestand, bewertet ohne KI.
        Fragebogen, Reifegrad und DORA-Prüfung gehören zum eigenen Assessment.
      </p>
      {state.kind === "loading" && (
        <p role="status" aria-live="polite" className="py-24 text-center text-ink-secondary">
          Die Musterbank wird bewertet …
        </p>
      )}
      {state.kind === "error" && (
        <div role="alert" className="max-w-2xl border-l-4 border-critical bg-surface px-4 py-3 text-sm">
          <p className="font-medium">Das Beispiel konnte nicht geladen werden.</p>
          <p className="mt-1 text-ink-secondary">{state.message}</p>
        </div>
      )}
      {state.kind === "ready" && <Results assessment={state.assessment} />}
    </Shell>
  );
}
