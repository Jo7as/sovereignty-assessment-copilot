"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { startQuickCheck } from "@/lib/api";
import type { QuickCheckResult } from "@/lib/types";

import Shell from "../Shell";
import QuickCheckResults from "./QuickCheckResults";
import ScanProgress from "./ScanProgress";

type State =
  | { kind: "running"; steps: string[]; current: string | null }
  | { kind: "done"; result: QuickCheckResult; seconds: number }
  | { kind: "error"; message: string };

export default function QuickCheckView({ domain }: { domain: string }) {
  const [state, setState] = useState<State>({ kind: "running", steps: [], current: null });
  const started = useRef(0);

  useEffect(() => {
    // Kein Zurücksetzen nötig: Die Seite setzt die Domain als key, bei neuer Domain entsteht die
    // Komponente neu
    started.current = Date.now();
    return startQuickCheck(domain, {
      onPlan: (steps) => setState((previous) => (previous.kind === "running" ? { ...previous, steps } : previous)),
      onStep: (step) => setState((previous) => (previous.kind === "running" ? { ...previous, current: step } : previous)),
      onResult: (result) =>
        setState({ kind: "done", result, seconds: Math.round((Date.now() - started.current) / 1000) }),
      onError: (message) => setState({ kind: "error", message }),
    });
  }, [domain]);

  return (
    <Shell
      actions={
        <Link
          href="/"
          className="rounded-md border border-baseline px-3 py-1.5 text-sm hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent"
        >
          Andere Website prüfen
        </Link>
      }
    >
      {state.kind === "running" && <ScanProgress domain={domain} steps={state.steps} current={state.current} />}
      {state.kind === "error" && (
        <div role="alert" className="mx-auto max-w-xl rounded-lg border-l-4 border-critical bg-surface px-4 py-3 text-sm">
          <p className="font-medium">Der Schnellcheck für „{domain}“ hat nicht geklappt.</p>
          <p className="mt-1 text-ink-secondary">{state.message}</p>
          <Link href="/" className="mt-3 inline-block underline">
            Zurück zur Startseite
          </Link>
        </div>
      )}
      {state.kind === "done" && <QuickCheckResults result={state.result} seconds={state.seconds} />}
    </Shell>
  );
}
