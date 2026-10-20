"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { ApiError, createAssessment } from "@/lib/api";

// Assessment anlegen und zur Seite des Assessments wechseln
export default function CreateAssessmentForm({ label = "Assessment starten" }: { label?: string }) {
  const router = useRouter();
  const nameId = useId();
  const errorId = `${nameId}-error`;
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const assessment = await createAssessment(name.trim());
      router.push(`/assessments/${assessment.id}`);
    } catch (problem) {
      setError(problem instanceof ApiError ? problem.message : "Unbekannter Fehler.");
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
      className="w-full max-w-xl"
    >
      <label htmlFor={nameId} className="block text-sm font-medium">
        Name des Unternehmens
      </label>
      <div className="mt-2 flex flex-col gap-2 sm:flex-row">
        <input
          id={nameId}
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={200}
          required
          placeholder="z. B. Musterbank AG"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
          className="min-w-0 flex-1 rounded-md border border-baseline bg-surface px-4 py-3 text-base placeholder:text-ink-muted focus-visible:outline-2 focus-visible:outline-accent"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-md bg-accent px-5 py-3 text-base font-medium text-accent-ink hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
        >
          {busy ? "Wird angelegt …" : label}
        </button>
      </div>
      {error && (
        <p id={errorId} role="alert" className="mt-2 text-sm text-critical">
          {error}
        </p>
      )}
    </form>
  );
}
