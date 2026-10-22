import type { QuickCheckResult } from "@/lib/types";

import LevelLegend from "../LevelLegend";
import Handover from "./Handover";
import Levers from "./Levers";
import OtherFindings from "./OtherFindings";
import ProfileCard from "./ProfileCard";
import ResultHeader from "./ResultHeader";
import ServiceTable from "./ServiceTable";
import Signals from "./Signals";

// Ergebnis des Schnellchecks, aufgebaut wie ein Bericht: Kernaussage, Hebel, Unternehmen,
// alle Dienste mit Eigentümer und Alternative, technische Signale, übrige Funde, Übergang
export default function QuickCheckResults({ result, seconds }: { result: QuickCheckResult; seconds: number }) {
  const business = result.services.filter((service) => service.group === "UNTERNEHMEN");
  const website = result.services.filter((service) => service.group === "WEBSITE");

  return (
    <div className="space-y-14">
      <ResultHeader result={result} seconds={seconds} />
      <Levers levers={result.levers} />
      <ProfileCard result={result} />
      <div className="space-y-10">
        <ServiceTable
          id="business-title"
          title="Unternehmensdienste"
          intro="Erkannt über E-Mail, Domain und Hosting. Sie verarbeiten oft Daten des Unternehmens."
          services={business}
        />
        <ServiceTable
          id="website-title"
          title="Website-Werkzeuge"
          intro="Nur auf der Website gefunden, etwa Statistik oder Werbung. Meist mit geringer Kritikalität."
          services={website}
        />
        {result.services.length > 0 && <LevelLegend />}
      </div>
      <Signals result={result} />
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
