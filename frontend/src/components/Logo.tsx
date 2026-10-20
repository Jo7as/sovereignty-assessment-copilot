// Bildmarke: vier Felder der Stufenskala, ein Verweis auf die Heatmap. Bewusst ohne
// EU-Sterne oder Schild, die jedes Souveränitätsprodukt nutzt.
export default function Logo({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <rect x="1" y="1" width="10" height="10" rx="1.5" fill="var(--level-1)" />
      <rect x="13" y="1" width="10" height="10" rx="1.5" fill="var(--level-2)" />
      <rect x="1" y="13" width="10" height="10" rx="1.5" fill="var(--level-3)" />
      <rect x="13" y="13" width="10" height="10" rx="1.5" fill="var(--level-4)" />
    </svg>
  );
}
