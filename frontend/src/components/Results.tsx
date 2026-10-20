"use client";

import { type ReactNode, useState } from "react";

import type { AssessedService, Assessment } from "@/lib/types";

import Heatmap from "./Heatmap";
import KpiStrip from "./KpiStrip";
import QuestionCatalog from "./QuestionCatalog";
import Roadmap from "./Roadmap";
import ServiceDetail from "./ServiceDetail";
import UnmatchedList from "./UnmatchedList";

interface Props {
  assessment: Assessment;
  // erscheint zwischen Kennzahlen und Heatmap, etwa Rechtslage und Reifegrad
  insert?: ReactNode;
  // innerhalb eines Assessments: Die Seite hat schon eine Hauptüberschrift
  nested?: boolean;
}

export default function Results({ assessment, insert, nested = false }: Props) {
  const [selected, setSelected] = useState<AssessedService | null>(null);
  const { inventory, portfolio } = assessment;
  const date = new Date(inventory.assessed_on).toLocaleDateString("de-DE");

  return (
    <div className="space-y-12">
      <div>
        {nested ? (
          <h2 className="text-xl font-semibold tracking-tight">IT-Bestand „{inventory.name}“</h2>
        ) : (
          <h1 className="text-3xl font-semibold tracking-tight">{inventory.name}</h1>
        )}
        <p className="text-sm text-ink-secondary">
          {inventory.entries} Einträge im IT-Bestand, {assessment.services.length} Dienste bewertet am {date}
        </p>
      </div>

      {portfolio && (
        <KpiStrip portfolio={portfolio} services={assessment.services} unmatched={assessment.unmatched.length} />
      )}
      {insert}
      <Heatmap services={assessment.services} onSelect={setSelected} />
      <Roadmap roadmap={assessment.roadmap} />
      <QuestionCatalog questions={assessment.roadmap.questions} />
      <UnmatchedList unmatched={assessment.unmatched} />

      <ServiceDetail service={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
