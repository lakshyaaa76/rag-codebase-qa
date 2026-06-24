from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedGitHubURL:
    owner: str
    repo_name: str
    branch: Optional[str]

class InvalidGitHubURLError(ValueError):
    pass

def parse_github_url(url: str) -> ParsedGitHubURL:
    url = url.strip().rstrip("/")
    if not url.startswith("https://github.com/"):
        raise InvalidGitHubURLError(f"Not a GitHub URL: {url!r}")
    remainder = url[len("https://github.com/"):]
    parts = remainder.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise InvalidGitHubURLError(f"Cannot parse owner/repo from URL: {url!r}")
    owner = parts[0]
    repo_name = parts[1]
    branch: Optional[str] = None
    if len(parts) >= 4 and parts[2] == "tree":
        branch = "/".join(parts[3:])
    return ParsedGitHubURL(owner=owner, repo_name=repo_name, branch=branch)
