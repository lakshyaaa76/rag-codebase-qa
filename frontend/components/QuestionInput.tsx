"use client";

import { useRef, useState } from "react";

interface QuestionInputProps {
  onSubmit: (question: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

export default function QuestionInput({
  onSubmit,
  isLoading = false,
  disabled = false,
}: QuestionInputProps) {
  const [question, setQuestion] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleSubmit() {
    const q = question.trim();
    if (!q || isLoading || disabled) return;
    onSubmit(q);
    setQuestion("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  const isActive = !disabled && !isLoading;

  return (
    <div className="flex gap-0 border-t border-terminal-border pt-4">
      {/* Blinking cursor prefix */}
      <span className="flex items-center px-3 py-2 terminal-input border-r-0 text-terminal-cyan text-xs select-none">
        <span className={isActive ? "animate-blink" : "opacity-30"}>▋</span>
      </span>
      <input
        ref={inputRef}
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={disabled ? "Index a repository first..." : "Ask a question about this codebase..."}
        disabled={!isActive}
        autoComplete="off"
        spellCheck={false}
        className="terminal-input flex-1 px-3 py-2 text-xs border-r-0"
      />
      <button
        type="button"
        onClick={handleSubmit}
        disabled={!isActive || !question.trim()}
        className="terminal-btn border-l-0 min-w-[80px]"
      >
        {isLoading ? "RUNNING" : "QUERY"}
      </button>
    </div>
  );
}