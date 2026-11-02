import { LEVELS, OBJECTIVES } from "@/lib/labels";
import type { Assessment, Level } from "@/lib/types";

import { Sheet, SheetTitle } from "./Sheet";

const SCALE: Level[] = [0, 1, 2, 3, 4];
// Prüfstatus im Satzfluss, deshalb klein und als Teil eines Satzes formuliert
const STATUS_TEXT: Record<string, string> = {
  GEPRUEFT: "von einem Menschen geprüft",
  KI_NACHGEPRUEFT: "von der KI nachgeprüft",
  KI_VORSCHLAG: "als KI-Vorschlag noch nicht nachgeprüft",
};

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="break-inside-avoid">
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="mt-1 space-y-1.5">{children}</div>
    </section>
  );
}

// Wie bewertet wird und was der Bericht nicht leisten kann. Inhaltlich wie docs/bewertungslogik.md.
export default function MethodPage({ inventory, sources }: { inventory: Assessment; sources: number }) {
  const status = new Map<string, number>();
  for (const service of inventory.services) status.set(service.review_status, (status.get(service.review_status) ?? 0) + 1);
  const unmatched = inventory.unmatched;

  return (
    <Sheet label="Methodik und Grenzen">
      <SheetTitle eyebrow="6 · Methodik">Methodik und Grenzen</SheetTitle>
      <div className="space-y-4 text-[12px] leading-snug">
        <Block title="Maßstab">
          <p>
            Cloud Sovereignty Framework der Europäischen Kommission, Version 1.2.1 (Oktober 2025): acht Zielbereiche und
            fünf Stufen. Das Rahmenwerk legt nicht fest, welche Tatsache zu welcher Stufe führt. Die Regeln dieses Berichts
            sind deshalb eine begründete Auslegung.
          </p>
          <div className="grid grid-cols-2 gap-x-6">
            <ul className="space-y-0.5 text-[11px]">
              {SCALE.map((level) => (
                <li key={level}>
                  <span className="font-medium">
                    Stufe {level} · {LEVELS[level].name}:
                  </span>{" "}
                  {LEVELS[level].description}
                </li>
              ))}
            </ul>
            <ul className="space-y-0.5 text-[11px]">
              {OBJECTIVES.map((objective) => (
                <li key={objective.key} className="flex justify-between gap-2">
                  <span>{objective.label}</span>
                  <span className="tabular text-ink-muted">{objective.weight} %</span>
                </li>
              ))}
            </ul>
          </div>
        </Block>

        <Block title="Von den Angaben zur Stufe">
          <p>
            Je Zielbereich begrenzen ein bis drei Kriterien die Stufe, es zählt das schwächste. Die Gesamtstufe eines
            Dienstes ist der schwächste Zielbereich ohne Umwelt. Der Souveränitätswert (0 bis 100) gewichtet alle acht
            Zielbereiche nach den Gewichten des Rahmenwerks. Für das Unternehmen gehen die Dienste nach Kritikalität ein:
            gering 1, mittel 2, hoch 3.
          </p>
          <p>
            Maßgeblich ist, wer den Dienst kontrolliert: der Betreiber der Variante, sonst der Anbieter, und davon der
            schwächere Rechtsraum aus eigenem Sitz und Sitz der Konzernmutter. Ein Rechenzentrum in der EU ändert daran
            nichts, denn eine Konzernmutter in den USA unterliegt dem CLOUD Act.
          </p>
          <p>
            Fehlt eine Angabe, nennt der Bericht zwei Stufen: gesichert, wenn sie wie der ungünstigste Fall zählt, und
            möglich, wenn sie wie der günstigste zählt. Fehlendes Wissen führt so nie zu einer zu guten Stufe.
          </p>
        </Block>

        <Block title="Von der Stufe zur Roadmap">
          <p>
            Priorität ist Kritikalität mal Abstand zur Höchststufe. Jede fehlende Angabe wird zu einer Frage an den Anbieter.
            Maßnahmen sind ein Wechsel der Variante beim selben Anbieter oder zu einer EU-Alternative aus der Datenbank. Die
            Wellen folgen dem Aufwand: Klärungen und geringer Aufwand zuerst, Migrationen zuletzt. Der Aufwand ist eine
            Einschätzung, keine belegte Angabe.
          </p>
        </Block>

        <Block title="Belege und Prüfstatus">
          <p>
            Jede Angabe zu einem Anbieter hat eine Quelle mit wörtlicher Fundstelle, zusammen {sources} Fundstellen im
            Quellenverzeichnis (Anhang C). Die Fundstellen lassen sich automatisch erneut abrufen und auf ihren Wortlaut
            prüfen.
          </p>
          <p>
            Prüfstatus der bewerteten Dienste:{" "}
            {[...status.entries()]
              .map(([key, count]) => `${count} ${STATUS_TEXT[key] ?? key}`)
              .join(", ")}
            . Ein KI-Vorschlag ist recherchiert und belegt, aber noch nicht in einem zweiten Durchgang nachgeprüft.
          </p>
        </Block>

        <Block title="Grenzen">
          <ul className="list-disc space-y-1 pl-4">
            <li>Keine Rechtsberatung. Die Einordnung zu DORA und NIS2 ist eine Vorprüfung mit Fundstellen.</li>
            <li>
              Bewertet sind die öffentlich belegten Standardbedingungen der Anbieter, nicht die individuellen Verträge des
              Unternehmens. Abweichende Vereinbarungen können die Stufe heben oder senken.
            </li>
            <li>
              Je Zielbereich bildet der Bericht ein bis drei der vier bis sechs Faktoren des Rahmenwerks ab. Die Schwellen
              zwischen den Stufen sind begründete Setzungen und nicht gegen Bewertungen Dritter geeicht.
            </li>
            <li>„Möglich“ ist eine Obergrenze, keine Erwartung: Sie nimmt für jede offene Angabe den besten Fall an.</li>
            <li>
              Grundlage ist der IT-Bestand mit den Angaben des Unternehmens zu Kritikalität und Exit-Plänen. Der Bericht ist
              eine Momentaufnahme zum Datenstand auf dem Deckblatt.
            </li>
            {unmatched.length > 0 && (
              <li>
                {unmatched.length === 1
                  ? "1 Eintrag im IT-Bestand ließ sich keinem Dienst der Datenbank zuordnen und ist nicht bewertet: "
                  : `${unmatched.length} Einträge im IT-Bestand ließen sich keinem Dienst der Datenbank zuordnen und sind nicht bewertet: `}
                {unmatched.map((entry) => entry.service).join(", ")}.
              </li>
            )}
          </ul>
        </Block>
      </div>
    </Sheet>
  );
}
