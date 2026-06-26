-- =============================================================================
-- Migration 002 — match_chunks RPC function
-- RAG Codebase Q&A Tool
--
-- Run this in Supabase Dashboard → SQL Editor AFTER migration 001.
--
-- Creates a PostgreSQL function callable via supabase.rpc('match_chunks', {...})
-- that performs a pgvector cosine similarity search scoped to a single repo.
--
-- Why a Postgres function instead of a raw SELECT?
--   The Supabase PostgREST client's .order() method only accepts plain column
--   names — it cannot express `ORDER BY embedding <=> $1`. A Postgres function
--   sidesteps this limitation and keeps the vector math server-side where it
--   belongs (close to the index).
-- =============================================================================

CREATE OR REPLACE FUNCTION match_chunks(
    query_embedding  VECTOR(384),
    match_repo_id    UUID,
    match_count      INT DEFAULT 5
)
RETURNS TABLE (
    id            UUID,
    repo_id       UUID,
    file_path     TEXT,
    language      TEXT,
    start_line    INTEGER,
    end_line      INTEGER,
    content       TEXT,
    chunk_type    TEXT,
    similarity    FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        repo_id,
        file_path,
        language,
        start_line,
        end_line,
        content,
        chunk_type,
        1 - (embedding <=> query_embedding) AS similarity
    FROM chunks
    WHERE repo_id = match_repo_id
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;


-- =============================================================================
-- Verification query (run manually)
-- =============================================================================
-- SELECT routine_name FROM information_schema.routines
--   WHERE routine_schema = 'public' AND routine_name = 'match_chunks';