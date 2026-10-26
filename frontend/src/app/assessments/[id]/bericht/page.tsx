import { notFound } from "next/navigation";
import { Suspense } from "react";

import ReportView from "@/components/report/ReportView";

// Wie die Assessment-Seite: Zugriff auf `params` hinter einer Suspense-Grenze (cacheComponents)
export default function ReportPage(props: PageProps<"/assessments/[id]/bericht">) {
  return (
    <Suspense fallback={<p role="status" className="py-24 text-center">Der Bericht wird geladen …</p>}>
      <Report params={props.params} />
    </Suspense>
  );
}

async function Report({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // Nur Ziffern: Die Nummer geht in die Adresse der API
  if (!/^\d+$/.test(id)) notFound();
  return <ReportView source={Number(id)} back={`/assessments/${id}`} />;
}
