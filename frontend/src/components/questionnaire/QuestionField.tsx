"use client";

import { useId, useState } from "react";

import type { AnswerValue, QuestionnaireQuestion } from "@/lib/types";

import LegalBasis from "./LegalBasis";

interface Props {
  question: QuestionnaireQuestion;
  number: number;
  value: AnswerValue | undefined;
  error: string | undefined;
  onSave: (value: AnswerValue | null) => void;
  onReject: (message: string) => void;
}

// Eine Frage: Auswahl als Optionsfelder, Zahl als Eingabefeld. Gespeichert wird bei
// Auswahl sofort, bei Zahlen beim Verlassen des Felds oder mit Enter.
export default function QuestionField({ question, number, value, error, onSave, onReject }: Props) {
  const id = useId();
  const helpId = `${id}-help`;
  const errorId = `${id}-error`;
  const described = [question.help && helpId, error && errorId].filter(Boolean).join(" ") || undefined;

  return (
    <fieldset className="border-t border-hairline py-6" aria-describedby={described}>
      <legend className="float-left w-full font-medium">
        <span className="tabular mr-2 text-ink-muted">{number}.</span>
        {question.text}
      </legend>
      <div className="clear-both" />
      {question.help && (
        <p id={helpId} className="mt-1 text-sm text-ink-secondary">
          {question.help}
        </p>
      )}

      {question.type === "SINGLE" ? (
        // Lange Listen wie die Sektoren in zwei Spalten, damit sie nicht über mehrere Bildschirme laufen
        <div className={`mt-3 grid gap-2 ${question.options.length > 6 ? "sm:grid-cols-2" : ""}`}>
          {question.options.map((option) => (
            <label
              key={option.value}
              className="flex cursor-pointer items-start gap-3 rounded-md border border-hairline px-3 py-2 text-sm hover:border-baseline has-[:checked]:border-accent has-[:checked]:bg-page has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent"
            >
              <input
                type="radio"
                name={question.key}
                value={option.value}
                checked={value === option.value}
                onChange={() => onSave(option.value)}
                className="mt-0.5 accent-[var(--accent)]"
              />
              <span>{option.label}</span>
            </label>
          ))}
        </div>
      ) : (
        <NumberInput question={question} value={value} invalid={Boolean(error)} errorId={errorId} onSave={onSave} onReject={onReject} />
      )}

      <div className="mt-2 flex items-center gap-4 text-sm">
        {error && (
          <p id={errorId} role="alert" className="text-critical">
            {error}
          </p>
        )}
        {value !== undefined && question.type === "SINGLE" && (
          <button
            type="button"
            onClick={() => onSave(null)}
            className="text-ink-muted underline hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
          >
            Antwort entfernen
          </button>
        )}
      </div>

      <LegalBasis basis={question.basis} />
    </fieldset>
  );
}

function NumberInput({
  question,
  value,
  invalid,
  errorId,
  onSave,
  onReject,
}: Pick<Props, "question" | "value" | "onSave" | "onReject"> & { invalid: boolean; errorId: string }) {
  const [text, setText] = useState(value === undefined ? "" : String(value).replace(".", ","));

  function commit() {
    const trimmed = text.trim();
    if (trimmed === "") {
      if (value !== undefined) onSave(null);
      return;
    }
    // Nur das Komma ist Dezimalzeichen, ein Punkt wird abgelehnt: „1.500“ hieße sonst
    // still 1,5 statt 1500
    if (!/^\d+(,\d+)?$/.test(trimmed)) {
      onReject("Bitte eine Zahl ab 0 ohne Punkte eingeben, mit Komma als Dezimalzeichen, etwa 1500 oder 42,5.");
      return;
    }
    const number = Number(trimmed.replace(",", "."));
    // Auch bei gleichem Wert speichern, wenn vorher ein Fehler angezeigt wurde: Das räumt ihn ab
    if (number !== value || invalid) onSave(number);
  }

  return (
    <div className="mt-3 flex items-center gap-2">
      <input
        type="text"
        inputMode="decimal"
        aria-label={question.text}
        aria-invalid={invalid}
        aria-errormessage={invalid ? errorId : undefined}
        value={text}
        onChange={(event) => setText(event.target.value)}
        onBlur={commit}
        onKeyDown={(event) => {
          if (event.key === "Enter") commit();
        }}
        className="tabular w-40 rounded-md border border-baseline bg-page px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-accent aria-[invalid=true]:border-critical"
      />
      {question.unit && <span className="text-sm text-ink-secondary">{question.unit}</span>}
    </div>
  );
}
