import type { Assessment } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface RowProblem {
  row: number;
  column: string | null;
  message: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly details: RowProblem[] = [],
  ) {
    super(message);
  }
}

async function read(response: Response): Promise<Assessment> {
  if (response.ok) return (await response.json()) as Assessment;
  let message = `Die Bewertung ist fehlgeschlagen (HTTP ${response.status}).`;
  let details: RowProblem[] = [];
  try {
    const body = await response.json();
    if (body?.error?.message) message = body.error.message;
    if (Array.isArray(body?.error?.details)) details = body.error.details;
  } catch {
    // Keine lesbare Fehlermeldung vom Server, die allgemeine Meldung bleibt
  }
  throw new ApiError(message, details);
}

async function call(path: string, init?: RequestInit): Promise<Assessment> {
  try {
    return await read(await fetch(`${API_URL}${path}`, init));
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      "Der Server ist nicht erreichbar. Läuft das Backend (uv run uvicorn app.main:app)?",
    );
  }
}

export function loadDemo(): Promise<Assessment> {
  return call("/assessments/demo");
}

export function assessFile(file: File): Promise<Assessment> {
  const form = new FormData();
  form.append("file", file);
  return call("/assessments/preview", { method: "POST", body: form });
}
