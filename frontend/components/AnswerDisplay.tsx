"use client";

import { useState } from "react";
import type { QueryResponse } from "@/types";
import CitationCard from "./CitationCard";

interface AnswerDisplayProps {
  question: string;
  response: QueryResponse;
}

export default function AnswerDisplay({ question, response }: AnswerDisplayProps) {
  const [citationsOpen, setCitationsOpen] = useState(true);

  return (
    <div className="flex flex-col gap-3 animate-fade-up">
      {/* Question echo */}
      <div className="flex gap-2 text-xs font-mono">
        <span className="text-terminal-cyan shrink-0">▋</span>
        <span className="text-terminal-muted">{question}</span>
      </div>

      {/* Answer block */}
      <div className="terminal-panel border-l-2 border-l-terminal-cyan px-4 py-3">
        <p className="terminal-label mb-2">// RESPONSE</p>
        <p className="text-terminal-text text-xs font-mono leading-relaxed whitespace-pre-wrap">
          {response.answer}
        </p>
      </div>

      {/* Citations */}
      {response.citations.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <button
            type="button"
            onClick={() => setCitationsOpen((v) => !v)}
            className="terminal-label flex items-center gap-2 hover:text-terminal-cyan
                       transition-colors duration-100 text-left w-fit"
          >
            <span>{citationsOpen ? "▼" : "▶"}</span>
            <span>// SOURCES ({response.citations.length})</span>
          </button>

          {citationsOpen && (
            <div className="flex flex-col gap-1.5 animate-fade-in">
              {response.citations.map((citation, i) => (
                <CitationCard key={citation.id} citation={citation} index={i + 1} />
              ))}
            </div>
          )}
        </div>
      )}

      {response.citations.length === 0 && (
        <p className="text-terminal-muted text-xs font-mono">
          // no source citations returned
        </p>
      )}
    </div>
  );
}