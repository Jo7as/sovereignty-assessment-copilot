import type { QuickCheckResult } from "@/lib/types";

import LevelLegend from "../LevelLegend";
import Handover from "./Handover";
import OtherFindings from "./OtherFindings";
import ProfileCard from "./ProfileCard";
import ServiceList from "./ServiceList";

// Ergebnis des Schnellchecks: Kernaussage, Profil, erkannte Dienste, übrige Funde, Übergang
export default function QuickCheckResults({ result, seconds }: { result: QuickCheckResult; seconds: number }) {
  const business = result.services.filter((service) => service.group === "UNTERNEHMEN");
  const website = result.services.filter((service) => service.group === "WEBSITE");
  const weak = result.services.filter((service) => service.level <= 1).length;

  return (
    <div className="space-y-12">
      <header>
        <p className="text-sm text-ink-muted">
          Schnellcheck abgeschlossen{seconds > 0 && ` in ${seconds} Sekunden`}
        </p>
        <h1 className="mt-1 font-mono text-3xl tracking-tight">{result.domain}</h1>
        {result.services.length > 0 ? (
          <p className="mt-4 max-w-3xl text-2xl font-semibold tracking-tight">
            <span className="tabular">{weak}</span> von <span className="tabular">{result.services.length}</span> erkannten
            Diensten stehen auf Stufe 0 oder 1.
          </p>
        ) : (
          <p className="mt-4 max-w-3xl text-2xl font-semibold tracking-tight">
            Von außen ließ sich kein Dienst aus der Datenbank sicher erkennen.
          </p>
        )}
        <p className="mt-2 max-w-3xl text-sm text-ink-secondary">
          Stufe 0 und 1 heißt: Die Kontrolle liegt bei einem Konzern außerhalb der EU, oder entscheidende Angaben fehlen.
          Fehlende Angaben zählen wie der ungünstigste Fall. Jeder Fund ist mit Quelle belegt.
        </p>
      </header>

      <ProfileCard result={result} />

      <div className="space-y-10">
        <ServiceList
          id="business-title"
          title="Unternehmensdienste"
          intro="Erkannt über E-Mail, Domain und Hosting. Sie verarbeiten oft Daten des Unternehmens."
          services={business}
        />
        <ServiceList
          id="website-title"
          title="Website-Werkzeuge"
          intro="Nur auf der Website gefunden, etwa Statistik oder Werbung. Meist mit geringer Kritikalität."
          services={website}
        />
        {result.services.length > 0 && <LevelLegend />}
      </div>

      <OtherFindings findings={result.other_findings} />

      {result.problems.length > 0 && (
        <section aria-labelledby="problems-title" className="text-sm">
          <h2 id="problems-title" className="font-medium">
            Hinweise zum Scan
          </h2>
          <ul className="mt-2 space-y-1 text-ink-secondary">
            {result.problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        </section>
      )}

      <Handover result={result} />
    </div>
  );
}
