from pathlib import PurePosixPath

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".go", ".java", ".kt", ".rs", ".rb",
    ".c", ".cpp", ".cc", ".h", ".hpp", ".cs",
    ".md", ".mdx", ".json", ".yaml", ".yml", ".toml",
    ".sh", ".bash", ".sql",
})

DENIED_DIRECTORIES: frozenset[str] = frozenset({
    "node_modules", ".git", "dist", "build", "out",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "venv", ".venv", "env", ".env", "coverage", ".coverage",
    ".next", ".nuxt", "target", "vendor", "Pods", ".gradle", "gradle",
})

DENIED_SUFFIXES: frozenset[str] = frozenset({
    ".lock", ".min.js", ".min.css", ".map", ".pyc",
    ".class", ".jar", ".war", ".exe", ".dll", ".so", ".dylib", ".wasm", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".pdf", ".zip", ".tar", ".gz", ".bz2",
    ".ttf", ".woff", ".woff2", ".eot",
})

def is_allowed(file_path: str) -> bool:
    path = PurePosixPath(file_path)
    for part in path.parts[:-1]:
        if part in DENIED_DIRECTORIES:
            return False
    name_lower = path.name.lower()
    for suffix in DENIED_SUFFIXES:
        if name_lower.endswith(suffix):
            return False
    return path.suffix.lower() in ALLOWED_EXTENSIONS
