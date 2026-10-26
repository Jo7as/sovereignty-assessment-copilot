import type { Question } from "@/lib/types";

import { Sheet, SheetTitle } from "./Sheet";

// Themen der Fragen in fester Reihenfolge, lang für den Fragentext, kurz für die Tabelle
const TOPICS: { fact: string; label: string; short: string }[] = [
  { fact: "data_location", label: "Datenstandort", short: "Standort" },
  { fact: "transfer_basis", label: "Übermittlungsgrundlage", short: "Übermittl." },
  { fact: "operations_location", label: "Betrieb und Support", short: "Betrieb" },
  { fact: "governing_law", label: "Vertragsrecht", short: "Recht" },
  { fact: "key_management", label: "Schlüsselverwaltung", short: "Schlüssel" },
  { fact: "data_export", label: "Datenexport", short: "Export" },
  { fact: "openness", label: "Offenheit", short: "Offenheit" },
  { fact: "ai_training_on_customer_data", label: "KI-Training", short: "KI" },
  { fact: "certificates", label: "Zertifikate", short: "Zertif." },
  { fact: "dependencies", label: "Zulieferer", short: "Zuliefer." },
  { fact: "renewable_energy", label: "Energieversorgung", short: "Energie" },
];

interface Row {
  provider: string;
  services: Set<string>;
  facts: Map<string, boolean>; // Thema → Kernfrage?
}

function byProvider(questions: Question[]): Row[] {
  const rows = new Map<string, Row>();
  for (const question of questions) {
    const row = rows.get(question.provider) ?? { provider: question.provider, services: new Set(), facts: new Map() };
    row.services.add(question.service);
    row.facts.set(question.fact, (row.facts.get(question.fact) ?? false) || question.is_core);
    rows.set(question.provider, row);
  }
  // Anbieter mit den meisten Kernfragen zuerst
  const core = (row: Row) => [...row.facts.values()].filter(Boolean).length;
  return [...rows.values()].sort((a, b) => core(b) - core(a) || a.provider.localeCompare(b.provider, "de"));
}

// Fragenkatalog: jede Frage einmal je Thema, dann welcher Anbieter welche Fragen bekommt
export default function QuestionsAppendix({ questions }: { questions: Question[] }) {
  const texts = new Map(questions.map((question) => [question.fact, question.text]));
  const topics = TOPICS.filter((topic) => texts.has(topic.fact));
  const rows = byProvider(questions);
  const coreCount = questions.filter((question) => question.is_core).length;

  return (
    <Sheet label="Fragenkatalog an die Anbieter">
      <SheetTitle eyebrow="Anhang B">Fragenkatalog an die Anbieter</SheetTitle>
      <p className="text-ink-secondary">
        {questions.length} Fragen an {rows.length} Anbieter, davon {coreCount} Kernfragen. Eine Kernfrage betrifft eine
        Lücke, die einen der schwächsten Zielbereiche begrenzt und damit die Gesamtstufe des Dienstes unten hält.
      </p>

      <h3 className="mt-4 text-sm font-semibold">Die Fragen je Thema</h3>
      <dl className="mt-2 grid grid-cols-[34mm_1fr] gap-x-3 gap-y-1.5 text-[11px]">
        {topics.map((topic) => (
          <div key={topic.fact} className="contents">
            <dt className="font-medium">{topic.label}</dt>
            <dd className="text-ink-secondary">{texts.get(topic.fact)}</dd>
          </div>
        ))}
      </dl>

      <h3 className="mt-6 text-sm font-semibold break-after-avoid">Wer welche Fragen bekommt</h3>
      <p className="mb-2 text-[10px] text-ink-muted">● Kernfrage · ○ weitere Frage</p>
      <table className="w-full table-fixed border-collapse text-[10px]">
        <thead>
          <tr className="text-left text-[9px] text-ink-muted">
            <th className="w-[52mm] pb-1 font-normal">Anbieter (Dienste)</th>
            {topics.map((topic) => (
              <th key={topic.fact} className="pb-1 text-center font-normal">
                {topic.short}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.provider} className="break-inside-avoid border-t border-hairline">
              <td className="py-1 pr-2 leading-tight">
                <span className="block truncate font-medium">{row.provider}</span>
                <span className="block truncate text-[9px] text-ink-muted">{[...row.services].join(", ")}</span>
              </td>
              {topics.map((topic) => (
                <td key={topic.fact} className="py-1 text-center">
                  {row.facts.has(topic.fact) ? (row.facts.get(topic.fact) ? "●" : "○") : ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Sheet>
  );
}
