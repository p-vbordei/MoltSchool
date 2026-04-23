import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "Kindred — a shared notebook your team's AI reads",
  description:
    "Write once. Every AI on your team knows. A shared notebook where you write and every teammate's AI reads.",
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
