"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, loadAssessment, loadQuestionnaire } from "@/lib/api";
import type { Questionnaire, StoredAssessment } from "@/lib/types";
import { useAnswers } from "@/lib/use-answers";

import QuestionnaireForm from "./questionnaire/QuestionnaireForm";
import Shell from "./Shell";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string; notFound: boolean }
  | { kind: "ready"; questionnaire: Questionnaire; assessment: StoredAssessment };

// Ein gespeichertes Assessment. Die Adresse /assessments/{id} lässt sich merken, um später
// weiterzumachen.
export default function AssessmentWorkspace({ id }: { id: number }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    Promise.all([loadQuestionnaire(), loadAssessment(id)])
      .then(([questionnaire, assessment]) => {
        if (active) setState({ kind: "ready", questionnaire, assessment });
      })
      .catch((error: unknown) => {
        if (!active) return;
        const message = error instanceof ApiError ? error.message : "Unbekannter Fehler.";
        setState({ kind: "error", message, notFound: error instanceof ApiError && error.status === 404 });
      });
    return () => {
      active = false;
    };
  }, [id]);

  return (
    <Shell
      actions={
        <Link
          href="/"
          className="rounded border border-baseline px-3 py-1.5 text-sm hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent"
        >
          Startseite
        </Link>
      }
    >
      {state.kind === "loading" && (
        <p role="status" aria-live="polite" className="py-24 text-center text-ink-secondary">
          Das Assessment wird geladen …
        </p>
      )}
      {state.kind === "error" && (
        <div role="alert" className="max-w-2xl border-l-4 border-critical bg-surface px-4 py-3 text-sm">
          <p className="font-medium">
            {state.notFound ? "Dieses Assessment gibt es nicht." : "Das Assessment konnte nicht geladen werden."}
          </p>
          <p className="mt-1 text-ink-secondary">{state.message}</p>
        </div>
      )}
      {state.kind === "ready" && <Ready questionnaire={state.questionnaire} initial={state.assessment} />}
    </Shell>
  );
}

function Ready({ questionnaire, initial }: { questionnaire: Questionnaire; initial: StoredAssessment }) {
  const { answers, errors, status, save, reject } = useAnswers(initial);
  const created = new Date(initial.created_at).toLocaleDateString("de-DE");

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{initial.name}</h1>
        <p className="text-sm text-ink-secondary">
          Assessment vom {created}. Diese Seite lässt sich als Lesezeichen speichern, um später
          weiterzumachen.
        </p>
      </div>
      <QuestionnaireForm
        questionnaire={questionnaire}
        answers={answers}
        errors={errors}
        status={status}
        onSave={save}
        onReject={reject}
      />
    </div>
  );
}
