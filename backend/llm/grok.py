"""
Grok LLM client.

Responsible for:
  - Building the system prompt and numbered user message from retrieved chunks
  - Calling the Grok API (OpenAI-compatible /v1/chat/completions endpoint)
  - Parsing and returning the generated answer text

Prompt design (Phase 0):
  - System prompt: instructs Grok to answer only from provided code snippets;
    say so explicitly if the answer is not present in the context.
  - User message: question followed by numbered citation blocks [1], [2], ...
    The numbers match the citation index displayed to the user in the frontend.
  - Temperature: 0.2 — factual, grounded, low creative variance.
  - max_tokens: 1024 — sufficient for a detailed code explanation.

API notes:
  - Base URL: https://api.x.ai/v1 (OpenAI-compatible)
  - Auth:     Authorization: Bearer <GROK_API_KEY>
  - Model:    configurable via settings.grok_model (default "grok-3")
  - All values driven from config.py — no hardcoding in this module.
"""

from __future__ import annotations

import logging

import httpx

from config import settings
from models.schemas import ChunkCitation

logger = logging.getLogger(__name__)

GROK_BASE_URL = "https://api.x.ai/v1"
CHAT_ENDPOINT = f"{GROK_BASE_URL}/chat/completions"

# Maximum characters for a single chunk's content in the prompt.
# A 60-line chunk at ~50 chars/line ≈ 3,000 chars; this cap handles
# pathologically large chunks without blowing the context window.
_CHUNK_CONTENT_MAX_CHARS = 3_000

# System prompt — instructs Grok to stay grounded in retrieved context.
_SYSTEM_PROMPT = """\
You are an expert code assistant. You are given a user question and a set of \
relevant code snippets retrieved from a GitHub repository. \
Answer the question using ONLY the information present in the provided code snippets. \
If the answer cannot be determined from the snippets, say so clearly — do not guess or invent details. \
When referencing code, cite the relevant snippet number (e.g. [1], [2]) inline. \
Be concise, precise, and technical.\
"""


def build_user_message(question: str, citations: list[ChunkCitation]) -> str:
    """
    Construct the user message sent to Grok.

    Format:
      Question: <question>

      Relevant code snippets:

      [1] File: src/auth.py (lines 12-48)
      ```python
      <content>
      ```

      [2] File: ...

    Args:
        question:  The user's natural-language question.
        citations: Retrieved ChunkCitation objects from the retriever.

    Returns:
        Formatted string ready to send as the user message.
    """
    parts = [f"Question: {question}", "", "Relevant code snippets:"]

    for i, citation in enumerate(citations, start=1):
        content = citation.content
        if len(content) > _CHUNK_CONTENT_MAX_CHARS:
            content = content[:_CHUNK_CONTENT_MAX_CHARS] + "\n... [truncated]"

        lang = citation.language or ""
        header = (
            f"[{i}] File: {citation.file_path} "
            f"(lines {citation.start_line}-{citation.end_line})"
        )
        block = f"{header}\n```{lang}\n{content}\n```"
        parts.append(block)

    return "\n\n".join(parts)


async def generate_answer(
    question: str,
    citations: list[ChunkCitation],
) -> str:
    """
    Generate a grounded answer using Grok given a question and retrieved citations.

    Makes an async HTTP POST to the Grok chat completions endpoint.
    Returns the answer text string.

    If citations is empty, the prompt still runs — Grok will state it has
    no code context and cannot answer.

    Args:
        question:  The user's natural-language question.
        citations: Retrieved ChunkCitation objects (may be empty).

    Returns:
        Answer text as a string.

    Raises:
        httpx.HTTPStatusError: on non-2xx response from Grok API.
        httpx.TimeoutException: if the API call exceeds the timeout.
        KeyError / IndexError: if the response shape is unexpected (logged + re-raised).
    """
    user_message = build_user_message(question, citations)

    payload = {
        "model":       settings.grok_model,
        "max_tokens":  settings.grok_max_tokens,
        "temperature": settings.grok_temperature,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.grok_api_key}",
        "Content-Type":  "application/json",
    }

    logger.info(
        "Calling Grok API: model=%s, citations=%d, question='%s...'",
        settings.grok_model, len(citations), question[:60],
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(CHAT_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    try:
        answer: str = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        logger.error("Unexpected Grok response shape: %s — raw: %s", exc, data)
        raise

    logger.info(
        "Grok answer received: %d chars (finish_reason=%s)",
        len(answer),
        data.get("choices", [{}])[0].get("finish_reason", "unknown"),
    )
    return answer.strip()