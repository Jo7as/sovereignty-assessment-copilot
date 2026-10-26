// Ein Blatt entspricht im Druck einer Seite. Passt der Inhalt nicht, bricht der Browser um.
export function Sheet({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <section aria-label={label} className="report-sheet text-[13px] leading-relaxed text-ink">
      {children}
    </section>
  );
}

export function SheetTitle({ eyebrow, children }: { eyebrow: string; children: React.ReactNode }) {
  return (
    <header className="mb-6 border-b border-hairline pb-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-ink-muted">{eyebrow}</p>
      <h2 className="mt-1 text-2xl font-semibold tracking-tight">{children}</h2>
    </header>
  );
}
