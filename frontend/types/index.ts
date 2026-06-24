export type RepoStatus = "pending" | "indexing" | "ready" | "failed";

export interface RepoCreate { github_url: string; }

export interface RepoResponse {
  id: string; github_url: string; owner: string; repo_name: string;
  default_branch: string; status: RepoStatus; error_message: string | null;
  file_count: number | null; chunk_count: number | null;
  created_at: string; updated_at: string;
}

export interface IndexingStatus {
  id: string; status: RepoStatus;
  file_count: number | null; chunk_count: number | null; error_message: string | null;
}

export interface QueryRequest { repo_id: string; question: string; top_k?: number; }

export interface ChunkCitation {
  id: string; file_path: string; start_line: number; end_line: number;
  language: string | null; content: string; score: number;
}

export interface QueryResponse { answer: string; citations: ChunkCitation[]; }
export interface ApiError { detail: string; }
