import type { AnswerValue, Assessment, Questionnaire, StoredAssessment } from "./types";

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

export function assessFile(file: File): Promise<Assessment> {
  const form = new FormData();
  form.append("file", file);
  return call("/assessments/preview", { method: "POST", body: form });
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
