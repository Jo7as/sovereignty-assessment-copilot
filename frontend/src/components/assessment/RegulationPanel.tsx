import type { Assessment, Regime, StoredAssessment } from "@/lib/types";

import LegalBasis from "../questionnaire/LegalBasis";

const STATUS: Record<Regime["status"], { label: string; mark: string }> = {
  GILT: { label: "Gilt", mark: "●" },
  GILT_NICHT: { label: "Gilt nicht", mark: "○" },
  NICHT_BESTIMMBAR: { label: "Noch nicht bestimmbar", mark: "?" },
};

const ENTITY: Record<NonNullable<Regime["entity_class"]>, string> = {
  WESENTLICH: "wesentliche Einrichtung",
  WICHTIG: "wichtige Einrichtung",
};

interface Props {
  regulation: StoredAssessment["regulation"];
  doraHints: Assessment["dora_hints"] | null;
  onOpenQuestionnaire: () => void;
}

// Welches Recht gilt und welche Pflichten sind offen. Eine Vorprüfung, keine Rechtsberatung.
export default function RegulationPanel({ regulation, doraHints, onOpenQuestionnaire }: Props) {
  const inventoryHints = doraHints?.applies === false ? [] : (doraHints?.hints ?? []);
  const gaps = regulation.hints.length + inventoryHints.length;

  return (
    <section aria-labelledby="regulation-title">
      <h2 id="regulation-title" className="text-lg font-semibold">
        DORA und NIS2
      </h2>
      <p className="text-sm text-ink-secondary">
        Vorprüfung aus Fragebogen und IT-Bestand, jede Aussage mit Fundstelle im amtlichen
        Text. Keine Rechtsberatung.
      </p>

      <div className="mt-4 grid items-start gap-4 sm:grid-cols-2">
        {[regulation.dora, regulation.nis2].map((regime) => (
          <RegimeCard
            key={regime.law}
            regime={regime}
            superseded={regime.law === "NIS2" && regulation.dora_precedes_nis2}
          />
        ))}
      </div>

      <h3 className="mt-8 font-medium">Offene Pflichten ({gaps})</h3>
      {regulation.applicable_laws.length === 0 && (
        <p className="mt-2 text-sm text-ink-secondary">
          Solange weder DORA noch NIS2 gilt oder bestimmbar ist, leitet das Tool keine Pflichten ab.
        </p>
      )}

      <ul className="mt-2 divide-y divide-hairline">
        {regulation.hints.map((hint) => (
          <li key={hint.question} className="py-3 text-sm">
            <p>
              <span className="font-medium">{hint.severity === "LUECKE" ? "Lücke" : "Teilweise erfüllt"}:</span>{" "}
              {hint.text}
            </p>
            <p className="text-ink-secondary">Antwort im Fragebogen: {hint.answer}</p>
            <LegalBasis basis={hint.basis} />
          </li>
        ))}
        {inventoryHints.map((hint) => (
          <li key={`${hint.code}-${hint.group ?? ""}`} className="py-3 text-sm">
            <p>
              <span className="font-medium">Aus dem IT-Bestand:</span> {hint.title}
              {hint.group && ` (${hint.group})`}
            </p>
            <p className="text-ink-secondary">{hint.explanation}</p>
            <p className="mt-1 text-ink-secondary">
              {hint.services.length} {hint.services.length === 1 ? "Dienst" : "Dienste"}:{" "}
              {hint.services.join(", ")}
            </p>
            {doraHints?.applies === null && <p className="mt-1 text-xs text-ink-muted">{doraHints.condition}</p>}
            <LegalBasis basis={hint.basis} />
          </li>
        ))}
      </ul>

      {regulation.unanswered_obligations.length > 0 && (
        <p className="mt-3 text-sm text-ink-secondary">
          {regulation.unanswered_obligations.length} Pflichtfragen sind noch nicht beantwortet.{" "}
          <button
            type="button"
            onClick={onOpenQuestionnaire}
            className="underline hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
          >
            Zum Fragebogen
          </button>
        </p>
      )}
    </section>
  );
}

function RegimeCard({ regime, superseded }: { regime: Regime; superseded: boolean }) {
  const status = STATUS[regime.status];
  return (
    <div className="border border-hairline bg-surface p-4">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="font-medium">{regime.law}</h3>
        <span className="text-sm">
          <span aria-hidden className="mr-1 text-accent">
            {status.mark}
          </span>
          {status.label}
          {regime.entity_class && `, ${ENTITY[regime.entity_class]}`}
        </span>
      </div>
      {superseded && (
        <p className="mt-1 text-xs font-medium text-ink-secondary">DORA geht vor</p>
      )}
      <ul className="mt-2 space-y-1 text-sm text-ink-secondary">
        {regime.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      <LegalBasis basis={regime.basis} />
    </div>
  );
}
