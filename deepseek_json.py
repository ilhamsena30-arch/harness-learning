"""DeepSeek chat completion that returns a JSON object.

Uses DeepSeek's OpenAI-compatible API with ``response_format={"type": "json_object"}``
so the model is forced to emit valid, parseable JSON instead of prose.

Usage:
    python deepseek_json.py "Give me 3 SDET interview questions as json"
    python deepseek_json.py --file prompt.txt --pretty
    echo "summarize this as json" | python deepseek_json.py -

Notes:
    * DeepSeek requires the word "json" to appear somewhere in the messages when
      ``response_format`` is ``json_object``, otherwise the API returns 400.
    * Set DEEPSEEK_API_KEY in your environment or in a .env file next to this script.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from deepseek_client import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    build_client,
    build_messages,
    load_env_file,
    require_api_key,
    resolve_prompt,
)

SYSTEM_PROMPT = (
    "You are a precise assistant. Always answer with a single valid json object. "
    "Do not wrap the output in markdown code fences and do not add commentary "
    "outside of the json object."
)

DEFAULT_PROMPT_FILENAME = "json_prompt.txt"


def chat_json(
    prompt: str,
    *,
    system_prompt: str = SYSTEM_PROMPT,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_tokens: int = 2048,
    base_url: str = DEFAULT_BASE_URL,
    api_key: str | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Return the model's answer already parsed into a Python dict."""
    client = build_client(base_url, api_key or require_api_key())
    response = client.chat.completions.create(
        model=model,
        messages=build_messages(prompt, system_prompt),
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )

    content = response.choices[0].message.content or ""
    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:  # keep the raw text so the user can debug
        raise ValueError(
            f"Model did not return valid JSON: {exc}\n--- raw response ---\n{content}"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    load_env_file()

    parser = argparse.ArgumentParser(
        description="DeepSeek chat completion returning a JSON object."
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
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument(
        "--base-url",
        default=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print single-line JSON instead of indented JSON.",
    )
    parser.add_argument(
        "--out",
        help="Optional file path to also write the JSON payload to.",
    )
    args = parser.parse_args(argv)

    try:
        prompt = resolve_prompt(args.prompt, args.prompt_file, DEFAULT_PROMPT_FILENAME)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if "json" not in prompt.lower() and "json" not in args.system.lower():
        # Fail fast with a helpful message instead of a confusing 400 from the API.
        prompt = f"{prompt}\n\nRespond in json."

    try:
        data = chat_json(
            prompt,
            system_prompt=args.system,
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            base_url=args.base_url,
            timeout=args.timeout,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(data, ensure_ascii=False, indent=None if args.compact else 2)
    print(text)

    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"[written to {args.out}]", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
