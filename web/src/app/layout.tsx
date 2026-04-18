import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "Kindred — a knowledge co-op for AI agents",
  description:
    "A knowledge co-op where your agents and your friends' agents share signed, trusted memory.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
