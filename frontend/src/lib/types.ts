// Antwort von GET /assessments/demo und POST /assessments/preview

export type Level = 0 | 1 | 2 | 3 | 4;
export type Criticality = "HOCH" | "MITTEL" | "GERING";
export type Effort = "GERING" | "MITTEL" | "HOCH";
export type ObjectiveKey =
  | "STRATEGISCH"
  | "RECHTLICH"
  | "DATEN_KI"
  | "OPERATIV"
  | "LIEFERKETTE"
  | "TECHNOLOGIE"
  | "SICHERHEIT"
  | "UMWELT";

export interface Finding {
  criterion: string;
  ceiling: Level;
  potential: Level;
  reason: string;
  fact: string | null;
  is_gap: boolean;
}

export interface ObjectiveResult {
  level: Level;
  potential: Level;
  findings: Finding[];
}

export interface EvidenceItem {
  attribute: string;
  source_url: string;
  quote: string | null;
  retrieved_at: string;
}

export interface AssessedService {
  service: string;
  name: string;
  provider: string;
  variant: string;
  variant_name: string;
  criticality: Criticality;
  critical_function: boolean;
  rows: number[];
  needs_review: boolean;
  level: Level;
  potential: Level;
  score: number;
  potential_score: number;
  gaps: string[];
  objectives: Record<ObjectiveKey, ObjectiveResult>;
  notes: string[];
  review_status: "KI_VORSCHLAG" | "KI_NACHGEPRUEFT" | "GEPRUEFT";
  evidence: EvidenceItem[];
}

export interface Portfolio {
  level: number;
  potential: number;
  score: number;
  potential_score: number;
  levels: Record<ObjectiveKey, number>;
  weakest_critical_level: Level | null;
  weakest_critical_services: string[];
  distribution: Record<string, number>;
  provisional_services: number;
}

export interface WaveItem {
  title: string;
  services: string[];
  criticality: Criticality;
  effort: Effort | null;
  level_now: Level;
  priority: number;
  possible_gain: number;
}

export interface Measure {
  service: string;
  criticality: Criticality;
  kind: "VARIANTE" | "ALTERNATIVE";
  target: string;
  effort: Effort;
  wave: 1 | 2 | 3;
  level_before: Level;
  potential_before: Level;
  level_after: Level;
  potential_after: Level;
  score_before: number;
  score_after: number;
  note: string | null;
}

export interface Question {
  provider: string;
  service: string;
  criticality: Criticality;
  fact: string;
  text: string;
  level_now: Level;
  level_if_favourable: Level;
  is_core: boolean;
}

export interface Assessment {
  inventory: { name: string; entries: number; assessed_on: string };
  services: AssessedService[];
  unmatched: { row: number; service: string; reason: string }[];
  portfolio: Portfolio | null;
  roadmap: {
    waves: { wave: 1 | 2 | 3; title: string; items: WaveItem[] }[];
    measures: Measure[];
    questions: Question[];
  };
}
