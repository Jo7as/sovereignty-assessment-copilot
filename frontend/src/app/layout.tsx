import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sovereignty Assessment Copilot",
  description:
    "Bewertet die Abhängigkeit eines Unternehmens von außereuropäischen IT-Anbietern nach dem EU Cloud Sovereignty Framework und leitet eine Roadmap ab.",
};

// Systemschrift statt Webfonts: Ein Werkzeug für digitale Souveränität lädt keine
// Schriften von Servern außerhalb der EU.
export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="de" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
