import type { ProblemDetail } from "@/lib/api";

const MAX_SHOWN = 10;

// Fehler aus der API: beim IT-Bestand mit Zeile und Spalte, sonst nur mit Meldung
export default function ProblemList({ details }: { details: ProblemDetail[] }) {
  if (details.length === 0) return null;
  return (
    <ul className="mt-2 space-y-1 text-ink-secondary">
      {details.slice(0, MAX_SHOWN).map((problem) => (
        <li key={`${problem.row}-${problem.column}-${problem.message}`}>
          {problem.row !== undefined && `Zeile ${problem.row}`}
          {problem.column ? `, Spalte „${problem.column.replace(" *", "")}“` : ""}
          {problem.row !== undefined && ": "}
          {problem.message}
        </li>
      ))}
      {details.length > MAX_SHOWN && <li>und {details.length - MAX_SHOWN} weitere</li>}
    </ul>
  );
}
