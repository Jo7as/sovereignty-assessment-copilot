import Link from "next/link";
import type { ReactNode } from "react";

import Logo from "./Logo";

interface Props {
  children: ReactNode;
  actions?: ReactNode; // rechts im Kopf
  wide?: boolean; // Startseite: Abschnitte gestalten ihre Breite selbst
}

// Kopf- und Fußzeile für alle Seiten
export default function Shell({ children, actions, wide = false }: Props) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-hairline">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <Link
            href="/"
            className="flex items-center gap-2.5 rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-accent"
          >
            <Logo />
            <span className="text-sm font-semibold tracking-tight">Sovereignty Assessment Copilot</span>
          </Link>
          {actions}
        </div>
      </header>

      <main className={wide ? "flex-1" : "mx-auto w-full max-w-7xl flex-1 px-4 py-8 sm:px-6 lg:px-8"}>
        {children}
      </main>

      <footer className="border-t border-hairline">
        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 text-xs text-ink-muted sm:grid-cols-[2fr_1fr] sm:px-6 lg:px-8">
          <p>
            Prototyp aus einem Bewerbungsprojekt. Keine Rechtsberatung. Die Angaben zu den
            Anbietern stammen aus öffentlichen Quellen und sind je Dienst belegt. Ob eine Angabe
            von der KI nachgeprüft oder von einem Menschen bestätigt wurde, steht in der
            Detailansicht.
          </p>
          <p className="sm:text-right">
            Bewertet nach dem Cloud Sovereignty Framework der EU-Kommission (Version 1.2.1),
            DORA und NIS2. Ohne Tracker und ohne nachgeladene Schriften.
          </p>
        </div>
      </footer>
    </div>
  );
}
