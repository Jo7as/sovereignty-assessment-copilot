"use client";

import { useRef, useState } from "react";

import { ApiError, saveAnswers } from "./api";
import type { AnswerValue, StoredAssessment } from "./types";

export type SaveStatus = "idle" | "saving" | "saved" | "error";

/**
 * Antworten des Fragebogens, gespeichert bei jeder Änderung.
 *
 * Die Anzeige folgt sofort der Eingabe. Gespeichert wird nacheinander in einer
 * Warteschlange: Zwei schnelle Klicks auf dieselbe Frage könnten den Server sonst in
 * falscher Reihenfolge erreichen, und die ältere Antwort bliebe gespeichert.
 */
export function useAnswers(initial: StoredAssessment) {
  const [assessment, setAssessment] = useState(initial);
  const [answers, setAnswers] = useState<Record<string, AnswerValue>>(initial.answers);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [status, setStatus] = useState<SaveStatus>("idle");
  const queue = useRef<Promise<void>>(Promise.resolve());
  const pending = useRef(0);

  function save(key: string, value: AnswerValue | null) {
    setAnswers((previous) => {
      const next = { ...previous };
      if (value === null) delete next[key];
      else next[key] = value;
      return next;
    });
    pending.current += 1;
    setStatus("saving");
    queue.current = queue.current.then(async () => {
      try {
        const result = await saveAnswers(initial.id, { [key]: value });
        setAssessment(result);
        setErrors((previous) => {
          const next = { ...previous };
          delete next[key];
          return next;
        });
        pending.current -= 1;
        if (pending.current === 0) setStatus("saved");
      } catch (error) {
        const detail = error instanceof ApiError ? error.details.find((d) => d.question === key) : undefined;
        const message =
          detail?.message ?? (error instanceof ApiError ? error.message : "Speichern fehlgeschlagen.");
        setErrors((previous) => ({ ...previous, [key]: message }));
        pending.current -= 1;
        setStatus("error");
      }
    });
  }

  /** Fehler, der vor dem Speichern auffällt, etwa ein Buchstabe im Zahlenfeld. */
  function reject(key: string, message: string) {
    setErrors((previous) => ({ ...previous, [key]: message }));
  }

  /** Übernimmt einen neuen Stand vom Server, etwa nach dem Hochladen des IT-Bestands. */
  function replace(next: StoredAssessment) {
    setAssessment(next);
  }

  return { assessment, answers, errors, status, save, reject, replace };
}
