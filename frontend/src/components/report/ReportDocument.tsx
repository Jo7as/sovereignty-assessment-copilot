import type { ReportResponse } from "@/lib/types";

import Cover from "./Cover";
import HeatmapPage from "./HeatmapPage";
import QuestionsAppendix from "./QuestionsAppendix";
import RegulationPage from "./RegulationPage";
import RisksPage from "./RisksPage";
import RoadmapPage from "./RoadmapPage";
import Summary from "./Summary";

// Reihenfolge wie in einem Abschlussbericht: Kernaussage vorn, Belege und Details hinten
export default function ReportDocument({ data }: { data: ReportResponse }) {
  const { inventory } = data.assessment;
  const critical = inventory.services.filter((service) => service.criticality === "HOCH");
  const others = inventory.services.filter((service) => service.criticality !== "HOCH");
  return (
    <article aria-label={`Bericht ${data.assessment.name}`} className="px-4 pb-12 print:p-0">
      <Cover data={data} />
      <Summary report={data.report} />
      <HeatmapPage
        eyebrow="2 · Heatmap"
        title="Hoch kritische Dienste"
        intro={`Stufe 0 bis 4 je Zielbereich für die ${critical.length} Dienste mit hoher Kritikalität. Die übrigen Dienste stehen in Anhang A.`}
        services={critical}
      />
      <RisksPage report={data.report} />
      <RegulationPage data={data} />
      <RoadmapPage roadmap={inventory.roadmap} />
      {others.length > 0 && (
        <HeatmapPage
          eyebrow="Anhang A"
          title="Übrige Dienste"
          intro={`Stufe 0 bis 4 je Zielbereich für die ${others.length} Dienste mit mittlerer oder geringer Kritikalität.`}
          services={others}
        />
      )}
      {inventory.roadmap.questions.length > 0 && <QuestionsAppendix questions={inventory.roadmap.questions} />}
    </article>
  );
}
