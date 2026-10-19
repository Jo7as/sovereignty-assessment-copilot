import type { Level } from "@/lib/types";

// Helle Stufen tragen dunkle Schrift, dunkle Stufen helle. Die Token tauschen im
// dunklen Modus mit, weil sich dort auch die Skala umkehrt.
export function levelStyle(level: Level) {
  return {
    background: `var(--level-${level})`,
    color: level <= 1 ? "var(--level-ink-light)" : "var(--level-ink-dark)",
  };
}

interface Props {
  level: Level;
  potential: Level;
  emphasis?: boolean;
}

/** Zelle mit gesicherter Stufe. Ist mehr möglich, steht die mögliche Stufe klein daneben. */
export default function LevelCell({ level, potential, emphasis = false }: Props) {
  const provisional = potential > level;
  return (
    <span
      className={`tabular flex h-9 w-full items-center justify-center gap-1 rounded-sm ${
        emphasis ? "font-semibold" : ""
      }`}
      style={levelStyle(level)}
    >
      <span>{level}</span>
      {provisional && (
        <span className="text-[0.7rem] opacity-80" aria-hidden="true">
          ↗{potential}
        </span>
      )}
    </span>
  );
}
