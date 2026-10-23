import type { QuickCheckResult } from "@/lib/types";

interface Signal {
  title: string;
  text: string;
  value: string;
  tone: "good" | "info" | "warn";
}

const TONE: Record<Signal["tone"], string> = {
  good: "Gut",
  info: "Info",
  warn: "Beachten",
};

// Was die Domain technisch verrät, ohne Bewertung als Risiko
export default function Signals({ result }: { result: QuickCheckResult }) {
  const { signals } = result;
  const network = result.other_findings.find((f) => f.record === "ASN")?.value ??
    result.services.flatMap((s) => s.findings).find((f) => f.record === "ASN")?.value;
  const cookies = signals.cookies ?? [];
  const items: Signal[] = [
    {
      title: "Netzbetreiber der Website",
      text: "Wem die IP-Adresse der Website gehört, auch wenn der Vertragspartner ein anderer ist.",
      value: network ? `${network}${signals.website_ip ? ` · ${signals.website_ip}` : ""}` : "Nicht ermittelt",
      tone: "info",
    },
    {
      title: "DNSSEC",
      text: "Signierte DNS-Antworten. Erschwert es, die Domain auf fremde Server umzuleiten.",
      value: signals.dnssec ? "Aktiv" : "Nicht aktiv",
      tone: signals.dnssec ? "good" : "warn",
    },
    {
      title: "TLS-Zertifikat",
      text: "Wer das Zertifikat der Website ausgestellt hat. Verarbeitet keine Daten des Unternehmens.",
      value: signals.tls_issuer ?? "Nicht ermittelt",
      tone: "info",
    },
    {
      title: "Cookies vor der Einwilligung",
      text: "Cookies, die die Startseite beim ersten Aufruf setzt, bevor jemand im Cookie-Banner zustimmt.",
      value: cookies.length ? cookies.join(", ") : "Keine erkannt",
      tone: cookies.length ? "warn" : "good",
    },
    {
      title: "Reverse-DNS",
      text: "Name, auf den die IP-Adresse zurückverweist. Bei großen Netzen oft nicht gesetzt.",
      value: signals.reverse_dns ?? "Kein Eintrag",
      tone: "info",
    },
  ];

  return (
    <section aria-labelledby="signals-title">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-muted">Technische Signale</p>
      <h2 id="signals-title" className="mt-1 text-2xl font-semibold tracking-tight">
        Was die Domain technisch verrät.
      </h2>
      <ul className="mt-5 divide-y divide-hairline rounded-lg border border-hairline">
        {items.map((item) => (
          <li key={item.title} className="grid gap-1 px-4 py-3 sm:grid-cols-[1fr_auto] sm:gap-6">
            <div>
              <p className="font-medium">{item.title}</p>
              <p className="text-sm text-ink-secondary">{item.text}</p>
              <p className="mt-1 break-all font-mono text-xs">{item.value}</p>
            </div>
            <span
              className={`self-start justify-self-start rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                item.tone === "good" ? "border-accent text-accent" : item.tone === "warn" ? "border-critical text-critical" : "border-baseline text-ink-secondary"
              }`}
            >
              {TONE[item.tone]}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
