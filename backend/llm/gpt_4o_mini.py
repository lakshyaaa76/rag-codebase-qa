"""
OpenAI LLM client (gpt-4o-mini).

Responsible for:
  - Building the system prompt and numbered user message from retrieved chunks
  - Calling the OpenAI API (/v1/chat/completions endpoint)
  - Parsing and returning the generated answer text

Prompt design (Phase 0):
  - System prompt: instructs OpenAI to answer only from provided code snippets;
    say so explicitly if the answer is not present in the context.
  - User message: question followed by numbered citation blocks [1], [2], ...
    The numbers match the citation index displayed to the user in the frontend.
  - Temperature: 0.2 — factual, grounded, low creative variance.
  - max_tokens: 1024 — sufficient for a detailed code explanation.

API notes:
  - Base URL: https://api.openai.com/v1
  - Auth:     Authorization: Bearer <OPENAI_API_KEY>
  - Model:    configurable via settings.openai_model (default "gpt-4o-mini")
  - All values driven from config.py — no hardcoding in this module.
"""

from __future__ import annotations

import logging

import httpx

from config import settings
from models.schemas import ChunkCitation

logger = logging.getLogger(__name__)

OPENAI_BASE_URL = "https://api.openai.com/v1"
CHAT_ENDPOINT = f"{OPENAI_BASE_URL}/chat/completions"

# Maximum characters for a single chunk's content in the prompt.
# A 60-line chunk at ~50 chars/line ≈ 3,000 chars; this cap handles
# pathologically large chunks without blowing the context window.
_CHUNK_CONTENT_MAX_CHARS = 3_000

# System prompt — instructs OpenAI to stay grounded in retrieved context.
_SYSTEM_PROMPT = """\
You are an expert code assistant. You are given a user question and a set of \
relevant code snippets retrieved from a GitHub repository. \
You must ONLY answer questions that are related to the codebase or the provided snippets. \
If the user asks personal, conversational, or out-of-domain questions, \
do not answer them. Instead, politely reply with: "Please ask questions related to the project." \
Otherwise, answer the question using ONLY the information present in the provided code snippets. \
If the answer cannot be determined from the snippets, say so clearly — do not guess or invent details. \
When referencing code, cite the relevant snippet number (e.g. [1], [2]) inline. \
Be concise, precise, and technical.\
"""


def build_user_message(question: str, citations: list[ChunkCitation]) -> str:
    """
    Construct the user message sent to OpenAI.

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
    Generate a grounded answer using OpenAI given a question and retrieved citations.

    Makes an async HTTP POST to the OpenAI chat completions endpoint.
    Returns the answer text string.

    If citations is empty, the prompt still runs — OpenAI will state it has
    no code context and cannot answer.

    Args:
        question:  The user's natural-language question.
        citations: Retrieved ChunkCitation objects (may be empty).

    Returns:
        Answer text as a string.

    Raises:
        httpx.HTTPStatusError: on non-2xx response from OpenAI API.
        httpx.TimeoutException: if the API call exceeds the timeout.
        KeyError / IndexError: if the response shape is unexpected (logged + re-raised).
    """
    user_message = build_user_message(question, citations)

    payload = {
        "model":       settings.openai_model,
        "max_tokens":  settings.openai_max_tokens,
        "temperature": settings.openai_temperature,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type":  "application/json",
    }

    logger.info(
        "Calling OpenAI API: model=%s, citations=%d, question='%s...'",
        settings.openai_model, len(citations), question[:60],
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(CHAT_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    try:
        answer: str = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        logger.error("Unexpected OpenAI response shape: %s — raw: %s", exc, data)
        raise

    logger.info(
        "OpenAI answer received: %d chars (finish_reason=%s)",
        len(answer),
        data.get("choices", [{}])[0].get("finish_reason", "unknown"),
    )
    return answer.strip()
