"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError, loadReport } from "@/lib/api";
import type { ReportResponse } from "@/lib/types";

import ReportDocument from "./ReportDocument";

// Seitengröße, Ränder und Fußzeile mit Seitenzahl. Bewusst hier und nicht in globals.css:
// Turbopack verwirft die Randfelder von @page (@bottom-left und Co.) beim Übersetzen von
// globals.css still und liefert dann die alte Fassung aus. Ein <style>-Element bleibt unberührt.
const PAGE_CSS = `
@page {
  size: A4;
  margin: 16mm 16mm 18mm;
  @bottom-left {
    content: "Sovereignty Assessment Copilot · Keine Rechtsberatung";
    font: 8pt system-ui, sans-serif;
    color: #6f6d68;
  }
  @bottom-right {
    content: "Seite " counter(page) " von " counter(pages);
    font: 8pt system-ui, sans-serif;
    color: #6f6d68;
  }
}

/* Deckblatt ohne Fußzeile */
@page :first {
  @bottom-left {
    content: none;
  }
  @bottom-right {
    content: none;
  }
}
`;

type State = { kind: "loading" } | { kind: "error"; message: string } | { kind: "ready"; data: ReportResponse };

// Bericht als Folge von A4-Blättern. „Als PDF speichern“ öffnet den Druckdialog des Browsers,
// die Druckansicht kommt aus PAGE_CSS und globals.css (.report-sheet).
export default function ReportView({ source, back }: { source: number | "demo"; back: string }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let active = true;
    loadReport(source)
      .then((data) => {
        if (!active) return;
        setState({ kind: "ready", data });
        // Der Dateiname beim Speichern als PDF kommt aus dem Titel der Seite
        document.title = `Sovereignty Assessment ${data.assessment.name}`;
      })
      .catch((error: unknown) => {
        if (active) setState({ kind: "error", message: error instanceof ApiError ? error.message : "Unbekannter Fehler." });
      });
    return () => {
      active = false;
    };
  }, [source]);

  return (
    <div className="report-light min-h-screen bg-[#e9e8e3] print:bg-white">
      <style href="report-page" precedence="default">
        {PAGE_CSS}
      </style>
      <div className="sticky top-0 z-10 mb-6 border-b border-hairline bg-surface print:hidden">
        <div className="mx-auto flex max-w-[210mm] items-center justify-between gap-4 px-4 py-3">
          <Link href={back} className="text-sm text-ink-secondary underline focus-visible:outline-2 focus-visible:outline-accent">
            Zurück zum Ergebnis
          </Link>
          <button
            type="button"
            onClick={() => window.print()}
            disabled={state.kind !== "ready"}
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-ink hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-60"
          >
            Als PDF speichern
          </button>
        </div>
      </div>
      {state.kind === "loading" && (
        <p role="status" aria-live="polite" className="py-24 text-center text-ink-secondary">
          Der Bericht wird erstellt …
        </p>
      )}
      {state.kind === "error" && (
        <div role="alert" className="mx-auto max-w-xl border-l-4 border-critical bg-surface px-4 py-3 text-sm">
          <p className="font-medium">Der Bericht ließ sich nicht erstellen.</p>
          <p className="mt-1 text-ink-secondary">{state.message}</p>
        </div>
      )}
      {state.kind === "ready" && <ReportDocument data={state.data} />}
    </div>
  );
}
