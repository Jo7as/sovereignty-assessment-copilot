// Warum jetzt, Arbeitsweise und häufige Fragen. Fundstellen wie in data/compliance.yaml,
// dort mit verify_evidence.py nachgeprüft.

const DORA = "http://publications.europa.eu/resource/cellar/0caf473a-85bd-11ed-9887-01aa75ed71a1.0004.03/DOC_1";
const NIS2 = "http://publications.europa.eu/resource/cellar/9b84d482-85bd-11ed-9887-01aa75ed71a1.0004.03/DOC_1";

const DEADLINES = [
  {
    date: "17.01.2025",
    title: "DORA gilt",
    text: "Für Banken, Versicherer und andere Finanzunternehmen, unmittelbar in jedem Mitgliedstaat.",
    quote: "Sie gilt ab dem 17. Januar 2025.",
    source: DORA,
    cite: "Art. 64 DORA",
  },
  {
    date: "17.10.2024",
    title: "Frist zur Umsetzung der NIS2",
    text: "Für mittlere und große Unternehmen in kritischen Sektoren wie Energie, Gesundheit oder digitaler Infrastruktur.",
    quote: "Bis zum 17. Oktober 2024 erlassen und veröffentlichen die Mitgliedstaaten die erforderlichen Vorschriften",
    source: NIS2,
    cite: "Art. 41 Abs. 1 NIS2",
  },
  {
    date: "Pflicht",
    title: "Exit-Strategien für kritische Funktionen",
    text: "Wer unter DORA fällt, braucht für jeden Dienst, der eine kritische oder wichtige Funktion unterstützt, einen Weg hinaus.",
    quote: "Für IKT-Dienstleistungen, die kritische oder wichtige Funktionen unterstützen, richten Finanzunternehmen Ausstiegsstrategien ein.",
    source: DORA,
    cite: "Art. 28 Abs. 8 DORA",
  },
];

export function WhyNow() {
  return (
    <ol className="grid gap-6 md:grid-cols-3">
      {DEADLINES.map((item) => (
        <li key={item.title} className="rounded-lg border border-hairline bg-surface p-6">
          <p className="tabular text-sm font-medium text-accent">{item.date}</p>
          <h3 className="mt-2 font-semibold">{item.title}</h3>
          <p className="mt-2 text-sm text-ink-secondary">{item.text}</p>
          <blockquote className="mt-4 border-l-2 border-hairline pl-3 text-xs text-ink-secondary">
            „{item.quote}“{" "}
            <a href={item.source} target="_blank" rel="noreferrer" className="whitespace-nowrap underline">
              {item.cite}
            </a>
          </blockquote>
        </li>
      ))}
    </ol>
  );
}

const PRINCIPLES = [
  {
    title: "Belegt",
    text: "Jede Angabe zu einem Anbieter hat eine Quelle mit wörtlicher Fundstelle. Ein Skript ruft jede Quelle erneut ab und sucht die Fundstelle.",
  },
  {
    title: "Vorsichtig",
    text: "Fehlt eine Angabe, zählt der ungünstigste Fall. Neben der gesicherten Stufe steht die mögliche, und die Lücke wird zur Frage an den Anbieter.",
  },
  {
    title: "KI mit Kontrolle",
    text: "Die KI ordnet nur unsichere Einträge zu, wählt nur aus dem Katalog und jeder Vorschlag ist markiert. Angefragt werden nur Anbieter ohne Datenspeicherung.",
  },
  {
    title: "Maßgeblich ist die Konzernmutter",
    text: "Ein Rechenzentrum in Frankfurt schützt nicht vor dem Recht des Landes, in dem der Konzern sitzt. Bewertet wird deshalb der Rechtsraum der Konzernmutter.",
  },
];

export function Principles() {
  return (
    <ul className="grid gap-8 sm:grid-cols-2">
      {PRINCIPLES.map((item) => (
        <li key={item.title}>
          <h3 className="font-semibold">{item.title}</h3>
          <p className="mt-2 text-sm text-ink-secondary">{item.text}</p>
        </li>
      ))}
    </ul>
  );
}

const QUESTIONS = [
  {
    question: "Ersetzt das Ergebnis eine Rechtsberatung?",
    answer: "Nein. Das Werkzeug ist eine Vorprüfung. Es zeigt, wo Lücken wahrscheinlich sind, und nennt dazu die Fundstelle. Die verbindliche Prüfung bleibt bei Rechtsabteilung, Aufsicht oder Beratung.",
  },
  {
    question: "Was passiert mit unseren Daten?",
    answer: "Fragebogen und IT-Bestand werden in der Datenbank dieses Prototyps gespeichert. Einträge, die der Textvergleich nicht sicher erkennt, gehen an ein KI-Modell, angefragt nur bei Anbietern ohne Datenspeicherung. Für echte Kundendaten ist ein in der EU betriebenes Modell vorgesehen.",
  },
  {
    question: "Woher stammen die Angaben zu den Anbietern?",
    answer: "Aus öffentlichen Quellen: Vertragsunterlagen, Dokumentation, Zertifikatsverzeichnisse, Handelsregister. Jede Angabe trägt einen Prüfstatus, der in der Detailansicht steht.",
  },
  {
    question: "Was bedeuten die Stufen 0 bis 4?",
    answer: "Die Stufen folgen dem Cloud Sovereignty Framework der EU-Kommission: von 0, unter ausschließlicher Kontrolle außerhalb der EU, bis 4, vollständig unter EU-Kontrolle. Die Gesamtstufe eines Dienstes ist sein schwächster Zielbereich.",
  },
  {
    question: "Gilt für uns DORA oder NIS2?",
    answer: "Das bestimmt der Fragebogen aus Sektor, Beschäftigten, Umsatz und Bilanzsumme, jeweils mit Fundstelle. Bei Finanzunternehmen geht DORA der NIS2 vor.",
  },
];

export function Faq() {
  return (
    <div className="max-w-3xl divide-y divide-hairline border-y border-hairline">
      {QUESTIONS.map((item) => (
        <details key={item.question} className="group py-4">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-medium focus-visible:outline-2 focus-visible:outline-accent">
            {item.question}
            <span aria-hidden className="text-ink-muted transition-transform group-open:rotate-45">
              +
            </span>
          </summary>
          <p className="mt-3 text-sm text-ink-secondary">{item.answer}</p>
        </details>
      ))}
    </div>
  );
}
