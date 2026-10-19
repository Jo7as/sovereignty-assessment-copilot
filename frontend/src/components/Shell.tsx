import Link from "next/link";
import type { ReactNode } from "react";

// Kopf- und Fußzeile für alle Seiten. `actions` steht rechts im Kopf.
export default function Shell({ children, actions }: { children: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-4 sm:px-6 lg:px-8">
      <header className="flex items-baseline justify-between gap-4 border-b border-hairline py-5">
        <div>
          <Link
            href="/"
            className="text-xs font-medium uppercase tracking-wide text-ink-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
          >
            Sovereignty Assessment Copilot
          </Link>
          <p className="text-sm text-ink-secondary">
            Abhängigkeit von IT-Anbietern außerhalb der EU, bewertet nach dem EU Cloud
            Sovereignty Framework
          </p>
        </div>
        {actions}
      </header>

      <main className="flex-1 py-8">{children}</main>

      <footer className="border-t border-hairline py-5 text-xs text-ink-muted">
        Prototyp für ein Bewerbungsprojekt. Keine Rechtsberatung. Die Angaben zu den
        Anbietern stammen aus öffentlichen Quellen und sind je Dienst belegt. Ob eine
        Angabe von der KI nachgeprüft oder von einem Menschen bestätigt wurde, steht in
        der Detailansicht.
      </footer>
    </div>
  );
}
