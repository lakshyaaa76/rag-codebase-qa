import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "RAG Codebase Q&A",
  description: "Ask natural-language questions about any GitHub repository.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen bg-gray-50 text-gray-900`}>
        <header className="border-b border-gray-200 bg-white px-6 py-4">
          <div className="mx-auto max-w-4xl">
            <span className="text-lg font-semibold text-gray-900">RAG Codebase Q&amp;A</span>
          </div>
        </header>
        <main className="mx-auto max-w-4xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
