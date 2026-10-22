import type {
  AnswerValue,
  Assessment,
  Prefill,
  QuickCheckResult,
  Questionnaire,
  StoredAssessment,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Ein Fehler im Detail: beim IT-Bestand mit Zeile und Spalte, bei Antworten mit Frage,
// bei ungültigen Anfragen mit Ort
export interface ProblemDetail {
  message: string;
  row?: number;
  column?: string | null;
  question?: string;
  location?: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null = null,
    readonly details: ProblemDetail[] = [],
  ) {
    super(message);
  }
}

async function read<T>(response: Response): Promise<T> {
  if (response.ok) return (await response.json()) as T;
  let message = `Die Anfrage ist fehlgeschlagen (HTTP ${response.status}).`;
  let details: ProblemDetail[] = [];
  try {
    const body = await response.json();
    if (body?.error?.message) message = body.error.message;
    if (Array.isArray(body?.error?.details)) details = body.error.details;
  } catch {
    // Keine lesbare Fehlermeldung vom Server, die allgemeine Meldung bleibt
  }
  throw new ApiError(message, response.status, details);
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(
      "Der Server ist nicht erreichbar. Läuft das Backend (uv run uvicorn app.main:app)?",
    );
  }
  return read<T>(response);
}

function json(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export function loadDemo(): Promise<Assessment> {
  return call("/assessments/demo");
}


export function loadQuestionnaire(): Promise<Questionnaire> {
  return call("/questionnaire");
}

export function createAssessment(name: string): Promise<StoredAssessment> {
  return call("/assessments", json("POST", { name }));
}

export function loadAssessment(id: number): Promise<StoredAssessment> {
  return call(`/assessments/${id}`);
}

/** Speichert Antworten. `null` löscht eine Antwort. */
export function saveAnswers(
  id: number,
  answers: Record<string, AnswerValue | null>,
): Promise<StoredAssessment> {
  return call(`/assessments/${id}/answers`, json("PUT", { answers }));
}

/** Speichert den IT-Bestand am Assessment. Mit KI kann die Zuordnung eine Minute dauern. */
export function uploadInventory(id: number, file: File): Promise<StoredAssessment> {
  const form = new FormData();
  form.append("file", file);
  return call(`/assessments/${id}/inventory`, { method: "PUT", body: form });
}

/**
 * Startet den Schnellcheck und meldet jeden Schritt, sobald der Server ihn beginnt.
 * Gibt eine Funktion zum Abbrechen zurück.
 */
export function startQuickCheck(
  domain: string,
  handlers: {
    onPlan: (steps: string[]) => void;
    onStep: (step: string) => void;
    onResult: (result: QuickCheckResult) => void;
    onError: (message: string) => void;
  },
): () => void {
  const source = new EventSource(`${API_URL}/scan/stream?domain=${encodeURIComponent(domain)}`);
  let finished = false;
  source.addEventListener("plan", (event) => handlers.onPlan(JSON.parse((event as MessageEvent).data)));
  source.addEventListener("step", (event) => handlers.onStep(JSON.parse((event as MessageEvent).data)));
  source.addEventListener("result", (event) => {
    finished = true;
    source.close();
    handlers.onResult(JSON.parse((event as MessageEvent).data));
  });
  source.addEventListener("error", (event) => {
    if (finished) return;
    finished = true;
    source.close();
    // Eigene Fehlermeldung des Servers oder abgebrochene Verbindung
    const data = (event as MessageEvent).data;
    handlers.onError(
      data ? JSON.parse(data) : "Der Schnellcheck ließ sich nicht starten. Bitte die Domain prüfen.",
    );
  });
  return () => {
    finished = true;
    source.close();
  };
}

export interface FromScanRequest {
  name: string;
  domain: string;
  services: string[];
  sector: Prefill["sector"];
  employees: Prefill["employees"];
  profile: Prefill["profile"];
}

export function createFromScan(body: FromScanRequest): Promise<StoredAssessment> {
  return call("/assessments/from-scan", json("POST", body));
}
