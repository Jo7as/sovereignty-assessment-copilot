import type { QuickCheckResult } from "@/lib/types";

const GLEIF_RECORD = "https://search.gleif.org/#/record/";

// Seitentitel nur an Trennern mit Leerzeichen kürzen: „Capgemini - Make it real“, nicht „ING-DiBa“
export function shortTitle(title: string): string {
  return title.split(/\s[|–-]\s/)[0].trim();
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 py-2 sm:grid-cols-[11rem_1fr] sm:gap-4">
      <dt className="text-sm text-ink-muted">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </div>
  );
}

// Unternehmensprofil aus Impressum und GLEIF, dazu die Vorschläge der KI mit Zitat
export default function ProfileCard({ result }: { result: QuickCheckResult }) {
  const { imprint, entity, parent, notes, imprint_url } = result.profile;
  const { sector, employees, note, pending } = result.suggestions;

  return (
    <section aria-labelledby="profile-title" className="rounded-lg border border-hairline bg-surface p-6">
      <h2 id="profile-title" className="text-xl font-semibold tracking-tight">
        Unternehmen
      </h2>
      <p className="text-sm text-ink-secondary">Aus Impressum, dem Register GLEIF und dem Text der Website.</p>

      <dl className="mt-4 divide-y divide-hairline">
        <Row label="Firma">{imprint.legal_name?.value ?? (shortTitle(result.title) || result.domain)}</Row>
        {imprint.register && (
          <Row label="Register">
            {imprint.register.kind} {imprint.register.number}
            {imprint.register.court && `, Amtsgericht ${imprint.register.court}`}
          </Row>
        )}
        {imprint.supervision && (
          <Row label="Aufsicht">
            Hinweis auf die BaFin im Impressum. Das spricht für ein Finanzunternehmen unter DORA.
            <span className="mt-1 block text-xs text-ink-muted">„{imprint.supervision.quote}“</span>
          </Row>
        )}
        {entity && (
          <Row label="LEI">
            <a href={`${GLEIF_RECORD}${entity.lei}`} target="_blank" rel="noreferrer" className="tabular underline">
              {entity.lei}
            </a>
            <span className="text-ink-muted"> · {entity.name}</span>
          </Row>
        )}
        {entity && (
          <Row label="Konzernmutter">
            {parent ? (
              <>
                {parent.name} <span className="text-ink-muted">({parent.country})</span>
              </>
            ) : (
              <span className="text-ink-muted">Bei GLEIF keine gemeldet</span>
            )}
          </Row>
        )}
        {pending && (
          <Row label="Branche und Größe">
            <span role="status" className="flex items-center gap-2 text-ink-secondary">
              <span aria-hidden className="h-2 w-2 animate-pulse rounded-full bg-accent" />
              Die KI liest die Website und schlägt Branche und Größe vor …
            </span>
          </Row>
        )}
        {sector && (
          <Row label="Branche (Vorschlag)">
            {sector.label}
            <span className="mt-1 block text-xs text-ink-muted">Begründet mit: „{sector.quote}“</span>
          </Row>
        )}
        {employees && (
          <Row label="Beschäftigte (Vorschlag)">
            {employees.label}
            <span className="mt-1 block text-xs text-ink-muted">„{employees.quote}“</span>
          </Row>
        )}
      </dl>

      <ul className="mt-4 space-y-1 text-xs text-ink-muted">
        {imprint_url && (
          <li>
            Quelle:{" "}
            <a href={imprint_url} target="_blank" rel="noreferrer" className="underline">
              Impressum
            </a>
          </li>
        )}
        {[...notes, ...(note ? [note] : [])].map((text) => (
          <li key={text}>{text}</li>
        ))}
        <li>Vorschläge der KI sind wörtlich belegt und werden im Fragebogen erst nach Bestätigung übernommen.</li>
      </ul>
    </section>
  );
}
