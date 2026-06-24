import type { RepoCreate, RepoResponse, IndexingStatus, QueryRequest, QueryResponse, ApiError } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try { const err: ApiError = await res.json(); message = err.detail ?? message; } catch {}
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export async function submitRepo(payload: RepoCreate): Promise<RepoResponse> {
  return apiFetch<RepoResponse>("/repos", { method: "POST", body: JSON.stringify(payload) });
}

export async function getRepoStatus(repoId: string): Promise<IndexingStatus> {
  return apiFetch<IndexingStatus>(`/repos/${repoId}`);
}

export async function queryRepo(payload: QueryRequest): Promise<QueryResponse> {
  return apiFetch<QueryResponse>("/query", { method: "POST", body: JSON.stringify(payload) });
}
