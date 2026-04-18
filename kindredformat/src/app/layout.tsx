import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KAF — Kindred Artifact Format",
  description:
    "KAF 0.1 — a minimal portable envelope for agent-shareable knowledge artifacts.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="container">
            <a className="brand" href="/">KAF</a>
            <nav>
              <a href="/">Spec</a>
              <a href="/examples/">Examples</a>
              <a href="/implementers/">Implementers</a>
              <a
                href="https://github.com/kindred/kindred"
                target="_blank"
                rel="noreferrer"
              >
                GitHub
              </a>
            </nav>
          </div>
        </header>
        <main className="container prose">{children}</main>
        <footer className="site-footer">
          <div className="container">
            <p>
              KAF 0.1 — draft spec. Reference implementation at{" "}
              <a href="https://github.com/kindred/kindred">github.com/kindred/kindred</a>.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
