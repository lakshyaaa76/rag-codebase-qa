"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { submitRepo, getRepoStatus, queryRepo } from "@/lib/api";
import type { RepoResponse, IndexingStatus, QueryResponse, RepoStatus } from "@/types";

import RepoForm from "@/components/RepoForm";
import QuestionInput from "@/components/QuestionInput";
import StatusBadge from "@/components/StatusBadge";
import AnswerDisplay from "@/components/AnswerDisplay";

interface ChatEntry {
  id: string;
  question: string;
  response: QueryResponse;
}

const POLL_INTERVAL_MS = 2000;

export default function HomePage() {
  // --- Repo state ---
  const [repo, setRepo] = useState<RepoResponse | null>(null);
  const [indexingStatus, setIndexingStatus] = useState<IndexingStatus | null>(null);
  const [repoLoading, setRepoLoading] = useState(false);
  const [repoError, setRepoError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // --- Query state ---
  const [chat, setChat] = useState<ChatEntry[]>([]);
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);

  // --- Scroll anchor ---
  const bottomRef = useRef<HTMLDivElement>(null);

  // Derived status — use live polling status if available, else repo status
  const currentStatus: RepoStatus =
    indexingStatus?.status ?? repo?.status ?? "pending";

  const isReady = currentStatus === "ready";

  // --- Stop polling ---
  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  // --- Poll indexing status ---
  const startPolling = useCallback((repoId: string) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const status = await getRepoStatus(repoId);
        setIndexingStatus(status);
        if (status.status === "ready" || status.status === "failed") {
          stopPolling();
        }
      } catch {
        // Silently retry — network blip shouldn't stop polling
      }
    }, POLL_INTERVAL_MS);
  }, []);

  // Cleanup on unmount
  useEffect(() => () => stopPolling(), []);

  // Scroll to bottom whenever chat grows
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, queryLoading]);

  // --- Submit repo ---
  async function handleRepoSubmit(url: string) {
    setRepoLoading(true);
    setRepoError(null);
    setIndexingStatus(null);
    setChat([]);
    stopPolling();
    try {
      const res = await submitRepo({ github_url: url });
      setRepo(res);
      if (res.status === "pending" || res.status === "indexing") {
        startPolling(res.id);
      }
    } catch (err) {
      setRepoError(err instanceof Error ? err.message : "Failed to submit repository.");
    } finally {
      setRepoLoading(false);
    }
  }

  // --- Submit question ---
  async function handleQuestion(question: string) {
    if (!repo || !isReady) return;
    setQueryLoading(true);
    setQueryError(null);
    try {
      const response = await queryRepo({
        repo_id: repo.id,
        question,
        top_k: 5,
      });
      setChat((prev) => [
        ...prev,
        { id: crypto.randomUUID(), question, response },
      ]);
    } catch (err) {
      setQueryError(err instanceof Error ? err.message : "Query failed.");
    } finally {
      setQueryLoading(false);
    }
  }

  // Displayed file/chunk counts — prefer live status over initial response
  const fileCount  = indexingStatus?.file_count  ?? repo?.file_count;
  const chunkCount = indexingStatus?.chunk_count ?? repo?.chunk_count;
  const errorMsg   = indexingStatus?.error_message ?? repo?.error_message;

  return (
    <div className="h-full flex overflow-hidden">

      {/* ================================================================
          LEFT PANEL — repo info + controls
      ================================================================ */}
      <aside className="w-72 shrink-0 flex flex-col border-r border-terminal-border
                        bg-terminal-panel overflow-y-auto">

        {/* Header */}
        <div className="border-b border-terminal-border px-4 py-3">
          <p className="text-terminal-cyan text-xs uppercase tracking-widest text-glow-cyan">
            RAG // CODEBASE Q&amp;A
          </p>
          <p className="text-terminal-muted text-xs mt-0.5">
            v0.1.0 // TERMINAL
          </p>
        </div>

        {/* Repo input */}
        <div className="px-4 py-4 border-b border-terminal-border flex flex-col gap-3">
          <p className="terminal-label">// REPOSITORY</p>
          <RepoForm onSubmit={handleRepoSubmit} isLoading={repoLoading} />
          {repoError && (
            <p className="text-terminal-red text-xs font-mono animate-fade-in">
              ✗ {repoError}
            </p>
          )}
        </div>

        {/* Repo status block — shown once a repo is submitted */}
        {repo && (
          <div className="px-4 py-4 border-b border-terminal-border flex flex-col gap-3
                          animate-fade-in">
            <div className="flex items-center justify-between">
              <p className="terminal-label">// STATUS</p>
              <StatusBadge status={currentStatus} />
            </div>

            {/* Repo name */}
            <div className="flex flex-col gap-0.5">
              <p className="terminal-label">REPO</p>
              <p className="text-terminal-code text-xs font-mono truncate">
                {repo.owner}/{repo.repo_name}
              </p>
            </div>

            {/* Branch */}
            <div className="flex flex-col gap-0.5">
              <p className="terminal-label">BRANCH</p>
              <p className="text-terminal-code text-xs font-mono">
                {repo.default_branch}
              </p>
            </div>

            {/* Stats — shown when ready */}
            {isReady && (
              <div className="grid grid-cols-2 gap-2 animate-fade-in">
                <div className="terminal-panel p-2 flex flex-col gap-0.5">
                  <p className="terminal-label">FILES</p>
                  <p className="text-terminal-cyan text-sm font-mono">
                    {fileCount ?? "—"}
                  </p>
                </div>
                <div className="terminal-panel p-2 flex flex-col gap-0.5">
                  <p className="terminal-label">CHUNKS</p>
                  <p className="text-terminal-cyan text-sm font-mono">
                    {chunkCount ?? "—"}
                  </p>
                </div>
              </div>
            )}

            {/* Indexing progress indicator */}
            {(currentStatus === "pending" || currentStatus === "indexing") && (
              <div className="flex items-center gap-2 animate-fade-in">
                <span className="h-1.5 w-1.5 bg-terminal-amber animate-pulse-slow" />
                <p className="text-terminal-amber text-xs font-mono">
                  {currentStatus === "indexing" ? "Indexing codebase..." : "Queued..."}
                </p>
              </div>
            )}

            {/* Error message */}
            {currentStatus === "failed" && errorMsg && (
              <p className="text-terminal-red text-xs font-mono break-words animate-fade-in">
                ✗ {errorMsg}
              </p>
            )}
          </div>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Footer */}
        <div className="px-4 py-3 border-t border-terminal-border">
          <p className="text-terminal-muted text-xs font-mono">
            // powered by grok + pgvector
          </p>
        </div>
      </aside>

      {/* ================================================================
          MAIN AREA — chat history + question input
      ================================================================ */}
      <main className="flex-1 flex flex-col overflow-hidden">

        {/* Top bar */}
        <div className="border-b border-terminal-border px-6 py-3 flex items-center
                        justify-between shrink-0">
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 bg-terminal-red" />
            <span className="h-2 w-2 bg-terminal-amber" />
            <span className="h-2 w-2 bg-terminal-green" />
            <span className="text-terminal-muted text-xs font-mono ml-2">
              {repo ? `${repo.owner}/${repo.repo_name}` : "no repository loaded"}
            </span>
          </div>
          {isReady && (
            <span className="text-terminal-green text-xs font-mono text-glow-green">
              ● READY
            </span>
          )}
        </div>

        {/* Chat scroll area */}
        <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-6">

          {/* Empty state */}
          {chat.length === 0 && !queryLoading && (
            <div className="flex-1 flex flex-col items-center justify-center gap-4
                            text-center animate-fade-in">
              {!repo && (
                <>
                  <div className="text-terminal-border text-6xl select-none">⌘</div>
                  <p className="text-terminal-muted text-xs font-mono">
                    // enter a github repository url in the left panel
                  </p>
                  <p className="text-terminal-muted text-xs font-mono">
                    // then ask questions about the codebase
                  </p>
                </>
              )}
              {repo && !isReady && (
                <p className="text-terminal-muted text-xs font-mono animate-pulse-slow">
                  // waiting for indexing to complete...
                </p>
              )}
              {repo && isReady && (
                <p className="text-terminal-muted text-xs font-mono">
                  // repository indexed — ask a question below
                </p>
              )}
            </div>
          )}

          {/* Chat entries */}
          {chat.map((entry) => (
            <AnswerDisplay
              key={entry.id}
              question={entry.question}
              response={entry.response}
            />
          ))}

          {/* Loading indicator */}
          {queryLoading && (
            <div className="flex items-center gap-2 animate-fade-in">
              <span className="text-terminal-cyan text-xs font-mono">▋</span>
              <span className="text-terminal-muted text-xs font-mono animate-pulse-slow">
                querying...
              </span>
            </div>
          )}

          {/* Query error */}
          {queryError && !queryLoading && (
            <div className="terminal-panel border-l-2 border-l-terminal-red px-4 py-3
                            animate-fade-in">
              <p className="text-terminal-red text-xs font-mono">
                ✗ ERROR: {queryError}
              </p>
            </div>
          )}

          {/* Scroll anchor */}
          <div ref={bottomRef} />
        </div>

        {/* Question input — pinned to bottom */}
        <div className="shrink-0 px-6 pb-4">
          <QuestionInput
            onSubmit={handleQuestion}
            isLoading={queryLoading}
            disabled={!isReady}
          />
        </div>
      </main>
    </div>
  );
}