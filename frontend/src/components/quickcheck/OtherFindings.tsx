import type { FindingCategory, ScanFinding } from "@/lib/types";

import { RECORD_LABEL } from "./records";

const CATEGORY: Record<FindingCategory, string> = {
  EMAIL: "E-Mail",
  DOMAIN: "Domain und Zertifikate",
  HOSTING: "Hosting",
  WEBSITE: "Website",
};

// Funde ohne passenden Dienst in der Datenbank: zuerst die per Signatur benannten, dann roh
export default function OtherFindings({ findings }: { findings: ScanFinding[] }) {
  const named = findings.filter((f) => f.tool);
  const raw = findings.filter((f) => !f.tool);
  return (
    <>
      <NamedTools findings={named} />
      <RawFindings findings={raw} />
    </>
  );
}

// Belegstufe „Signatur“: Name aus einer offenen Liste, Anbieter und Rechtsraum noch nicht geprüft
function NamedTools({ findings }: { findings: ScanFinding[] }) {
  if (findings.length === 0) return null;
  return (
    <section aria-labelledby="named-title">
      <h2 id="named-title" className="text-xl font-semibold tracking-tight">
        Erkannt, noch ohne Bewertung{" "}
        <span className="tabular text-base font-normal text-ink-muted">({findings.length})</span>
      </h2>
      <p className="max-w-2xl text-sm text-ink-secondary">
        Diese Werkzeuge lädt die Website. Den Namen liefert eine offene Signaturliste. Wem sie gehören und welches Recht
        gilt, ist noch nicht geprüft. Deshalb zählen sie in der Bewertung oben nicht mit.
      </p>
      <ul className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {findings.map((finding) => (
          <li key={`${finding.record}-${finding.value}`} className="rounded-lg border border-hairline bg-surface p-4">
            <p className="font-medium">
              {finding.tool!.website ? (
                <a href={finding.tool!.website} target="_blank" rel="noreferrer" className="underline">
                  {finding.tool!.name}
                </a>
              ) : (
                finding.tool!.name
              )}
            </p>
            {finding.tool!.category && <p className="text-xs text-ink-muted">{finding.tool!.category}</p>}
            <p className="mt-2 break-all font-mono text-xs text-ink-secondary">{finding.value}</p>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-ink-muted">
        Quelle der Namen:{" "}
        <a href="https://github.com/enthec/webappanalyzer" target="_blank" rel="noreferrer" className="underline">
          enthec/webappanalyzer
        </a>{" "}
        (GPL-3.0), Nachfolger der offenen Wappalyzer-Daten.
      </p>
    </section>
  );
}

function RawFindings({ findings }: { findings: ScanFinding[] }) {
  if (findings.length === 0) return null;
  const groups = (Object.keys(CATEGORY) as FindingCategory[])
    .map((category) => [category, findings.filter((f) => f.category === category)] as const)
    .filter(([, items]) => items.length > 0);

  return (
    <section aria-labelledby="other-title">
      <h2 id="other-title" className="text-xl font-semibold tracking-tight">
        Weitere Funde <span className="tabular text-base font-normal text-ink-muted">({findings.length})</span>
      </h2>
      <p className="text-sm text-ink-secondary">
        Was von außen sichtbar ist, aber noch keinem Dienst der Datenbank zugeordnet werden kann. Lieber roh als geraten.
      </p>
      <div className="mt-4 grid gap-6 md:grid-cols-2">
        {groups.map(([category, items]) => (
          <div key={category}>
            <h3 className="text-sm font-medium">{CATEGORY[category]}</h3>
            <FindingItems items={items} />
          </div>
        ))}
      </div>
    </section>
  );
}

const VISIBLE = 6;
// Aussagekräftiges zuerst: Netzbetreiber und eingebundene Werkzeuge vor Mail- und Nameservern
const ORDER = ["SPF_NET", "WEB", "SCRIPT", "TECH", "ASN", "CNAME", "MX", "SPF", "NS", "CAA"];

function FindingItems({ items }: { items: ScanFinding[] }) {
  const sorted = [...items].sort((a, b) => ORDER.indexOf(a.record) - ORDER.indexOf(b.record));
  const shown = sorted.slice(0, VISIBLE);
  const hidden = sorted.slice(VISIBLE);
  return (
    <>
      <ul className="mt-2 space-y-1.5">
        {shown.map((finding) => (
          <Item key={`${finding.record}-${finding.value}`} finding={finding} />
        ))}
      </ul>
      {hidden.length > 0 && (
        <details className="mt-2">
          <summary className="cursor-pointer text-xs text-ink-secondary underline focus-visible:outline-2 focus-visible:outline-accent">
            {hidden.length} weitere anzeigen
          </summary>
          <ul className="mt-2 space-y-1.5">
            {hidden.map((finding) => (
              <Item key={`${finding.record}-${finding.value}`} finding={finding} />
            ))}
          </ul>
        </details>
      )}
    </>
  );
}

// Beim Netz eines Absenders zählt der Netzbetreiber, der lange SPF-Eintrag steht im Titel
function Item({ finding }: { finding: ScanFinding }) {
  const [source, network] = finding.record === "SPF_NET" ? finding.value.split(" → ") : [null, finding.value];
  return (
    <li className="text-sm" title={source ? `Über ${source}` : undefined}>
      <span className="text-xs text-ink-muted">{RECORD_LABEL[finding.record] ?? finding.record}: </span>
      <span className="break-all font-mono text-xs">{network ?? finding.value}</span>
    </li>
  );
}
