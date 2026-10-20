import type { Assessment } from "@/lib/types";

export default function UnmatchedList({ unmatched }: { unmatched: Assessment["unmatched"] }) {
  if (unmatched.length === 0) return null;
  return (
    <section aria-labelledby="unmatched-title">
      <h2 id="unmatched-title" className="text-xl font-semibold tracking-tight">Nicht zugeordnete Einträge</h2>
      <p className="text-sm text-ink-secondary">
        Diese Einträge konnte das Tool keinem Dienst sicher zuordnen. Meist sind es Eigenentwicklungen oder Dienste, die noch nicht in der Datenbank stehen. Sie sind nicht bewertet.
      </p>
      <ul className="mt-3 divide-y divide-hairline border-y border-hairline text-sm">
        {unmatched.map((entry) => (
          <li key={entry.row} className="flex gap-4 py-2">
            <span className="tabular w-16 shrink-0 text-xs text-ink-muted">Zeile {entry.row}</span>
            <span>
              {entry.service}
              <span className="block text-xs text-ink-muted">{entry.reason}</span>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
