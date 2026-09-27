"""DeepSeek chat completion that returns plain text.

No ``response_format`` is sent, so the model answers naturally (prose, markdown,
code, ...). Supports one-shot and streaming output.

Usage:
    python deepseek_text.py
    python deepseek_text.py "Explain the Page Object Model in 3 sentences"
    python deepseek_text.py --prompt-file step_1.txt
    echo "rewrite this CV bullet" | python deepseek_text.py -
    python deepseek_text.py --stream "Write a pytest fixture example"

Set DEEPSEEK_API_KEY in your environment or in a .env file next to this script.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterator

from deepseek_client import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    build_client,
    build_messages,
    iter_stream_chunks,
    load_env_file,
    require_api_key,
    resolve_prompt,
)

SYSTEM_PROMPT = "You are a helpful, concise assistant."

DEFAULT_PROMPT_FILENAME = "step_1.txt"


def chat_text(
    prompt: str,
    *,
    system_prompt: str = SYSTEM_PROMPT,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    base_url: str = DEFAULT_BASE_URL,
    api_key: str | None = None,
    timeout: float = 60.0,
) -> str:
    """Return the model's answer as a plain string."""
    client = build_client(base_url, api_key or require_api_key())
    response = client.chat.completions.create(
        model=model,
        messages=build_messages(prompt, system_prompt),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return response.choices[0].message.content or ""


def chat_text_stream(
    prompt: str,
    *,
    system_prompt: str = SYSTEM_PROMPT,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    base_url: str = DEFAULT_BASE_URL,
    api_key: str | None = None,
    timeout: float = 60.0,
) -> Iterator[str]:
    """Yield the answer in chunks as the model produces them."""
    client = build_client(base_url, api_key or require_api_key())
    stream = client.chat.completions.create(
        model=model,
        messages=build_messages(prompt, system_prompt),
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        stream=True,
    )
    yield from iter_stream_chunks(stream)


def main(argv: list[str] | None = None) -> int:
    load_env_file()

    parser = argparse.ArgumentParser(
        description="DeepSeek chat completion returning plain text."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Prompt text, a path to a prompt file, or '-' to read stdin. "
        f"Defaults to prompts/{DEFAULT_PROMPT_FILENAME}.",
    )
    parser.add_argument(
        "--prompt-file",
        help="Path to a file holding the prompt (overrides the positional argument).",
    )
    parser.add_argument("--system", default=SYSTEM_PROMPT, help="System prompt.")
    parser.add_argument(
        "--model",
        default=os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL),
        help=f"Model name (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Print tokens as they arrive instead of waiting for the full reply.",
    )
    parser.add_argument(
        "--out",
        help="Optional file path to also write the answer to.",
    )
    args = parser.parse_args(argv)

    try:
        prompt = resolve_prompt(args.prompt, args.prompt_file, DEFAULT_PROMPT_FILENAME)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    kwargs = dict(
        system_prompt=args.system,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        base_url=args.base_url,
        timeout=args.timeout,
    )

    try:
        if args.stream:
            chunks: list[str] = []
            for piece in chat_text_stream(prompt, **kwargs):
                print(piece, end="", flush=True)
                chunks.append(piece)
            print()
            answer = "".join(chunks)
        else:
            answer = chat_text(prompt, **kwargs)
            print(answer)
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.out:
        Path(args.out).write_text(answer + "\n", encoding="utf-8")
        print(f"[written to {args.out}]", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
