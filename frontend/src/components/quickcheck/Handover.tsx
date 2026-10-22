"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { ApiError, createFromScan } from "@/lib/api";
import type { QuickCheckResult } from "@/lib/types";

import { shortTitle } from "./ProfileCard";

const INVISIBLE = [
  "Kernsysteme wie Kernbank, ERP oder Meldewesen",
  "Backup, Rechenzentrum und interne Anwendungen",
  "Verträge und Varianten, etwa EU-Mandant oder eigene Schlüssel",
  "Exit-Pläne, Notfallplanung und Steuerung der Anbieter",
  "Welche Pflichten aus DORA und NIS2 offen sind",
];

// Übergang vom Schnellcheck ins Assessment mit Startbestand und Vorschlägen
export default function Handover({ result }: { result: QuickCheckResult }) {
  const router = useRouter();
  const nameId = useId();
  const imprint = result.profile.imprint;
  const fromTitle = shortTitle(result.title);
  const [name, setName] = useState(imprint.legal_name?.value ?? (fromTitle || result.domain));
  const [chosen, setChosen] = useState(() => new Set(result.services.map((service) => service.service)));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy(true);
    setError(null);
    const { entity, parent } = result.profile;
    try {
      const assessment = await createFromScan({
        name: name.trim() || result.domain,
        domain: result.domain,
        services: [...chosen],
        sector: result.suggestions.sector,
        employees: result.suggestions.employees,
        profile: {
          legal_name: imprint.legal_name?.value ?? null,
          register_number: imprint.register ? `${imprint.register.kind} ${imprint.register.number}` : null,
          lei: entity?.lei ?? null,
          parent: parent?.name ?? null,
          parent_country: parent?.country ?? null,
          supervision: Boolean(imprint.supervision),
          imprint_url: result.profile.imprint_url,
        },
      });
      router.push(`/assessments/${assessment.id}`);
    } catch (problem) {
      setError(problem instanceof ApiError ? problem.message : "Unbekannter Fehler.");
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="handover-title" className="grid gap-8 rounded-lg border-2 border-accent bg-surface p-6 lg:grid-cols-2">
      <div>
        <h2 id="handover-title" className="text-xl font-semibold tracking-tight">
          Was von außen nicht sichtbar ist
        </h2>
        <p className="mt-1 text-sm text-ink-secondary">
          Der Außenscan sieht nur, was ein Unternehmen nach außen zeigt. Die kritischen Abhängigkeiten liegen meist dahinter:
        </p>
        <ul className="mt-3 space-y-1.5 text-sm">
          {INVISIBLE.map((item) => (
            <li key={item} className="flex gap-2">
              <span aria-hidden className="text-ink-muted">–</span>
              {item}
            </li>
          ))}
        </ul>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          start();
        }}
      >
        <h3 className="font-semibold">Vollständiges Assessment starten</h3>
        <p className="mt-1 text-sm text-ink-secondary">
          Die gewählten Dienste werden zum Startbestand, die Vorschläge stehen im Fragebogen zur Bestätigung bereit.
        </p>
        <label htmlFor={nameId} className="mt-4 block text-sm font-medium">
          Name des Unternehmens
        </label>
        <input
          id={nameId}
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={200}
          className="mt-1 w-full rounded-md border border-baseline bg-page px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-accent"
        />
        {result.services.length > 0 && (
          <fieldset className="mt-4">
            <legend className="text-sm font-medium">In den Startbestand übernehmen</legend>
            <div className="mt-2 grid gap-1 sm:grid-cols-2">
              {result.services.map((service) => (
                <label key={service.service} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={chosen.has(service.service)}
                    onChange={(event) => {
                      const next = new Set(chosen);
                      if (event.target.checked) next.add(service.service);
                      else next.delete(service.service);
                      setChosen(next);
                    }}
                    className="accent-[var(--accent)]"
                  />
                  {service.name}
                </label>
              ))}
            </div>
          </fieldset>
        )}
        {error && (
          <p role="alert" className="mt-3 text-sm text-critical">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="mt-5 rounded-md bg-accent px-5 py-2.5 text-sm font-medium text-accent-ink hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
        >
          {busy ? "Wird angelegt …" : "Assessment starten"}
        </button>
      </form>
    </section>
  );
}
