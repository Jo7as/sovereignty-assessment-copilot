import type { ReportResponse } from "@/lib/types";

import Cover from "./Cover";
import Summary from "./Summary";

export default function ReportDocument({ data }: { data: ReportResponse }) {
  return (
    <article aria-label={`Bericht ${data.assessment.name}`} className="px-4 pb-12 print:p-0">
      <Cover data={data} />
      <Summary report={data.report} />
    </article>
  );
}
