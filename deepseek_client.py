"""Shared helpers for the DeepSeek chat completion scripts.

DeepSeek exposes an OpenAI-compatible API, so this module wraps the `openai`
SDK and adds .env loading, prompt sourcing, and the API-key guard.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Iterator

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-chat"
PROMPTS_DIR = Path(__file__).with_name("prompts")


def load_env_file(path: Path | None = None) -> None:
    """Minimal .env loader so the scripts work without python-dotenv.

    Real environment variables win over values found in the file.
    """
    env_path = path or Path(__file__).with_name(".env")
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def read_prompt(source: str) -> str:
    """Prompt comes from an inline string, a file path, or stdin ('-')."""
    if source == "-":
        return sys.stdin.read()
    candidate = Path(source)
    if candidate.is_file():
        return candidate.read_text(encoding="utf-8")
    return source


def read_prompt_file(path: str | Path) -> str:
    """Read a prompt from an explicit file path, failing loudly if missing."""
    candidate = Path(path)
    if not candidate.is_file():
        raise FileNotFoundError(f"Prompt file not found: {candidate}")
    return candidate.read_text(encoding="utf-8")


# Values ending in these extensions are treated as file paths, not inline text,
# so a typo'd filename errors out instead of being sent to the model verbatim.
PROMPT_FILE_SUFFIXES = (".txt", ".md", ".text", ".prompt")


def resolve_prompt(
    source: str | None = None,
    prompt_file: str | None = None,
    default_filename: str | None = None,
) -> str:
    """Work out where the prompt comes from, in priority order.

    1. ``--prompt-file`` if given (must exist).
    2. The positional argument: inline text, a file path, or '-' for stdin.
    3. ``prompts/<default_filename>`` next to this module.

    A positional argument ending in .txt/.md is always treated as a path, so a
    typo raises FileNotFoundError rather than being sent as literal prompt text.
    """
    if prompt_file:
        prompt = read_prompt_file(prompt_file)
    elif source:
        looks_like_file = source.lower().endswith(PROMPT_FILE_SUFFIXES)
        if looks_like_file and not Path(source).is_file():
            raise FileNotFoundError(
                f"Prompt file not found: {source}\n"
                f"Tip: the default prompt lives in {PROMPTS_DIR / (default_filename or '')}"
            )
        prompt = read_prompt(source)
    elif default_filename:
        prompt = read_prompt_file(PROMPTS_DIR / default_filename)
    else:
        raise ValueError("No prompt provided.")

    if not prompt.strip():
        raise ValueError("Prompt is empty.")
    return prompt


def require_api_key(api_key: str | None = None) -> str:
    key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not set. Put it in the environment or in .env."
        )
    return key


def build_client(base_url: str = DEFAULT_BASE_URL, api_key: str | None = None) -> Any:
    try:
        from openai import OpenAI
    except ImportError:  # pragma: no cover - dependency guard
        sys.exit(
            "Missing dependency: openai\n"
            "Install it with:  python -m pip install -r requirements.txt"
        )
    return OpenAI(api_key=require_api_key(api_key), base_url=base_url)


def build_messages(prompt: str, system_prompt: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]


def iter_stream_chunks(stream: Any) -> Iterator[str]:
    """Yield only the text deltas from an OpenAI-style streaming response."""
    for chunk in stream:
        if not chunk.choices:
            continue
        piece = chunk.choices[0].delta.content
        if piece:
            yield piece
