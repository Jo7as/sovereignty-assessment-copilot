import type { LegalBasis, Regime, ReportResponse } from "@/lib/types";

import MaturityPanel from "../assessment/MaturityPanel";
import { Sheet, SheetTitle } from "./Sheet";

const STATUS: Record<Regime["status"], string> = {
  GILT: "Gilt",
  GILT_NICHT: "Gilt nicht",
  NICHT_BESTIMMBAR: "Noch nicht bestimmbar",
};
const ENTITY: Record<string, string> = { WESENTLICH: "wesentliche Einrichtung", WICHTIG: "wichtige Einrichtung" };

function Basis({ items }: { items: LegalBasis[] }) {
  return (
    <ul className="mt-1 space-y-1 text-[10px] text-ink-muted">
      {items.map((item) => (
        <li key={`${item.law}-${item.article}`}>
          {item.law} {item.article}: „{item.quote}“
        </li>
      ))}
    </ul>
  );
}

function RegimeBlock({ regime }: { regime: Regime }) {
  const entity = regime.entity_class ? `, ${ENTITY[regime.entity_class]}` : "";
  return (
    <div className="break-inside-avoid rounded-md border border-hairline px-3 py-2">
      <p className="font-semibold">
        {regime.law}: {STATUS[regime.status]}
        {entity}
      </p>
      {regime.reasons.map((reason) => (
        <p key={reason} className="mt-0.5 text-ink-secondary">
          {reason}
        </p>
      ))}
      <Basis items={regime.basis} />
    </div>
  );
}

// Rechtslage mit Fundstellen aus dem amtlichen Text, DORA-Hinweise aus dem IT-Bestand, Reifegrad
export default function RegulationPage({ data }: { data: ReportResponse }) {
  const { regulation, maturity, inventory } = data.assessment;
  const hints = inventory.dora_hints;
  return (
    <Sheet label="Rechtslage und Reifegrad">
      <SheetTitle eyebrow="4 · Rechtslage">Rechtslage und Reifegrad</SheetTitle>
      <p>{data.report.regulation}</p>
      <p className="mt-1 text-[11px] text-ink-muted">Vorprüfung aus Fragebogen und IT-Bestand, keine Rechtsberatung.</p>

      {regulation && (
        <div className="mt-4 grid grid-cols-2 gap-3">
          <RegimeBlock regime={regulation.dora} />
          <RegimeBlock regime={regulation.nis2} />
        </div>
      )}

      {hints.applies !== false && hints.hints.length > 0 && (
        <>
          <h3 className="mt-6 text-sm font-semibold">Hinweise zu DORA aus dem IT-Bestand</h3>
          <p className="text-[11px] text-ink-secondary">{hints.condition}</p>
          <ul className="mt-2 space-y-2">
            {hints.hints.map((hint) => (
              <li key={`${hint.code}-${hint.group ?? ""}`} className="break-inside-avoid border-l-2 border-critical pl-3">
                <p className="font-medium">{hint.title}</p>
                <p className="text-ink-secondary">{hint.explanation}</p>
                <p className="mt-0.5 text-[11px]">
                  {hint.services.length} {hint.services.length === 1 ? "Dienst" : "Dienste"}: {hint.services.join(", ")}
                </p>
                <Basis items={hint.basis} />
              </li>
            ))}
          </ul>
        </>
      )}

      <div className="mt-6 break-inside-avoid">
        {maturity ? (
          <MaturityPanel maturity={maturity} />
        ) : (
          <>
            <h3 className="text-sm font-semibold">Reifegrad des Unternehmens</h3>
            <p className="text-ink-secondary">
              Der Reifegrad stammt aus dem Fragebogen, etwa zu Exit-Plänen, Notfallplanung und Steuerung der Anbieter.
              In diesem Beispiel ist der Fragebogen nicht beantwortet.
            </p>
          </>
        )}
      </div>
    </Sheet>
  );
}
