import { CRITICALITY } from "@/lib/labels";
import type { Question } from "@/lib/types";

export default function QuestionCatalog({ questions }: { questions: Question[] }) {
  const providers = [...new Set(questions.map((question) => question.provider))];
  return (
    <section aria-labelledby="questions-title">
      <h2 id="questions-title" className="text-lg font-semibold">Fragen an die Anbieter</h2>
      <p className="text-sm text-ink-secondary">
        Aus jeder fehlenden Angabe wird eine Frage. Kernfragen halten die Gesamtstufe unten und gehören in den ersten Workshop.
      </p>
      <div className="mt-4 divide-y divide-hairline border-y border-hairline">
        {providers.map((provider) => {
          const asked = questions.filter((question) => question.provider === provider);
          const core = asked.filter((question) => question.is_core);
          const services = [...new Set(asked.map((question) => question.service))];
          return (
            <details key={provider} className="group py-3">
              <summary className="cursor-pointer list-none focus-visible:outline-2 focus-visible:outline-accent">
                <span className="font-medium">{provider}</span>
                <span className="ml-2 text-xs text-ink-muted">
                  {services.join(", ")} · Kritikalität {CRITICALITY[asked[0].criticality]} · {core.length} Kernfragen, {asked.length - core.length} weitere
                </span>
              </summary>
              <ol className="mt-3 list-decimal space-y-1.5 pl-6 text-sm">
                {[...core, ...asked.filter((question) => !question.is_core)].map((question) => (
                  <li key={`${question.service}-${question.fact}`}>
                    {question.text}
                    {question.is_core && <span className="ml-2 text-xs font-medium text-accent">Kernfrage</span>}
                    {services.length > 1 && <span className="block text-xs text-ink-muted">{question.service}</span>}
                  </li>
                ))}
              </ol>
            </details>
          );
        })}
      </div>
    </section>
  );
}
