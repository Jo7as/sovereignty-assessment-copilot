"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";

// Website eingeben und den Schnellcheck starten
export default function DomainForm({ label = "Jetzt prüfen" }: { label?: string }) {
  const router = useRouter();
  const inputId = useId();
  const errorId = `${inputId}-error`;
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        const domain = value.trim();
        if (!domain.includes(".")) {
          setError("Bitte eine Website eingeben, etwa musterbank.de.");
          return;
        }
        router.push(`/schnellcheck?domain=${encodeURIComponent(domain)}`);
      }}
      className="w-full max-w-xl"
    >
      <label htmlFor={inputId} className="block text-sm font-medium">
        Website Ihres Unternehmens
      </label>
      <div className="mt-2 flex flex-col gap-2 sm:flex-row">
        <input
          id={inputId}
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            setError(null);
          }}
          inputMode="url"
          autoComplete="url"
          spellCheck={false}
          placeholder="musterbank.de"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? errorId : undefined}
          className="min-w-0 flex-1 rounded-md border border-baseline bg-surface px-4 py-3 text-base placeholder:text-ink-muted focus-visible:outline-2 focus-visible:outline-accent"
        />
        <button
          type="submit"
          className="rounded-md bg-accent px-5 py-3 text-base font-medium text-accent-ink hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          {label}
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
