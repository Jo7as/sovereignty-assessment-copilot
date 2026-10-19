import { notFound } from "next/navigation";
import { Suspense } from "react";

import AssessmentWorkspace from "@/components/AssessmentWorkspace";
import Shell from "@/components/Shell";

// Mit cacheComponents liegt der Zugriff auf `params` hinter einer Suspense-Grenze: Die
// Hülle mit Kopf und Ladeanzeige ist statisch, der Inhalt folgt je Aufruf.
export default function AssessmentPage(props: PageProps<"/assessments/[id]">) {
  return (
    <Suspense
      fallback={
        <Shell>
          <p role="status" className="py-24 text-center text-ink-secondary">
            Das Assessment wird geladen …
          </p>
        </Shell>
      }
    >
      <Workspace params={props.params} />
    </Suspense>
  );
}

async function Workspace({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // Nur Ziffern: Die Nummer geht in die Adresse der API
  if (!/^\d+$/.test(id)) notFound();
  return <AssessmentWorkspace id={Number(id)} />;
}
