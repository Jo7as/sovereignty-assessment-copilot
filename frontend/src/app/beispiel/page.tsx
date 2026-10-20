import type { Metadata } from "next";

import DemoView from "@/components/DemoView";

export const metadata: Metadata = { title: "Beispiel Musterbank AG · Sovereignty Assessment Copilot" };

export default function ExamplePage() {
  return <DemoView />;
}
