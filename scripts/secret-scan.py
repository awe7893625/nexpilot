#!/usr/bin/env python3
"""Small release-tree leak scanner for the NexPilot public package."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
}

BANNED_PATH_PARTS = {
    ".m4_data",
    ".m4_runtime",
    ".workflow",
    ".tasks",
    "backups",
    "secrets",
    "private",
}

BANNED_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pem",
    ".key",
    ".p12",
    ".mobileprovision",
    ".log",
    ".bak",
    ".backup",
    ".snapshot",
    ".corrupt",
}

SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"/Users/" r"rain\b"),
    re.compile(r"\b100\.79\.187\.107\b"),
    re.compile(r"\b100\.123\.36\.104\b"),
    re.compile(r"\bND_ADMIN_SECRET\s*=\s*[^#\s]+"),
    re.compile(r"\b(?:OPENAI|ANTHROPIC|GOOGLE|GEMINI|TAILSCALE|CLOUDFLARE|CF_ACCESS)_[A-Z0-9_]*\s*=\s*[^#\s]+"),
]

PLACEHOLDER_HINTS = {
    "REPLACE_ME",
    "PLACEHOLDER",
    "your_",
    "example",
    "EXAMPLE",
    "OWNER",
}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def is_placeholder(line: str) -> bool:
    return any(hint in line for hint in PLACEHOLDER_HINTS)


def scan() -> list[str]:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if should_skip(rel):
            continue
        if path.is_dir():
            continue
        rel_text = str(rel)
        lowered_parts = {part.lower() for part in rel.parts}
        if lowered_parts & BANNED_PATH_PARTS:
            findings.append(f"banned path: {rel_text}")
        if path.suffix.lower() in BANNED_SUFFIXES:
            findings.append(f"banned suffix: {rel_text}")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if is_placeholder(line):
                continue
            for pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(f"{rel_text}:{line_no}: {pattern.pattern}")
    return findings


def main() -> int:
    findings = scan()
    if findings:
        print("NexPilot release leak scan: FAIL")
        for finding in findings:
            print(f" - {finding}")
        return 1
    print("NexPilot release leak scan: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
