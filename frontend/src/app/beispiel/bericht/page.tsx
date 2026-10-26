import type { Metadata } from "next";

import ReportView from "@/components/report/ReportView";

export const metadata: Metadata = { title: "Bericht Musterbank AG · Sovereignty Assessment Copilot" };

export default function ExampleReportPage() {
  return <ReportView source="demo" back="/beispiel" />;
}
