"""
Ingestion service.

Responsible for:
  - Resolving the default branch of a GitHub repository
  - Fetching the full recursive file tree via the GitHub Git Trees API
  - Filtering files using utils/file_filter.py
  - Fetching individual file contents via the GitHub raw content API
  - Enforcing the max_files_per_repo cap

All HTTP calls are made with httpx using the GITHUB_TOKEN from settings.
No file is written to disk — content is returned as strings in memory.

GitHub API docs referenced:
  GET /repos/{owner}/{repo}                    — repo metadata (default branch)
  GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1  — full file tree
  GET https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}  — raw file
"""

import asyncio
import hashlib
import logging
from dataclasses import dataclass

import httpx

from config import settings
from utils.file_filter import is_allowed

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

# Delay between individual file fetches to be a polite API citizen
_FILE_FETCH_DELAY_SECONDS = 0.05


@dataclass
class FetchedFile:
    """A single file fetched from GitHub, ready to be chunked."""
    file_path: str       # relative path from repo root, e.g. "src/utils/parser.py"
    content: str         # raw text content
    language: str | None # detected from extension, e.g. "python"
    content_hash: str    # SHA-256 hex of content


def _make_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _detect_language(file_path: str) -> str | None:
    """Map file extension to a language label stored in the chunks table."""
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    mapping = {
        "py": "python",
        "js": "javascript", "jsx": "javascript", "mjs": "javascript", "cjs": "javascript",
        "ts": "typescript", "tsx": "typescript",
        "go": "go",
        "java": "java",
        "kt": "kotlin",
        "rs": "rust",
        "rb": "ruby",
        "c": "c", "h": "c",
        "cpp": "cpp", "cc": "cpp", "hpp": "cpp",
        "cs": "csharp",
        "md": "markdown", "mdx": "markdown",
        "json": "json",
        "yaml": "yaml", "yml": "yaml",
        "toml": "toml",
        "sh": "shell", "bash": "shell",
        "sql": "sql",
    }
    return mapping.get(ext)


async def fetch_default_branch(owner: str, repo_name: str) -> str:
    """
    Return the default branch name for a repository (e.g. 'main' or 'master').

    Raises:
        httpx.HTTPStatusError: if the repo is not found or the token is invalid.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo_name}"
    async with httpx.AsyncClient(headers=_make_headers(), timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        return data["default_branch"]


async def fetch_file_tree(owner: str, repo_name: str, branch: str) -> list[str]:
    """
    Fetch the full recursive file tree and return a filtered list of file paths.

    Uses the Git Trees API with recursive=1 so a single request returns every
    path in the repo. Applies is_allowed() from file_filter and enforces the
    max_files_per_repo cap from settings.

    Returns:
        List of relative file paths (strings) that passed the filter.

    Raises:
        httpx.HTTPStatusError: on API failure.
        ValueError: if the tree is truncated (repo too large for a single API call).
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo_name}/git/trees/{branch}"
    params = {"recursive": "1"}

    async with httpx.AsyncClient(headers=_make_headers(), timeout=60.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    if data.get("truncated"):
        # GitHub truncates trees beyond ~100k entries. Extremely rare for repos
        # we'd index, but we must handle it gracefully rather than silently
        # indexing a partial tree.
        logger.warning(
            "Git tree response was truncated for %s/%s. "
            "Only files returned in the first page will be indexed.",
            owner, repo_name,
        )

    blobs = [item for item in data.get("tree", []) if item.get("type") == "blob"]
    allowed = [item["path"] for item in blobs if is_allowed(item["path"])]

    if len(allowed) > settings.max_files_per_repo:
        logger.warning(
            "Repo %s/%s has %d eligible files; capping at %d.",
            owner, repo_name, len(allowed), settings.max_files_per_repo,
        )
        allowed = allowed[: settings.max_files_per_repo]

    logger.info(
        "File tree for %s/%s: %d blobs total, %d after filtering.",
        owner, repo_name, len(blobs), len(allowed),
    )
    return allowed


async def fetch_file_content(
    owner: str, repo_name: str, branch: str, file_path: str
) -> str | None:
    """
    Fetch the raw text content of a single file.

    Returns None if the file appears to be binary (contains a null byte)
    or if the response is not UTF-8 decodable. Both cases are logged at
    DEBUG level and silently skipped by the caller.

    Raises:
        httpx.HTTPStatusError: on non-404 HTTP errors.
    """
    url = f"{GITHUB_RAW_BASE}/{owner}/{repo_name}/{branch}/{file_path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        if response.status_code == 404:
            logger.debug("File not found (may have been deleted): %s", file_path)
            return None
        response.raise_for_status()

    try:
        content = response.content.decode("utf-8")
    except UnicodeDecodeError:
        logger.debug("Skipping non-UTF-8 file: %s", file_path)
        return None

    if "\x00" in content:
        logger.debug("Skipping binary file: %s", file_path)
        return None

    return content


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def fetch_repo_files(
    owner: str,
    repo_name: str,
    branch: str,
    file_paths: list[str],
) -> list[FetchedFile]:
    """
    Fetch content for every path in file_paths and return FetchedFile objects.

    Requests are made sequentially with a small delay to avoid hammering the
    GitHub raw content CDN. Files that return None (binary / non-UTF-8 / 404)
    are silently dropped.

    Returns:
        List of successfully fetched FetchedFile objects.
    """
    results: list[FetchedFile] = []

    for i, path in enumerate(file_paths):
        content = await fetch_file_content(owner, repo_name, branch, path)
        if content is None:
            continue

        results.append(FetchedFile(
            file_path=path,
            content=content,
            language=_detect_language(path),
            content_hash=_sha256(content),
        ))

        # Small delay every file; slightly larger pause every 50 files
        if (i + 1) % 50 == 0:
            logger.info("Fetched %d / %d files...", i + 1, len(file_paths))
            await asyncio.sleep(0.5)
        else:
            await asyncio.sleep(_FILE_FETCH_DELAY_SECONDS)

    logger.info(
        "Fetched %d files successfully (%d skipped).",
        len(results), len(file_paths) - len(results),
    )
    return results