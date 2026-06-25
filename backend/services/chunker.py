"""
Chunking service.

Splits fetched file content into semantically meaningful chunks for embedding.

Strategy (decided in Phase 0):
  - AST-aware for Python and JavaScript/TypeScript:
      Extract top-level function definitions and class definitions.
      Methods inside a class are extracted as sub-chunks of that class.
      If any extracted node exceeds MAX_AST_CHUNK_LINES, it is further split
      using the sliding window algorithm.
  - Sliding window fallback for all other languages:
      Window size: WINDOW_SIZE lines, overlap: WINDOW_OVERLAP lines.

Public API:
  chunk_file(fetched_file: FetchedFile) -> list[ChunkResult]

ChunkResult carries every field the `chunks` DB table expects, except
`id`, `repo_id`, and `embedding` which are assigned at insert time.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Literal

from services.ingestion import FetchedFile

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WINDOW_SIZE = 60          # lines per sliding-window chunk
WINDOW_OVERLAP = 15       # lines of overlap between consecutive chunks
MAX_AST_CHUNK_LINES = 80  # AST node longer than this gets split further

ChunkType = Literal["function", "class", "block", "file_header", "sliding_window"]

# Languages that use AST-aware chunking
_AST_LANGUAGES = {"python", "javascript", "typescript"}


# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class ChunkResult:
    """
    A single chunk ready to be embedded and stored.

    All fields map 1-to-1 to columns in the `chunks` table.
    `repo_id` and `embedding` are added at insert time by the indexer.
    """
    file_path: str
    language: str | None
    start_line: int          # 1-indexed, inclusive
    end_line: int            # 1-indexed, inclusive
    content: str             # raw text of the chunk
    content_hash: str        # SHA-256 hex of content
    chunk_index: int         # 0-based position within the file
    chunk_type: ChunkType


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _make_chunk(
    lines: list[str],
    file_path: str,
    language: str | None,
    start_line: int,   # 1-indexed
    end_line: int,     # 1-indexed
    chunk_index: int,
    chunk_type: ChunkType,
) -> ChunkResult:
    """Build a ChunkResult from a slice of the file's line list."""
    # lines list is 0-indexed; start_line/end_line are 1-indexed
    content = "\n".join(lines[start_line - 1 : end_line])
    return ChunkResult(
        file_path=file_path,
        language=language,
        start_line=start_line,
        end_line=end_line,
        content=content,
        content_hash=_sha256(content),
        chunk_index=chunk_index,
        chunk_type=chunk_type,
    )


def _sliding_window(
    lines: list[str],
    file_path: str,
    language: str | None,
    start_offset: int = 0,   # 0-indexed line within the file where this content starts
    chunk_type: ChunkType = "sliding_window",
    first_chunk_index: int = 0,
) -> list[ChunkResult]:
    """
    Split a block of lines into fixed-size overlapping chunks.

    Args:
        lines:            The lines to chunk (already sliced to the relevant range).
        file_path:        Used in ChunkResult.
        language:         Used in ChunkResult.
        start_offset:     0-indexed line number in the *file* where `lines[0]` lives.
                          Used to calculate correct start_line / end_line.
        chunk_type:       Written to ChunkResult.chunk_type.
        first_chunk_index: The chunk_index to assign to the first produced chunk.

    Returns:
        List of ChunkResult objects.
    """
    results: list[ChunkResult] = []
    idx = first_chunk_index
    pos = 0  # 0-indexed position within `lines`

    while pos < len(lines):
        end_pos = min(pos + WINDOW_SIZE, len(lines))
        file_start_line = start_offset + pos + 1        # 1-indexed
        file_end_line = start_offset + end_pos          # 1-indexed

        results.append(_make_chunk(
            lines=[lines[i] for i in range(pos, end_pos)],  # subset for _make_chunk
            file_path=file_path,
            language=language,
            start_line=file_start_line,
            end_line=file_end_line,
            chunk_index=idx,
            chunk_type=chunk_type,
        ))
        idx += 1

        if end_pos == len(lines):
            break
        pos = end_pos - WINDOW_OVERLAP

    return results


def _make_chunk_from_lines_subset(
    all_lines: list[str],
    file_path: str,
    language: str | None,
    start_line: int,   # 1-indexed in file
    end_line: int,     # 1-indexed in file
    chunk_index: int,
    chunk_type: ChunkType,
) -> ChunkResult:
    """Helper: build a ChunkResult using 1-indexed line numbers into all_lines."""
    content = "\n".join(all_lines[start_line - 1 : end_line])
    return ChunkResult(
        file_path=file_path,
        language=language,
        start_line=start_line,
        end_line=end_line,
        content=content,
        content_hash=_sha256(content),
        chunk_index=chunk_index,
        chunk_type=chunk_type,
    )


# ---------------------------------------------------------------------------
# AST-aware chunking
# ---------------------------------------------------------------------------

def _get_top_level_nodes(source: bytes, language_label: str):
    """
    Return top-level function/class nodes from tree-sitter.

    Returns a list of (node, chunk_type) tuples, or an empty list if
    tree-sitter parsing fails for any reason.

    Failure is always graceful — the caller falls back to sliding window.
    """
    try:
        if language_label == "python":
            import tree_sitter_python as ts_lang
            lang_name = "python"
            top_level_kinds = {"function_definition", "class_definition"}
        else:
            # javascript and typescript both use the JS grammar here
            import tree_sitter_javascript as ts_lang
            lang_name = "javascript"
            top_level_kinds = {
                "function_declaration",
                "class_declaration",
                "export_statement",   # e.g. export function / export class
            }

        from tree_sitter import Language, Parser

        ts_language = Language(ts_lang.language(), lang_name)
        parser = Parser()
        parser.set_language(ts_language)
        tree = parser.parse(source)

        nodes = []
        for child in tree.root_node.children:
            effective = child

            # Unwrap `export default` / `export const` to get the inner node
            if child.type == "export_statement":
                for sub in child.children:
                    if sub.type in {
                        "function_declaration", "class_declaration",
                        "lexical_declaration", "variable_declaration",
                    }:
                        effective = sub
                        break

            if effective.type in top_level_kinds or (
                language_label == "python" and effective.type in top_level_kinds
            ):
                kind: ChunkType = (
                    "class" if "class" in effective.type else "function"
                )
                nodes.append((effective, kind))

        return nodes

    except Exception as exc:
        logger.debug(
            "tree-sitter parsing failed for %s (%s): %s — falling back to sliding window",
            language_label, type(exc).__name__, exc,
        )
        return []


def _chunk_ast_aware(
    all_lines: list[str],
    file_path: str,
    language: str | None,
) -> list[ChunkResult]:
    """
    Extract top-level AST nodes as chunks.

    For any node that exceeds MAX_AST_CHUNK_LINES, apply sliding window
    within that node's line range. This keeps chunks bounded without losing
    the semantic boundary benefit.

    If AST extraction yields zero nodes (parse failure or empty file),
    fall back to sliding window over the whole file.
    """
    source = "\n".join(all_lines).encode("utf-8")
    nodes = _get_top_level_nodes(source, language or "")

    if not nodes:
        logger.debug("No AST nodes found in %s — using sliding window fallback", file_path)
        return _sliding_window(all_lines, file_path, language)

    results: list[ChunkResult] = []
    chunk_idx = 0

    # Track which lines have been covered by AST nodes
    covered_lines: set[int] = set()   # 1-indexed

    for node, chunk_type in nodes:
        # tree-sitter uses 0-indexed (row, col) tuples
        start_line = node.start_point[0] + 1   # convert to 1-indexed
        end_line = node.end_point[0] + 1

        covered_lines.update(range(start_line, end_line + 1))
        node_line_count = end_line - start_line + 1

        if node_line_count <= MAX_AST_CHUNK_LINES:
            results.append(_make_chunk_from_lines_subset(
                all_lines, file_path, language,
                start_line, end_line, chunk_idx, chunk_type,
            ))
            chunk_idx += 1
        else:
            # Split the oversized node with sliding window
            node_lines = all_lines[start_line - 1 : end_line]
            sub_chunks = _sliding_window(
                node_lines, file_path, language,
                start_offset=start_line - 1,
                chunk_type=chunk_type,
                first_chunk_index=chunk_idx,
            )
            results.extend(sub_chunks)
            chunk_idx += len(sub_chunks)

    # Handle any leading lines before the first AST node (e.g. module docstring,
    # imports, top-level constants). Collect contiguous uncovered regions and
    # emit them as "file_header" or "block" chunks.
    uncovered = sorted(set(range(1, len(all_lines) + 1)) - covered_lines)
    if uncovered:
        # Group into contiguous runs
        runs: list[tuple[int, int]] = []
        run_start = uncovered[0]
        prev = uncovered[0]
        for ln in uncovered[1:]:
            if ln != prev + 1:
                runs.append((run_start, prev))
                run_start = ln
            prev = ln
        runs.append((run_start, prev))

        for run_start, run_end in runs:
            run_lines = all_lines[run_start - 1 : run_end]
            # Skip runs that are entirely blank
            if not any(l.strip() for l in run_lines):
                continue
            run_type: ChunkType = "file_header" if run_start == 1 else "block"
            sub = _sliding_window(
                run_lines, file_path, language,
                start_offset=run_start - 1,
                chunk_type=run_type,
                first_chunk_index=chunk_idx,
            )
            results.extend(sub)
            chunk_idx += len(sub)

    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def chunk_file(fetched_file: FetchedFile) -> list[ChunkResult]:
    """
    Split a FetchedFile into a list of ChunkResult objects.

    Dispatches to AST-aware chunking for Python/JS/TS and sliding window
    for everything else. Always returns at least one chunk for non-empty files.

    Args:
        fetched_file: A FetchedFile produced by services/ingestion.py.

    Returns:
        List of ChunkResult objects, in file order, with sequential chunk_index.
        Returns an empty list only if the file content is empty after stripping.
    """
    content = fetched_file.content

    if not content.strip():
        logger.debug("Skipping empty file: %s", fetched_file.file_path)
        return []

    lines = content.splitlines()
    lang = fetched_file.language

    if lang in _AST_LANGUAGES:
        chunks = _chunk_ast_aware(lines, fetched_file.file_path, lang)
    else:
        chunks = _sliding_window(lines, fetched_file.file_path, lang)

    logger.debug(
        "Chunked %s (%s): %d lines → %d chunks",
        fetched_file.file_path, lang, len(lines), len(chunks),
    )
    return chunks