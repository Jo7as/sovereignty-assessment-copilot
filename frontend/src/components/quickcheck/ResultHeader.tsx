import type { QuickCheckResult } from "@/lib/types";

const format = (value: number) => value.toFixed(1).replace(".", ",");

// Einordnung der Gesamtstufe in Worten, angelehnt an die Stufen des Rahmenwerks
function verdict(level: number): { title: string; text: string } {
  if (level < 1)
    return {
      title: "Kaum Souveränität.",
      text: "Die erkannten Dienste stehen überwiegend unter Kontrolle von Konzernen außerhalb der EU, oder entscheidende Angaben fehlen.",
    };
  if (level < 2)
    return {
      title: "Geringe Souveränität.",
      text: "EU-Recht gilt meist nur formal, etwa über Rechenzentren in der EU. Die Kontrolle liegt außerhalb.",
    };
  if (level < 3)
    return {
      title: "Teilweise souverän.",
      text: "Daten bleiben in der EU, es gibt aber wesentliche Abhängigkeiten außerhalb.",
    };
  return { title: "Weitgehend souverän.", text: "Die erkannten Dienste stehen weitgehend unter EU-Kontrolle." };
}

// Kopf des Ergebnisses: Kernaussage, betroffene Dienste, Kennzahlen und Score-Karte
export default function ResultHeader({ result, seconds }: { result: QuickCheckResult; seconds: number }) {
  const { summary } = result;
  const shown = summary.outside_eu_names.slice(0, 6);
  const more = summary.outside_eu_names.length - shown.length;

  return (
    <header className="grid gap-10 lg:grid-cols-[1fr_22rem] lg:items-start">
      <div>
        <p className="text-sm text-ink-muted">
          <span className="font-medium text-accent">Analyse abgeschlossen</span>
          {seconds > 0 && ` · ${seconds} Sekunden`}
        </p>
        <h1 className="mt-2 font-mono text-3xl tracking-tight sm:text-4xl">{result.domain}</h1>
        {summary.recognized > 0 ? (
          <p className="mt-5 max-w-2xl text-balance text-3xl font-semibold tracking-tight">
            <span className="tabular text-critical">{summary.outside_eu}</span> von{" "}
            <span className="tabular">{summary.recognized}</span> erkannten Diensten unterliegen dem Recht eines Staates
            außerhalb der EU.
          </p>
        ) : (
          <p className="mt-5 max-w-2xl text-3xl font-semibold tracking-tight">
            Von außen ließ sich kein Dienst aus der Datenbank sicher erkennen.
          </p>
        )}
        {shown.length > 0 && (
          <ul className="mt-5 flex flex-wrap gap-2" aria-label="Dienste außerhalb der EU">
            {shown.map((name) => (
              <li key={name} className="rounded-full border border-critical/40 px-3 py-1 text-sm">
                <span className="mr-1.5 text-xs font-semibold text-critical">Nicht-EU</span>
                {name}
              </li>
            ))}
            {more > 0 && <li className="rounded-full border border-baseline px-3 py-1 text-sm">+{more} weitere</li>}
          </ul>
        )}
        <dl className="mt-6 flex flex-wrap gap-x-8 gap-y-2 text-sm">
          <div>
            <dt className="sr-only">Erkannte Dienste</dt>
            <dd>
              <span className="tabular text-xl font-semibold">{summary.recognized}</span>{" "}
              <span className="text-ink-secondary">erkannte Dienste</span>
            </dd>
          </div>
          <div>
            <dt className="sr-only">Außerhalb der EU</dt>
            <dd>
              <span className="tabular text-xl font-semibold text-critical">{summary.outside_eu}</span>{" "}
              <span className="text-ink-secondary">außerhalb der EU</span>
            </dd>
          </div>
          <div>
            <dt className="sr-only">Mit EU-Alternative</dt>
            <dd>
              <span className="tabular text-xl font-semibold text-accent">{summary.with_alternative}</span>{" "}
              <span className="text-ink-secondary">mit EU-Alternative in der Datenbank</span>
            </dd>
          </div>
        </dl>
      </div>

      {summary.level !== null && <ScoreCard result={result} />}
    </header>
  );
}

function ScoreCard({ result }: { result: QuickCheckResult }) {
  const level = result.summary.level ?? 0;
  const { title, text } = verdict(level);
  return (
    <aside aria-label="Gesamtstufe" className="rounded-lg border border-hairline bg-surface p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Gesamtstufe</p>
      <div className="mt-3 flex items-end gap-4">
        <p className="tabular text-6xl font-semibold leading-none tracking-tight">{format(level)}</p>
        <p className="pb-1 text-sm text-ink-secondary">von 4</p>
      </div>
      <ol className="mt-4 grid grid-cols-5 gap-1" aria-hidden>
        {[0, 1, 2, 3, 4].map((step) => (
          <li
            key={step}
            className="h-1.5 rounded-sm"
            style={{ background: step <= Math.floor(level) ? `var(--level-${step})` : "var(--hairline)" }}
          />
        ))}
      </ol>
      <p className="mt-4 text-sm font-medium">{title}</p>
      <p className="mt-1 text-sm text-ink-secondary">{text}</p>
      {result.summary.score !== null && (
        <p className="mt-4 border-t border-hairline pt-3 text-xs text-ink-muted">
          Souveränitätswert {result.summary.score} von 100, möglich {result.summary.potential_score}. Gewichtet nach
          Kritikalität der Dienste.
        </p>
      )}
    </aside>
  );
}
