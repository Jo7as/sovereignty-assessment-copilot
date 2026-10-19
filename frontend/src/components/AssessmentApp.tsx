"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, type ProblemDetail, assessFile, createAssessment, loadDemo } from "@/lib/api";
import type { Assessment } from "@/lib/types";

import Results from "./Results";
import Shell from "./Shell";
import StartPanel from "./StartPanel";

type State =
  | { kind: "start"; error?: string; details?: ProblemDetail[] }
  | { kind: "loading"; label: string }
  | { kind: "result"; assessment: Assessment };

export default function AssessmentApp() {
  const router = useRouter();
  const [state, setState] = useState<State>({ kind: "start" });

  async function create(name: string) {
    setState({ kind: "loading", label: "Das Assessment wird angelegt …" });
    try {
      const assessment = await createAssessment(name);
      router.push(`/assessments/${assessment.id}`);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Unbekannter Fehler.";
      setState({ kind: "start", error: message });
    }
  }

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
    <Shell
      actions={
        state.kind === "result" && (
          <button
            type="button"
            onClick={() => setState({ kind: "start" })}
            className="rounded border border-baseline px-3 py-1.5 text-sm hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent"
          >
            Neue Bewertung
          </button>
        )
      }
    >
      {state.kind === "start" && (
        <StartPanel
          error={state.error}
          details={state.details}
          onCreate={(name) => create(name)}
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
    </Shell>
  );
}
