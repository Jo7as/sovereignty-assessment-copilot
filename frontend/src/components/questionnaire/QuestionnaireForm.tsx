"use client";

import { useRef, useState } from "react";

import type { SaveStatus } from "@/lib/use-answers";
import type { AnswerValue, Questionnaire } from "@/lib/types";

import QuestionField from "./QuestionField";

interface Props {
  questionnaire: Questionnaire;
  answers: Record<string, AnswerValue>;
  errors: Record<string, string>;
  status: SaveStatus;
  onSave: (key: string, value: AnswerValue | null) => void;
  onReject: (key: string, message: string) => void;
  onFinish: () => void;
}

const STATUS_TEXT: Record<SaveStatus, string> = {
  idle: "Antworten werden automatisch gespeichert.",
  saving: "Wird gespeichert …",
  saved: "Alle Antworten gespeichert.",
  error: "Eine Antwort wurde nicht gespeichert. Bitte die markierte Frage prüfen.",
};

// Fragebogen mit Abschnitten als Navigation. Auf dem Handy liegen die Abschnitte als
// waagerechte Leiste über den Fragen, ab mittlerer Breite als Spalte daneben.
export default function QuestionnaireForm({ questionnaire, answers, errors, status, onSave, onReject, onFinish }: Props) {
  const [current, setCurrent] = useState(0);
  const top = useRef<HTMLDivElement>(null);
  const { sections, questions } = questionnaire;
  const section = sections[current];
  const inSection = questions.filter((question) => question.section === section.key);
  const answered = questions.filter((question) => answers[question.key] !== undefined).length;

  function go(index: number) {
    setCurrent(index);
    top.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div ref={top} className="scroll-mt-4 md:grid md:grid-cols-[17rem_1fr] md:gap-10">
      <nav aria-label="Abschnitte des Fragebogens" className="md:sticky md:top-4 md:self-start">
        <p className="text-sm text-ink-secondary">
          <span className="tabular">{answered}</span> von <span className="tabular">{questions.length}</span>{" "}
          Fragen beantwortet
        </p>
        <div
          role="progressbar"
          aria-label="Fortschritt"
          aria-valuemin={0}
          aria-valuemax={questions.length}
          aria-valuenow={answered}
          className="mt-2 h-1 bg-hairline"
        >
          <div className="h-1 bg-accent" style={{ width: `${(answered / questions.length) * 100}%` }} />
        </div>
        <ol className="-mx-4 mt-4 flex gap-1 overflow-x-auto px-4 pb-2 md:mx-0 md:flex-col md:overflow-visible md:px-0">
          {sections.map((item, index) => {
            const keys = questions.filter((question) => question.section === item.key);
            const done = keys.filter((question) => answers[question.key] !== undefined).length;
            return (
              <li key={item.key} className="shrink-0">
                <button
                  type="button"
                  onClick={() => go(index)}
                  aria-current={index === current ? "step" : undefined}
                  className="flex w-full items-baseline justify-between gap-3 rounded px-3 py-2 text-left text-sm hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent aria-[current=step]:bg-surface aria-[current=step]:font-medium"
                >
                  <span className="whitespace-nowrap">{item.title}</span>
                  <span className="tabular text-xs text-ink-muted">
                    {done}/{keys.length}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </nav>

      <section aria-labelledby="section-title" className="mt-6 max-w-3xl md:mt-0">
        <h2 id="section-title" className="text-xl font-semibold tracking-tight">
          {section.title}
        </h2>
        <p role="status" aria-live="polite" className={`mt-1 text-sm ${status === "error" ? "text-critical" : "text-ink-muted"}`}>
          {STATUS_TEXT[status]}
        </p>

        <div className="mt-4">
          {inSection.map((question) => (
            <QuestionField
              key={question.key}
              question={question}
              number={questions.indexOf(question) + 1}
              value={answers[question.key]}
              error={errors[question.key]}
              onSave={(value) => onSave(question.key, value)}
              onReject={(message) => onReject(question.key, message)}
            />
          ))}
        </div>

        <div className="flex items-center justify-between border-t border-hairline pt-6">
          {current > 0 ? (
            <button
              type="button"
              onClick={() => go(current - 1)}
              className="rounded border border-baseline px-4 py-2 text-sm hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent"
            >
              Zurück
            </button>
          ) : (
            <span />
          )}
          {current < sections.length - 1 ? (
            <button
              type="button"
              onClick={() => go(current + 1)}
              className="rounded bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              Weiter: {sections[current + 1].title}
            </button>
          ) : (
            <div className="flex flex-col items-end gap-2 text-right">
              <button
                type="button"
                onClick={onFinish}
                className="rounded bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Weiter: IT-Bestand
              </button>
              <p className="text-xs text-ink-muted">
                {answered === questions.length
                  ? "Alle Fragen beantwortet."
                  : `Noch ${questions.length - answered} ${questions.length - answered === 1 ? "Frage" : "Fragen"} offen. Sie können später weitermachen.`}
              </p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
