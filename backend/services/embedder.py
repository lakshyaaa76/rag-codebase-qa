"""
Embedding service.

Wraps sentence-transformers (all-MiniLM-L6-v2) to produce 384-dimensional
float32 vectors from text.

Design decisions (Phase 0 + Phase 4):
  - The model is loaded ONCE at FastAPI startup via the lifespan event in
    main.py and stored on app.state.embedding_model.
  - All callers receive the same model instance via arguments — no global
    state inside this module.
  - embed_chunks() accepts list[ChunkResult] and returns list[list[float]],
    parallel to the input, ready for Supabase JSON insertion.
  - embed_query() embeds a single question string for retrieval.
  - Batch size 64 is a safe default for CPU inference.

Model notes:
  - all-MiniLM-L6-v2 produces normalised (unit-length) vectors.
  - Cosine similarity == dot product for unit vectors, matching pgvector's
    <=> operator when normalize_embeddings=True.
  - Output shape: (N, 384), dtype float32.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

from services.chunker import ChunkResult

logger = logging.getLogger(__name__)

MODEL_NAME = "jinaai/jina-embeddings-v2-base-code"
BATCH_SIZE = 8


# ---------------------------------------------------------------------------
# Model lifecycle
# ---------------------------------------------------------------------------

def load_model() -> "SentenceTransformer":
    """
    Load and return the embedding model.

    Called once from main.py lifespan on startup.
    The returned instance is stored on app.state.embedding_model.

    Raises:
        ImportError: if sentence-transformers is not installed.
        OSError: if the model cannot be downloaded or found in cache.
    """
    from sentence_transformers import SentenceTransformer  # noqa: PLC0415

    logger.info("Loading embedding model: %s", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME, trust_remote_code=True)
    logger.info("Embedding model loaded successfully.")
    return model


# ---------------------------------------------------------------------------
# Encoding
# ---------------------------------------------------------------------------

def _encode(model: "SentenceTransformer", texts: list[str]) -> np.ndarray:
    """
    Encode texts into a float32 numpy array of shape (N, 384).

    normalize_embeddings=True produces unit-length vectors so that cosine
    similarity equals the dot product — consistent with the pgvector index.
    """
    return model.encode(
        texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )


def embed_chunks(
    model: "SentenceTransformer",
    chunks: list[ChunkResult],
) -> list[list[float]]:
    """
    Embed a list of ChunkResult objects using chunk.content as the text.

    Args:
        model:  SentenceTransformer instance from app.state.embedding_model.
        chunks: Output of chunk_file() from services/chunker.py.

    Returns:
        list of 384-dimensional float vectors, one per chunk, same order.
        Empty list if chunks is empty.
    """
    if not chunks:
        return []

    texts = [c.content for c in chunks]
    vectors: np.ndarray = _encode(model, texts)

    logger.debug("Embedded %d chunks → shape %s", len(chunks), vectors.shape)
    return vectors.tolist()


def embed_query(model: "SentenceTransformer", question: str) -> list[float]:
    """
    Embed a single natural-language question for vector similarity search.

    Args:
        model:    SentenceTransformer instance from app.state.embedding_model.
        question: The user's question string.

    Returns:
        384-dimensional float vector as list[float].
    """
    vectors: np.ndarray = _encode(model, [question.strip()])
    return vectors[0].tolist()