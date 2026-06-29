import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CODEBASE Q&A // RAG TERMINAL",
  description: "Ask natural-language questions about any GitHub repository.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full overflow-hidden bg-terminal-bg text-terminal-text font-mono">
        {children}
      </body>
    </html>
  );
}