import Link from "next/link";

import CreateAssessmentForm from "@/components/landing/CreateAssessmentForm";
import DomainForm from "@/components/quickcheck/DomainForm";
import { Comparison, Facts, Objectives, Section, Steps } from "@/components/landing/Explain";
import HeroPreview from "@/components/landing/HeroPreview";
import { Faq, Principles, WhyNow } from "@/components/landing/Trust";
import Shell from "@/components/Shell";

export default function Home() {
  return (
    <Shell
      wide
      actions={
        <nav aria-label="Seitenbereiche" className="flex items-center gap-5 text-sm">
          <a href="#ablauf" className="hidden text-ink-secondary hover:text-ink md:inline">
            Ablauf
          </a>
          <a href="#methodik" className="hidden text-ink-secondary hover:text-ink md:inline">
            Methodik
          </a>
          <Link href="/beispiel" className="text-ink-secondary hover:text-ink">
            Beispiel
          </Link>
          <a
            href="#start"
            className="hidden rounded-md bg-accent px-3 py-1.5 font-medium text-accent-ink sm:inline-block hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Website prüfen
          </a>
        </nav>
      }
    >
      <section id="start" aria-labelledby="hero-title" className="scroll-mt-8">
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-16 sm:px-6 lg:grid-cols-[1fr_1fr] lg:px-8 lg:py-24">
          <div>
            <p className="text-sm font-medium text-accent">Für Banken, Versicherer und Unternehmen unter NIS2</p>
            <h1 id="hero-title" className="mt-3 text-balance text-4xl font-semibold tracking-tight sm:text-5xl">
              Wie abhängig ist Ihr Unternehmen von <span className="whitespace-nowrap">IT-Anbietern</span>{" "}
              außerhalb der EU?
            </h1>
            <p className="mt-5 max-w-xl text-lg text-ink-secondary">
              Bewertet Ihren IT-Bestand nach dem Cloud Sovereignty Framework der EU-Kommission,
              prüft DORA und NIS2 und leitet eine Roadmap ab. Jede Aussage mit Quelle.
            </p>
            <div className="mt-8">
              <DomainForm />
            </div>
            <p className="mt-4 text-sm text-ink-muted">
              Kein Konto nötig · Ergebnis in etwa 20 Sekunden ·{" "}
              <a href="#ohne-website" className="underline hover:text-ink">
                Ohne Website starten
              </a>{" "}
              ·{" "}
              <Link href="/beispiel" className="underline hover:text-ink">
                Beispiel Musterbank
              </Link>
            </p>
          </div>
          <HeroPreview />
        </div>
        <div className="border-t border-hairline">
          <Facts />
        </div>
      </section>

      <Section id="ablauf" title="In drei Schritten zur Roadmap" intro="Ein belastbarer erster Stand aus Fragebogen und IT-Bestand, als Einstieg vor einem mehrwöchigen Assessment mit Workshops.">
        <Steps />
      </Section>

      <Section tone="surface" id="zielbereiche" title="Acht Zielbereiche, eine Stufe von 0 bis 4" intro="Jeder Dienst wird in jedem Zielbereich bewertet. Die Gewichte stammen aus dem Rahmenwerk der EU-Kommission.">
        <Objectives />
      </Section>

      <Section id="abgrenzung" title="Von innen statt nur von außen" intro="Die Website eines Unternehmens zeigt nur einen kleinen Teil seiner IT. Die kritischen Abhängigkeiten liegen meist dahinter.">
        <Comparison />
      </Section>

      <Section tone="surface" id="warum-jetzt" title="Warum jetzt" intro="Abhängigkeiten von Anbietern sind keine reine Strategiefrage mehr. Für viele Unternehmen sind sie Aufsichtsthema.">
        <WhyNow />
      </Section>

      <Section id="methodik" title="So arbeitet das Werkzeug" intro="Ein Ergebnis ist nur so gut wie seine Grundlage. Deshalb sind alle Regeln offen und jede Angabe ist belegt.">
        <Principles />
      </Section>

      <Section tone="surface" id="fragen" title="Häufige Fragen">
        <Faq />
      </Section>

      <section aria-labelledby="final-title" className="border-t border-hairline bg-surface">
        <div className="mx-auto grid max-w-7xl gap-12 px-4 py-16 sm:px-6 lg:grid-cols-2 lg:px-8">
          <div>
            <h2 id="final-title" className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Bereit für einen ersten Stand?
            </h2>
            <p className="mt-2 text-ink-secondary">Mit der Website starten und die Funde ins Assessment übernehmen.</p>
            <div className="mt-6">
              <DomainForm />
            </div>
          </div>
          <div id="ohne-website" className="scroll-mt-8">
            <h3 className="text-lg font-semibold">Ohne Website starten</h3>
            <p className="mt-2 text-ink-secondary">Direkt mit Fragebogen und IT-Bestand, ohne Außenscan.</p>
            <div className="mt-6">
              <CreateAssessmentForm />
            </div>
          </div>
        </div>
      </section>
    </Shell>
  );
}
