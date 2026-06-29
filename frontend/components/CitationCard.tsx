"use client";

import { useState } from "react";
import type { ChunkCitation } from "@/types";

interface CitationCardProps {
  citation: ChunkCitation;
  index: number;
}

export default function CitationCard({ citation, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const scorePercent = Math.round(citation.score * 100);

  return (
    <div className="terminal-panel animate-fade-up border-l-2 border-l-terminal-cyan">
      {/* Header row */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-3 px-3 py-2 hover:bg-terminal-dim
                   transition-colors duration-100 text-left"
      >
        {/* Citation index */}
        <span className="text-terminal-cyan text-xs font-mono text-glow-cyan shrink-0">
          [{index}]
        </span>

        {/* File path */}
        <span className="text-terminal-code text-xs font-mono truncate flex-1">
          {citation.file_path}
        </span>

        {/* Line range */}
        <span className="text-terminal-muted text-xs font-mono shrink-0 hidden sm:inline">
          L{citation.start_line}–{citation.end_line}
        </span>

        {/* Language */}
        {citation.language && (
          <span className="text-terminal-muted text-xs font-mono uppercase tracking-wider
                           border border-terminal-border px-1.5 py-0.5 shrink-0">
            {citation.language}
          </span>
        )}

        {/* Score */}
        <span
          className={`text-xs font-mono shrink-0 ${
            scorePercent >= 80
              ? "text-terminal-green"
              : scorePercent >= 60
              ? "text-terminal-amber"
              : "text-terminal-muted"
          }`}
        >
          {scorePercent}%
        </span>

        {/* Expand toggle */}
        <span className="text-terminal-muted text-xs shrink-0">
          {expanded ? "▲" : "▼"}
        </span>
      </button>

      {/* Code block */}
      {expanded && (
        <div className="border-t border-terminal-border animate-fade-in">
          <pre className="overflow-x-auto px-4 py-3 text-xs leading-relaxed
                          text-terminal-code font-mono whitespace-pre">
            <code>{citation.content}</code>
          </pre>
        </div>
      )}
    </div>
  );
}