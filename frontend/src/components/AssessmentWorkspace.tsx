"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, loadAssessment, loadQuestionnaire } from "@/lib/api";
import type { Questionnaire, StoredAssessment } from "@/lib/types";
import { useAnswers } from "@/lib/use-answers";

import InventoryStep from "./assessment/InventoryStep";
import MaturityPanel from "./assessment/MaturityPanel";
import RegulationPanel from "./assessment/RegulationPanel";
import QuestionnaireForm from "./questionnaire/QuestionnaireForm";
import Results from "./Results";
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
          className="rounded-md border border-baseline px-3 py-1.5 text-sm hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent"
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

type Step = "questionnaire" | "inventory" | "result";

const STEPS: { key: Step; label: string }[] = [
  { key: "questionnaire", label: "Fragebogen" },
  { key: "inventory", label: "IT-Bestand" },
  { key: "result", label: "Ergebnis" },
];

function Ready({ questionnaire, initial }: { questionnaire: Questionnaire; initial: StoredAssessment }) {
  const { assessment, answers, errors, status, save, reject, replace } = useAnswers(initial);
  // Wer mit Bestand und Antworten zurückkommt, sieht zuerst das Ergebnis. Nach dem Schnellcheck
  // gibt es schon einen Startbestand, aber noch keine Antworten: Dann kommt der Fragebogen zuerst.
  const [step, setStep] = useState<Step>(
    initial.inventory && initial.progress.answered > 0 ? "result" : "questionnaire",
  );
  const created = new Date(initial.created_at).toLocaleDateString("de-DE");

  function go(next: Step) {
    setStep(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">{initial.name}</h1>
        <p className="text-sm text-ink-secondary">
          Assessment vom {created}. Diese Seite lässt sich als Lesezeichen speichern, um später
          weiterzumachen.
        </p>
      </div>

      <nav aria-label="Schritte des Assessments" className="border-b border-hairline">
        <ol className="-mb-px flex gap-8 overflow-x-auto">
          {STEPS.map((item, index) => {
            const current = step === item.key;
            const done =
              (item.key === "questionnaire" && assessment.progress.answered === assessment.progress.total) ||
              (item.key === "inventory" && assessment.inventory !== null);
            return (
              <li key={item.key} className="shrink-0">
                <button
                  type="button"
                  onClick={() => go(item.key)}
                  aria-current={current ? "step" : undefined}
                  className="flex items-center gap-2.5 border-b-2 border-transparent pb-3 text-sm text-ink-secondary hover:text-ink focus-visible:outline-2 focus-visible:outline-accent aria-[current=step]:border-accent aria-[current=step]:font-medium aria-[current=step]:text-ink"
                >
                  <span
                    aria-hidden
                    className={`tabular flex h-6 w-6 items-center justify-center rounded-full border text-xs ${
                      current ? "border-accent bg-accent text-accent-ink" : "border-baseline"
                    }`}
                  >
                    {done && !current ? "✓" : index + 1}
                  </span>
                  {item.label}
                  {done && <span className="sr-only">(erledigt)</span>}
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      {step === "questionnaire" && (
        <QuestionnaireForm
          questionnaire={questionnaire}
          answers={answers}
          errors={errors}
          status={status}
          onSave={save}
          onReject={reject}
          onFinish={() => go("inventory")}
          prefill={assessment.prefill}
        />
      )}
      {step === "inventory" && (
        <InventoryStep
          assessment={assessment}
          onUploaded={(next) => {
            replace(next);
            go("result");
          }}
        />
      )}
      {step === "result" && <ResultStep assessment={assessment} onGo={go} />}
    </div>
  );
}

function ResultStep({ assessment, onGo }: { assessment: StoredAssessment; onGo: (step: Step) => void }) {
  const panels = (
    <div className="grid gap-12 lg:grid-cols-[3fr_2fr]">
      <RegulationPanel
        regulation={assessment.regulation}
        doraHints={assessment.inventory?.dora_hints ?? null}
        onOpenQuestionnaire={() => onGo("questionnaire")}
      />
      <MaturityPanel maturity={assessment.maturity} />
    </div>
  );
  if (assessment.inventory) return <Results assessment={assessment.inventory} insert={panels} nested />;
  return (
    <div className="space-y-12">
      <div className="border-l-4 border-accent bg-surface px-4 py-3 text-sm">
        <p className="font-medium">Noch kein IT-Bestand hochgeladen.</p>
        <p className="mt-1 text-ink-secondary">
          Heatmap, Roadmap und die DORA-Hinweise zu einzelnen Diensten folgen, sobald der
          IT-Bestand vorliegt.{" "}
          <button
            type="button"
            onClick={() => onGo("inventory")}
            className="underline hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
          >
            IT-Bestand hochladen
          </button>
        </p>
      </div>
      {panels}
    </div>
  );
}
