import Link from "next/link";

// Weg vom Ergebnis zum Bericht, der sich als PDF speichern lässt
export default function ReportLink({ href, className = "" }: { href: string; className?: string }) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-2 rounded-md border border-baseline px-3 py-1.5 text-sm hover:bg-surface focus-visible:outline-2 focus-visible:outline-accent ${className}`}
    >
      <svg viewBox="0 0 16 16" className="h-4 w-4" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.5">
        <path d="M4 1.5h5.5L12.5 4.5v10h-8.5z M9.5 1.5v3h3 M6 8.5h4.5 M6 11h4.5" />
      </svg>
      Bericht als PDF
    </Link>
  );
}
