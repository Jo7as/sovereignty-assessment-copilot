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

export interface InventoryHint {
  code: "EXIT_PLAN_MISSING" | "CONCENTRATION" | "HARD_TO_REPLACE";
  title: string;
  explanation: string;
  services: string[];
  basis: LegalBasis[];
  group: string | null;
}

export interface Assessment {
  inventory: { name: string; entries: number; assessed_on: string };
  // DORA-Hinweise aus dem Bestand. applies: true (DORA gilt), false (gilt nicht), null (offen)
  dora_hints: { applies: boolean | null; condition: string; hints: InventoryHint[] };
  services: AssessedService[];
  unmatched: { row: number; service: string; reason: string }[];
  portfolio: Portfolio | null;
  roadmap: {
    waves: { wave: 1 | 2 | 3; title: string; items: WaveItem[] }[];
    measures: Measure[];
    questions: Question[];
  };
}

// Fragebogen (GET /questionnaire)

export interface LegalBasis {
  law: "DORA" | "NIS2" | "KMU";
  article: string;
  source: string;
  quote: string;
  retrieved: string;
}

export interface QuestionOption {
  value: string;
  label: string;
  level: number | null;
}

export interface QuestionnaireQuestion {
  key: string;
  section: string;
  type: "SINGLE" | "NUMBER";
  text: string;
  help: string | null;
  unit: string | null;
  dimension: string | null;
  options: QuestionOption[];
  basis: LegalBasis[];
}

export interface Questionnaire {
  version: number;
  laws: { key: string; title: string; url: string }[];
  sections: { key: string; title: string }[];
  dimensions: { key: string; label: string }[];
  questions: QuestionnaireQuestion[];
}

// Gespeichertes Assessment (GET /assessments/{id})

export type AnswerValue = string | number;
export type RegimeStatus = "GILT" | "GILT_NICHT" | "NICHT_BESTIMMBAR";

export interface DimensionMaturity {
  key: string;
  label: string;
  secured: number;
  possible: number;
  answered: number;
  total: number;
}

export interface Regime {
  law: "DORA" | "NIS2";
  status: RegimeStatus;
  reasons: string[];
  basis: LegalBasis[];
  entity_class: "WESENTLICH" | "WICHTIG" | null;
  microenterprise: boolean | null;
}

export interface QuestionHint {
  question: string;
  text: string;
  answer: string;
  severity: "LUECKE" | "TEILWEISE";
  basis: LegalBasis[];
}

export interface StoredAssessment {
  id: number;
  name: string;
  questionnaire_version: number;
  created_at: string;
  updated_at: string;
  answers: Record<string, AnswerValue>;
  progress: { answered: number; total: number };
  maturity: { dimensions: DimensionMaturity[]; secured: number; possible: number };
  regulation: {
    dora: Regime;
    nis2: Regime;
    dora_precedes_nis2: boolean;
    applicable_laws: ("DORA" | "NIS2")[];
    hints: QuestionHint[];
    unanswered_obligations: string[];
  };
  inventory: (Assessment & { inventory: { uploaded_at: string } }) | null;
}
