import type { Metadata } from "next";
import { Suspense } from "react";

import QuickCheckView from "@/components/quickcheck/QuickCheckView";
import Shell from "@/components/Shell";

export const metadata: Metadata = { title: "Schnellcheck · Sovereignty Assessment Copilot" };

// Mit cacheComponents liegt der Zugriff auf searchParams hinter einer Suspense-Grenze
export default function QuickCheckPage(props: PageProps<"/schnellcheck">) {
  return (
    <Suspense fallback={<Shell>{null}</Shell>}>
      <QuickCheck searchParams={props.searchParams} />
    </Suspense>
  );
}

async function QuickCheck({ searchParams }: { searchParams: PageProps<"/schnellcheck">["searchParams"] }) {
  const { domain } = await searchParams;
  const value = (Array.isArray(domain) ? domain[0] : domain)?.trim() ?? "";
  return <QuickCheckView key={value} domain={value} />;
}
