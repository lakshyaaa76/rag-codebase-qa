"use client";

import { useState } from "react";

interface RepoFormProps {
  onSubmit: (githubUrl: string) => void;
  isLoading?: boolean;
}

export default function RepoForm({ onSubmit, isLoading = false }: RepoFormProps) {
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  function validate(value: string): string | null {
    if (!value.trim()) return "URL required";
    if (!value.startsWith("https://github.com/")) return "Must be a github.com URL";
    const parts = value.replace("https://github.com/", "").split("/");
    if (parts.length < 2 || !parts[0] || !parts[1]) return "Must be github.com/owner/repo";
    return null;
  }

  function handleSubmit() {
    const err = validate(url);
    if (err) { setError(err); return; }
    setError(null);
    onSubmit(url.trim());
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSubmit();
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-0">
        {/* Prompt prefix */}
        <span className="terminal-input border-r-0 px-3 py-2 text-terminal-cyan text-xs select-none flex items-center">
          $
        </span>
        <input
          type="url"
          value={url}
          onChange={(e) => { setUrl(e.target.value); setError(null); }}
          onKeyDown={handleKeyDown}
          placeholder="https://github.com/owner/repo"
          disabled={isLoading}
          autoComplete="off"
          spellCheck={false}
          className="terminal-input flex-1 px-3 py-2 text-xs border-r-0"
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isLoading || !url.trim()}
          className="terminal-btn border-l-0"
        >
          {isLoading ? "INDEXING" : "INDEX"}
        </button>
      </div>
      {error && (
        <p className="text-terminal-red text-xs font-mono pl-6 animate-fade-in">
          ✗ {error}
        </p>
      )}
    </div>
  );
}