import { LEVELS } from "@/lib/labels";
import type { AssessedService, Portfolio } from "@/lib/types";

interface Props {
  portfolio: Portfolio;
  services: AssessedService[];
  unmatched: number;
}

function Tile({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="border-l-2 border-accent pl-4">
      <dt className="text-xs text-ink-muted">{label}</dt>
      <dd className="mt-1 text-3xl font-semibold tracking-tight">{value}</dd>
      <dd className="mt-1 text-xs text-ink-secondary">{detail}</dd>
    </div>
  );
}

export default function KpiStrip({ portfolio, services, unmatched }: Props) {
  const weakest = portfolio.weakest_critical_level;
  return (
    <section aria-labelledby="kpi-title">
      <h2 id="kpi-title" className="sr-only">Kennzahlen</h2>
      <dl className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <Tile
          label="Souveränitätswert, gewichtet nach Kritikalität"
          value={`${Math.round(portfolio.score)} von 100`}
          detail={`Möglich ${Math.round(portfolio.potential_score)}, wenn fehlende Angaben günstig ausfallen`}
        />
        <Tile
          label="Durchschnittliche Gesamtstufe"
          value={portfolio.level.toFixed(1).replace(".", ",")}
          detail={`Möglich ${portfolio.potential.toFixed(1).replace(".", ",")}, Skala 0 bis 4`}
        />
        <Tile
          label="Schwächster Dienst mit hoher Kritikalität"
          value={weakest === null ? "keiner" : `Stufe ${weakest}`}
          detail={
            weakest === null
              ? "Kein Dienst mit hoher Kritikalität"
              : `${LEVELS[weakest].name}, betrifft ${portfolio.weakest_critical_services.length} Dienste`
          }
        />
        <Tile
          label="Offene Punkte"
          value={`${portfolio.provisional_services} von ${services.length}`}
          detail={`Dienste mit fehlenden Angaben, dazu ${unmatched} nicht zugeordnete Einträge`}
        />
      </dl>
    </section>
  );
}
