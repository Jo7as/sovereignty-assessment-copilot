import type { ReactNode } from "react";

import { OBJECTIVES } from "@/lib/labels";

// Abschnitt der Startseite mit einheitlicher Breite und Abstand
interface SectionProps {
  id: string;
  title: string;
  intro?: string;
  tone?: "page" | "surface"; // wechselnde Flächen geben der langen Seite Rhythmus
  children: ReactNode;
}

export function Section({ id, title, intro, tone = "page", children }: SectionProps) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className={`scroll-mt-8 border-t border-hairline ${tone === "surface" ? "bg-surface" : ""}`}
    >
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8 lg:py-20">
        <h2 id={`${id}-title`} className="max-w-2xl text-2xl font-semibold tracking-tight sm:text-3xl">
          {title}
        </h2>
        {intro && <p className="mt-3 max-w-2xl text-ink-secondary">{intro}</p>}
        <div className="mt-10">{children}</div>
      </div>
    </section>
  );
}

// Zahlen aus den Dateien in data/, gezählt am 20.10.2026. Bei größeren Änderungen der
// Anbieterdatenbank hier nachziehen.
const FACTS = [
  { value: "61", label: "Dienste mit Konzernmutter und Sitzland" },
  { value: "147", label: "Angaben zu Anbietern, jede mit Fundstelle" },
  { value: "50", label: "Fundstellen aus DORA, NIS2 und KMU-Empfehlung" },
  { value: "8", label: "Zielbereiche des EU Cloud Sovereignty Framework" },
];

export function Facts() {
  return (
    <dl className="mx-auto grid max-w-7xl gap-8 px-4 py-12 sm:grid-cols-2 sm:px-6 lg:grid-cols-4 lg:px-8">
      {FACTS.map((fact) => (
        <div key={fact.label} className="border-l-2 border-accent pl-4">
          <dt className="sr-only">{fact.label}</dt>
          <dd className="text-3xl font-semibold tracking-tight">{fact.value}</dd>
          <dd className="mt-1 text-sm text-ink-secondary">{fact.label}</dd>
        </div>
      ))}
    </dl>
  );
}

const STEPS = [
  {
    title: "Fragebogen",
    text: "27 Fragen zu Steuerung, Exit-Strategie und Notfallplanung. Daraus folgen der Reifegrad des Unternehmens und die Antwort, ob DORA oder NIS2 gilt.",
  },
  {
    title: "IT-Bestand",
    text: "Die Excel-Vorlage folgt dem Informationsregister nach DORA. Jeder Eintrag wird einem Dienst zugeordnet, unsichere Fälle schlägt eine KI vor, ein Mensch bestätigt sie.",
  },
  {
    title: "Ergebnis",
    text: "Heatmap aller Dienste über acht Zielbereiche, offene Pflichten mit Fundstelle und eine Roadmap in drei Wellen mit konkreten Fragen an Ihre Anbieter.",
  },
];

export function Steps() {
  return (
    <ol className="grid gap-8 md:grid-cols-3">
      {STEPS.map((step, index) => (
        <li key={step.title}>
          <span className="tabular flex h-8 w-8 items-center justify-center rounded-full border border-baseline text-sm font-medium">
            {index + 1}
          </span>
          <h3 className="mt-4 font-semibold">{step.title}</h3>
          <p className="mt-2 text-sm text-ink-secondary">{step.text}</p>
        </li>
      ))}
    </ol>
  );
}

const OBJECTIVE_TEXT: Record<string, string> = {
  STRATEGISCH: "Wem gehört der Anbieter, und wo sitzt die Konzernmutter?",
  RECHTLICH: "Welches Recht gilt, und können Behörden außerhalb der EU zugreifen?",
  DATEN_KI: "Wo liegen die Daten, wer hält die Schlüssel, wird mit ihnen trainiert?",
  OPERATIV: "Kommen Betrieb und Support aus der EU?",
  LIEFERKETTE: "Welche Zulieferer und Unterauftragnehmer hängen daran?",
  TECHNOLOGIE: "Offene Standards, Datenexport und ein Weg hinaus",
  SICHERHEIT: "Zertifikate wie BSI C5 und ISO 27001",
  UMWELT: "Strom aus erneuerbaren Quellen. Zählt nur im Souveränitätswert",
};

export function Objectives() {
  return (
    <ul className="grid gap-px overflow-hidden rounded-lg border border-hairline bg-hairline sm:grid-cols-2 lg:grid-cols-4">
      {OBJECTIVES.map((objective) => (
        <li key={objective.key} className="bg-surface p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h3 className="font-semibold">{objective.label}</h3>
            <span className="tabular text-xs text-ink-muted">{objective.weight} %</span>
          </div>
          <p className="mt-2 text-sm text-ink-secondary">{OBJECTIVE_TEXT[objective.key]}</p>
        </li>
      ))}
    </ul>
  );
}

const OUTSIDE = ["DNS und Hosting der Website", "Eingebundene Website-Dienste und Tracker", "Schnell und ohne Unterlagen"];
const INSIDE = [
  "Alle Dienste aus dem IT-Bestand, auch ohne Spur auf der Website: Kernbanksystem, Backup, Meldewesen",
  "Rechtsraum der Konzernmutter statt Serverstandort",
  "Varianten und Verträge, etwa EU-Datengrenze oder eigene Schlüssel",
  "DORA und NIS2, Reifegrad und Roadmap",
];

export function Comparison() {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div className="rounded-lg border border-hairline p-6">
        <h3 className="font-semibold">Außenscan der Website</h3>
        <p className="mt-1 text-sm text-ink-muted">etwa scan.meetergo.com</p>
        <ul className="mt-4 space-y-2 text-sm text-ink-secondary">
          {OUTSIDE.map((item) => (
            <li key={item} className="flex gap-2">
              <span aria-hidden className="text-ink-muted">–</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
      <div className="rounded-lg border-2 border-accent bg-surface p-6">
        <h3 className="font-semibold">Assessment von innen</h3>
        <p className="mt-1 text-sm text-ink-muted">dieses Werkzeug</p>
        <ul className="mt-4 space-y-2 text-sm">
          {INSIDE.map((item) => (
            <li key={item} className="flex gap-2">
              <span aria-hidden className="text-accent">✓</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
      <p className="text-sm text-ink-secondary md:col-span-2">
        Beides ergänzt sich: Der Außenscan zeigt, was jeder sehen kann. Das Assessment zeigt,
        wovon das Geschäft tatsächlich abhängt.
      </p>
    </div>
  );
}
