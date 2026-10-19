import type { Criticality, Effort, Level, ObjectiveKey } from "./types";

// Reihenfolge und Namen der acht Zielbereiche des EU Cloud Sovereignty Framework
export const OBJECTIVES: { key: ObjectiveKey; label: string; short: string; weight: number }[] = [
  { key: "STRATEGISCH", label: "Strategisch", short: "Strat.", weight: 15 },
  { key: "RECHTLICH", label: "Rechtlich", short: "Recht", weight: 10 },
  { key: "DATEN_KI", label: "Daten und KI", short: "Daten", weight: 10 },
  { key: "OPERATIV", label: "Operativ", short: "Betrieb", weight: 15 },
  { key: "LIEFERKETTE", label: "Lieferkette", short: "Liefer.", weight: 20 },
  { key: "TECHNOLOGIE", label: "Technologie", short: "Techn.", weight: 15 },
  { key: "SICHERHEIT", label: "Sicherheit und Compliance", short: "Sich.", weight: 10 },
  { key: "UMWELT", label: "Umwelt", short: "Umwelt", weight: 5 },
];

// Kurzbeschreibung der Stufen, angelehnt an den Wortlaut des Rahmenwerks
export const LEVELS: Record<Level, { name: string; description: string }> = {
  0: { name: "Keine Souveränität", description: "Unter ausschließlicher Kontrolle außerhalb der EU" },
  1: { name: "Rechtsraum", description: "EU-Recht gilt nur formal" },
  2: { name: "Datensouveränität", description: "Wesentliche Abhängigkeiten außerhalb der EU" },
  3: { name: "Digitale Resilienz", description: "Nur geringe Kontrolle von außerhalb der EU" },
  4: { name: "Volle Souveränität", description: "Vollständig unter EU-Kontrolle" },
};

export const CRITICALITY: Record<Criticality, string> = {
  HOCH: "hoch",
  MITTEL: "mittel",
  GERING: "gering",
};

export const EFFORT: Record<Effort, string> = {
  GERING: "geringer Aufwand",
  MITTEL: "mittlerer Aufwand",
  HOCH: "hoher Aufwand",
};

export const REVIEW_STATUS: Record<string, string> = {
  KI_VORSCHLAG: "KI-Vorschlag, nicht nachgeprüft",
  KI_NACHGEPRUEFT: "Von der KI nachgeprüft",
  GEPRUEFT: "Von einem Menschen geprüft",
};

// Bezeichnung der belegten Merkmale in der Detailansicht
export const ATTRIBUTES: Record<string, string> = {
  ultimate_parent: "Konzernmutter",
  data_location: "Datenstandort",
  operations_location: "Betrieb und Support",
  transfer_basis: "Übermittlungsgrundlage",
  governing_law: "Vertragsrecht",
  key_management: "Schlüsselverwaltung",
  data_export: "Datenexport",
  openness: "Offenheit",
  ai_training_on_customer_data: "KI-Training",
  renewable_energy: "Energieversorgung",
};

export function attributeLabel(attribute: string): string {
  if (attribute.startsWith("certificate:")) return `Zertifikat ${attribute.split(":")[1]}`;
  if (attribute.startsWith("dependency:")) return `Zulieferer ${attribute.split(":")[1]}`;
  return ATTRIBUTES[attribute] ?? attribute;
}

export function levelText(level: number, potential: number): string {
  return level === potential ? `Stufe ${level}` : `gesichert Stufe ${level}, möglich Stufe ${potential}`;
}
