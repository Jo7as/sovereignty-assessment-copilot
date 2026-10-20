"use client";

import { useId, useRef, useState } from "react";

import { API_URL, ApiError, type ProblemDetail, uploadInventory } from "@/lib/api";
import type { StoredAssessment } from "@/lib/types";
import ProblemList from "../ProblemList";

interface Props {
  assessment: StoredAssessment;
  onUploaded: (assessment: StoredAssessment) => void;
}

type State =
  | { kind: "idle" }
  | { kind: "uploading"; name: string }
  | { kind: "error"; message: string; details: ProblemDetail[] };

// IT-Bestand am Assessment speichern. Ein neuer Bestand ersetzt den alten.
export default function InventoryStep({ assessment, onUploaded }: Props) {
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);
  const [state, setState] = useState<State>({ kind: "idle" });
  const stored = assessment.inventory;

  async function upload(file: File) {
    setState({ kind: "uploading", name: file.name });
    try {
      onUploaded(await uploadInventory(assessment.id, file));
      setState({ kind: "idle" });
    } catch (error) {
      setState({
        kind: "error",
        message: error instanceof ApiError ? error.message : "Unbekannter Fehler.",
        details: error instanceof ApiError ? error.details : [],
      });
    }
  }

  return (
    <section aria-labelledby="inventory-title" className="max-w-3xl">
      <h2 id="inventory-title" className="text-xl font-semibold tracking-tight">
        IT-Bestand
      </h2>
      <p className="mt-1 text-sm text-ink-secondary">
        Die Liste Ihrer IT-Dienste mit Zweck und Kritikalität. Das Tool ordnet jeden Eintrag
        einem Dienst der Anbieterdatenbank zu. Einträge, die es nicht sicher erkennt, schlägt
        eine KI vor. Diese Vorschläge sind in der Heatmap markiert und müssen geprüft werden.
      </p>

      {stored && (
        <div className="mt-6 border-l-2 border-accent pl-4 text-sm">
          <p className="font-medium">{stored.inventory.name}</p>
          <p className="text-ink-secondary">
            Hochgeladen am {new Date(stored.inventory.uploaded_at).toLocaleString("de-DE")},{" "}
            {stored.inventory.entries} Einträge, {stored.services.length} Dienste zugeordnet,{" "}
            {stored.unmatched.length} offen
          </p>
        </div>
      )}

      {state.kind === "error" && (
        <div role="alert" className="mt-6 border-l-4 border-critical bg-surface px-4 py-3 text-sm">
          <p className="font-medium">Der IT-Bestand wurde nicht gespeichert.</p>
          <p className="mt-1 text-ink-secondary">{state.message}</p>
          <ProblemList details={state.details} />
        </div>
      )}

      <div className="mt-6 rounded-lg border border-hairline bg-surface p-5">
        {state.kind === "uploading" ? (
          <p role="status" aria-live="polite" className="text-sm">
            „{state.name}“ wird zugeordnet und bewertet. Mit KI-Zuordnung kann das bis zu einer
            Minute dauern.
          </p>
        ) : (
          <>
            <label htmlFor={inputId} className="sr-only">
              IT-Bestand als Excel- oder CSV-Datei auswählen
            </label>
            <input
              ref={input}
              id={inputId}
              type="file"
              accept=".xlsx,.csv"
              className="sr-only"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) upload(file);
                event.target.value = "";
              }}
            />
            <button
              type="button"
              onClick={() => input.current?.click()}
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              {stored ? "Neuen IT-Bestand hochladen" : "IT-Bestand hochladen"}
            </button>
            <p className="mt-3 text-xs text-ink-muted">
              Excel-Vorlage oder CSV-Datei, höchstens 5 MB.{" "}
              <a href={`${API_URL}/inventory/template`} className="underline">
                Excel-Vorlage herunterladen
              </a>
              {stored && " · Ein neuer Bestand ersetzt den bisherigen."}
            </p>
          </>
        )}
      </div>
    </section>
  );
}
