import type { StoredAssessment } from "@/lib/types";

const format = (value: number) => value.toFixed(1).replace(".", ",");
const MAX = 4;

// Reifegrad je Handlungsfeld: Balken bis zum gesicherten Wert, hellere Verlängerung bis zum
// möglichen. Die Werte stehen als Text daneben, die Farbe trägt keine Information allein.
export default function MaturityPanel({ maturity }: { maturity: StoredAssessment["maturity"] }) {
  const open = maturity.dimensions.some((dimension) => dimension.answered < dimension.total);

  return (
    <section aria-labelledby="maturity-title">
      <h2 id="maturity-title" className="text-lg font-semibold">
        Reifegrad des Unternehmens
      </h2>
      <p className="text-sm text-ink-secondary">
        Wie gut das Unternehmen seine Abhängigkeit von Anbietern steuert, aus dem Fragebogen,
        Skala 0 bis 4. Unabhängig von den Stufen der Anbieter.
      </p>

      <p className="mt-4">
        <span className="text-2xl font-semibold">{format(maturity.secured)}</span>
        <span className="text-sm text-ink-secondary">
          {" "}
          von 4{open && `, möglich ${format(maturity.possible)}`}
        </span>
      </p>

      <ul className="mt-4 space-y-4">
        {maturity.dimensions.map((dimension) => (
          <li key={dimension.key}>
            <div className="flex items-baseline justify-between gap-4 text-sm">
              <span>{dimension.label}</span>
              <span className="tabular text-ink-secondary">
                {format(dimension.secured)}
                {dimension.possible > dimension.secured && ` bis ${format(dimension.possible)}`}
              </span>
            </div>
            <div
              className="relative mt-1 h-2 rounded-sm bg-hairline"
              role="img"
              aria-label={`${dimension.label}: gesichert ${format(dimension.secured)}, möglich ${format(dimension.possible)} von 4`}
            >
              <div
                className="absolute inset-y-0 left-0 rounded-sm bg-accent opacity-30"
                style={{ width: `${(dimension.possible / MAX) * 100}%` }}
              />
              <div
                className="absolute inset-y-0 left-0 rounded-sm bg-accent"
                style={{ width: `${(dimension.secured / MAX) * 100}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-ink-muted">
              {dimension.answered} von {dimension.total} Fragen beantwortet
            </p>
          </li>
        ))}
      </ul>

      {open && (
        <p className="mt-4 flex items-center gap-2 text-xs text-ink-muted">
          <span className="inline-block h-2 w-4 rounded-sm bg-accent" aria-hidden /> gesichert
          <span className="ml-3 inline-block h-2 w-4 rounded-sm bg-accent opacity-30" aria-hidden />{" "}
          möglich, wenn offene Fragen günstig beantwortet werden
        </p>
      )}
    </section>
  );
}
