"use client";

import { useState } from "react";

import type { AssessedService, Assessment } from "@/lib/types";

import Heatmap from "./Heatmap";
import KpiStrip from "./KpiStrip";
import QuestionCatalog from "./QuestionCatalog";
import Roadmap from "./Roadmap";
import ServiceDetail from "./ServiceDetail";
import UnmatchedList from "./UnmatchedList";

export default function Results({ assessment }: { assessment: Assessment }) {
  const [selected, setSelected] = useState<AssessedService | null>(null);
  const { inventory, portfolio } = assessment;
  const date = new Date(inventory.assessed_on).toLocaleDateString("de-DE");

  return (
    <div className="space-y-12">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{inventory.name}</h1>
        <p className="text-sm text-ink-secondary">
          {inventory.entries} Einträge im IT-Bestand, {assessment.services.length} Dienste bewertet am {date}
        </p>
      </div>

      {portfolio && (
        <KpiStrip portfolio={portfolio} services={assessment.services} unmatched={assessment.unmatched.length} />
      )}
      <Heatmap services={assessment.services} onSelect={setSelected} />
      <Roadmap roadmap={assessment.roadmap} />
      <QuestionCatalog questions={assessment.roadmap.questions} />
      <UnmatchedList unmatched={assessment.unmatched} />

      <ServiceDetail service={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
