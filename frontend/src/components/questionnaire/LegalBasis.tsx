import type { LegalBasis as Basis } from "@/lib/types";

const LAW_NAMES: Record<Basis["law"], string> = {
  DORA: "DORA",
  NIS2: "NIS2",
  KMU: "KMU-Empfehlung",
};

// Rechtsgrundlage einer Frage, aufklappbar, mit wörtlicher Fundstelle aus dem amtlichen Text
export default function LegalBasis({ basis }: { basis: Basis[] }) {
  if (basis.length === 0) return null;
  const summary = basis.map((item) => `${LAW_NAMES[item.law]} ${item.article}`).join(", ");

  return (
    <details className="group mt-3 text-sm">
      <summary className="cursor-pointer text-ink-secondary hover:text-ink focus-visible:outline-2 focus-visible:outline-accent">
        Rechtsgrundlage: {summary}
      </summary>
      <ul className="mt-2 space-y-3 border-l-2 border-hairline pl-4">
        {basis.map((item) => (
          <li key={`${item.law}-${item.article}-${item.quote.slice(0, 20)}`}>
            <p className="font-medium">
              {LAW_NAMES[item.law]} {item.article}
            </p>
            <blockquote className="mt-1 text-ink-secondary">„{item.quote}“</blockquote>
            <p className="mt-1 text-xs text-ink-muted">
              <a href={item.source} target="_blank" rel="noreferrer" className="underline">
                Amtlicher Text
              </a>{" "}
              (Amt für Veröffentlichungen der EU), abgerufen am{" "}
              {new Date(item.retrieved).toLocaleDateString("de-DE")}
            </p>
          </li>
        ))}
      </ul>
    </details>
  );
}
