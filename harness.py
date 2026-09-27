"""Score-and-generate harness across sequentially chained DeepSeek calls.

Pipeline (each step blocks until the previous one returns — no threads, no
asyncio, no parallel requests):

    step 1  prompts/step_1.txt      -> plain text, the candidate methods
    step 2  prompts/step_2.txt      -> that text as json
    step 3  prompts/step_3.txt      -> per-key scores from 0.0 to 1.0
    step 4  prompts/step_4.txt      -> Python code for the top k methods

``evaluator.txt`` supplies the evaluation criteria (categories) used by step 3.
Python does the averaging and the ranking, so ordering is deterministic.

Prompts are not hardcoded here: each step reads its own editable ``.txt`` file
and gets the previous step's output injected into the ``{{PAYLOAD}}`` slot.

Usage:
    python harness.py
    python harness.py --top-k 2
    python harness.py --verbose
    python harness.py --criteria "Speed, Security, OWASP"
    python harness.py --step1-prompt "List 3 ways to hash a password"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from deepseek_client import (
    PROMPTS_DIR,
    load_env_file,
    read_prompt_file,
    resolve_prompt,
)
from deepseek_json import DEFAULT_PROMPT_FILENAME as JSON_PROMPT_FILENAME
from deepseek_json import chat_json
from deepseek_text import DEFAULT_PROMPT_FILENAME as STEP1_PROMPT_FILENAME
from deepseek_text import chat_text

EVALUATOR_FILENAME = "evaluator.txt"
RESULTS_DIR = Path(__file__).with_name("results")

PAYLOAD_SLOT = "{{PAYLOAD}}"
CRITERIA_SLOT = "{{CRITERIA}}"

# If step 3 returns an empty category map, fall back to one flat overall score
# so a method can still be ranked instead of crashing the run.
FALLBACK_CATEGORY = "overall"


# --------------------------------------------------------------------------- #
# Step 1 + 2: gather the methods as text, then turn that text into JSON
# --------------------------------------------------------------------------- #


def run_step_1(step1_prompt: str) -> str:
    """Step 1: ask for the candidate methods as plain text."""
    # Plain text, not JSON: this step is the model's free-form brainstorm.
    return chat_text(step1_prompt)


def render_step_2(step_1_text: str) -> str:
    """Inject step 1's text into the step 2 template."""
    # Read the template on each call so edits to the .txt file apply immediately.
    template = read_prompt_file(PROMPTS_DIR / "step_2.txt")
    return _fill_template(template, PAYLOAD_SLOT, step_1_text)


def run_step_2(step_1_text: str) -> dict[str, Any]:
    """Step 2: convert step 1's text into a json ``{"methods": [...]}`` object."""
    return chat_json(render_step_2(step_1_text))


def extract_methods(step_2_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull the method list out of step 2's response.

    Accepts ``{"methods": [...]}`` plus a few common shapes an LLM may return,
    so a slightly different envelope does not abort the pipeline.
    """
    candidates: Any = None
    # Be forgiving about the envelope: accept the documented "methods" key, a few
    # common aliases, and finally any non-empty list value in the object.
    for key in ("methods", "items", "results", "data", "method"):
        value = step_2_json.get(key)
        if isinstance(value, list):
            candidates = value
            break
    if candidates is None:
        candidates = next(
            (v for v in step_2_json.values() if isinstance(v, list) and v),
            None,
        )
    if not isinstance(candidates, list) or not candidates:
        raise ValueError(
            "Step 2 did not return any methods. Raw json was:\n"
            f"{json.dumps(step_2_json, ensure_ascii=False, indent=2)}"
        )

    methods: list[dict[str, Any]] = []
    for index, entry in enumerate(candidates, start=1):
        # Wrap non-dict entries so every method is a dict downstream.
        if isinstance(entry, dict):
            method = dict(entry)
            method.setdefault("name", f"method_{index}")
        else:
            method = {"name": f"method_{index}", "description": str(entry)}
        methods.append(method)

    _ensure_unique_names(methods)
    return methods


def _ensure_unique_names(methods: list[dict[str, Any]]) -> None:
    """Keep names unique and non-blank so scores can be matched back to methods."""
    # Duplicate or blank names would make step 3's scores ambiguous to re-match.
    seen: dict[str, int] = {}
    for index, method in enumerate(methods, start=1):
        raw = str(method.get("name") or "").strip() or f"method_{index}"
        count = seen.get(raw, 0) + 1
        seen[raw] = count
        method["name"] = raw if count == 1 else f"{raw} ({count})"


# --------------------------------------------------------------------------- #
# Step 3: score every method in every category
# --------------------------------------------------------------------------- #


def load_criteria(path: Path | None = None) -> str:
    """Read the evaluation criteria from ``evaluator.txt``."""
    # Resolve relative to this file so the CLI works from any working directory.
    criteria_path = path or (Path(__file__).with_name(EVALUATOR_FILENAME))
    if not criteria_path.is_file():
        raise FileNotFoundError(f"Evaluation criteria not found: {criteria_path}")
    criteria = criteria_path.read_text(encoding="utf-8").strip()
    if not criteria:
        raise ValueError(f"Evaluation criteria file is empty: {criteria_path}")
    return criteria


def render_step_3(methods: list[dict[str, Any]], criteria: str) -> str:
    """Inject the criteria and the methods into the step 3 template."""
    # Serialize the methods as indented JSON so the model sees explicit structure.
    template = read_prompt_file(PROMPTS_DIR / "step_3.txt")
    payload = json.dumps(methods, ensure_ascii=False, indent=2)
    prompt = _fill_template(template, CRITERIA_SLOT, criteria)
    return _fill_template(prompt, PAYLOAD_SLOT, payload)


def run_step_3(methods: list[dict[str, Any]], criteria: str) -> dict[str, Any]:
    """Step 3: ask for a 0.0-1.0 score per category for every method."""
    return chat_json(render_step_3(methods, criteria))


def to_score(value: Any) -> float | None:
    """Coerce a model-provided score into a clamped float, or None if unusable."""
    if isinstance(value, bool):  # bool is an int subclass; reject it outright
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if not match:
            return None
        number = float(match.group())
    else:
        return None
    return min(max(number, 0.0), 1.0)


def normalize_categories(raw_categories: Any) -> dict[str, float]:
    """Turn a ``{category: score}`` mapping into clean, clamped floats."""
    # Anything that is not a mapping (or has no usable scores) is dropped.
    if not isinstance(raw_categories, dict):
        return {}
    clean: dict[str, float] = {}
    for key, value in raw_categories.items():
        score = to_score(value)
        # Skip unusable scores rather than counting them as zero.
        if score is not None:
            clean[str(key).strip() or FALLBACK_CATEGORY] = score
    return clean


def score_methods(
    methods: list[dict[str, Any]],
    evaluations: Any,
) -> list[dict[str, Any]]:
    """Merge step 3's scores onto the methods and add a Python-computed average.

    Matching is done in two passes (exact name, then position within the
    response) because ``chat_json`` parses the reply into a ``dict`` and a json
    object gives no key ordering guarantee.
    """
    eval_list: list[dict[str, Any]] = []
    # Step 3 may return the list directly or nest it under a named key.
    if isinstance(evaluations, dict):
        evaluations = evaluations.get("evaluations") or evaluations.get("methods") or []
    if isinstance(evaluations, list):
        eval_list = [e for e in evaluations if isinstance(e, dict)]

    # Pass 1 lookup key: the method name, case-insensitive so casing never blocks
    # a match between step 2's names and step 3's echoed names.
    by_name: dict[str, dict[str, Any]] = {}
    for entry in eval_list:
        name = str(entry.get("name") or "").strip()
        if name:
            by_name.setdefault(name.casefold(), entry)

    scored: list[dict[str, Any]] = []
    for index, method in enumerate(methods):
        # Pass 2 lookup: if the name did not match, fall back to position.
        entry = by_name.get(method["name"].casefold())
        if entry is None and index < len(eval_list):
            entry = eval_list[index]
        entry = entry or {}

        categories = normalize_categories(
            entry.get("categories") or entry.get("scores")
        )
        # If the model gave one flat score instead of categories, still rank it.
        if not categories:
            flat = to_score(entry.get("score") or entry.get("average_score"))
            if flat is not None:
                categories = {FALLBACK_CATEGORY: flat}

        average = sum(categories.values()) / len(categories) if categories else 0.0

        record = dict(method)
        record["categories"] = categories
        record["average_score"] = round(average, 4)
        record["notes"] = str(entry.get("notes") or "").strip()
        scored.append(record)

    return scored


# --------------------------------------------------------------------------- #
# Step 4: rank, then generate code for the top k methods
# --------------------------------------------------------------------------- #


def rank_methods(scored: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    """Sort by average score (highest first) and keep the top k.

    Python does the ranking, so equal scores fall back to the original order
    from step 2 rather than to the model's response ordering.
    """
    if top_k < 1:
        raise ValueError("--top-k must be at least 1.")
    # Sort by score descending; pair[0] (the original index) is the tie-break so
    # equal scores keep step 2's order instead of the model's response order.
    ordered = sorted(
        enumerate(scored),
        key=lambda pair: (-pair[1]["average_score"], pair[0]),
    )
    return [method for _, method in ordered[:top_k]]


def render_step_4(method: dict[str, Any]) -> str:
    """Inject a single method into the step 4 template."""
    template = read_prompt_file(PROMPTS_DIR / "step_4.txt")
    payload = json.dumps(method, ensure_ascii=False, indent=2)
    return _fill_template(template, PAYLOAD_SLOT, payload)


def run_step_4(method: dict[str, Any]) -> str:
    """Step 4: ask for Python code implementing one method."""
    return chat_text(render_step_4(method))


def strip_code_fences(text: str) -> str:
    """Drop a wrapping markdown fence if the model added one anyway."""
    # The prompt asks for bare code, but models often wrap it in ```python anyway.
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def generate_code_files(
    ranked: list[dict[str, Any]],
    *,
    verbose: bool = False,
) -> list[Path]:
    """Write ``results/generated_code_<rank>.py`` for each ranked method.

    One file per method, named by rank, so nothing gets overwritten and the
    ranking stays visible in the file names.
    """
    # Create results/ on demand so a fresh clone works without manual setup.
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    # One request per method, sequentially (never in parallel).
    for rank, method in enumerate(ranked, start=1):
        if verbose:
            print(
                f"[4] code request for rank {rank}: {method['name']}",
                file=sys.stderr,
            )
        code = strip_code_fences(run_step_4(method))
        target = RESULTS_DIR / f"generated_code_{rank}.py"
        target.write_text(code + "\n", encoding="utf-8")
        written.append(target)
    return written


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def run_harness(
    step1_prompt: str,
    criteria: str,
    *,
    top_k: int = 1,
    verbose: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Path]]:
    """Run the whole sequential pipeline.

    Returns ``(all_scored_methods, top_k_methods, written_code_files)``.
    """
    if verbose:
        print("[1] Text request (step_1)...", file=sys.stderr)
    step_1_text = run_step_1(step1_prompt)

    # Each step below starts only after the previous call has fully returned.
    if verbose:
        print("[2] JSON request: structure step 1 output (step_2)...", file=sys.stderr)
    methods = extract_methods(run_step_2(step_1_text))

    if verbose:
        print(f"[3] JSON request: score {len(methods)} methods (step_3)...", file=sys.stderr)
    # Python averages the returned key scores; the model never ranks for us.
    scored = score_methods(methods, run_step_3(methods, criteria)["evaluations"])

    ranked = rank_methods(scored, top_k)

    if verbose:
        print(f"[4] Text requests: generate code for top {len(ranked)}...", file=sys.stderr)
    written = generate_code_files(ranked, verbose=verbose)

    return scored, ranked, written


def _fill_template(template: str, slot: str, value: str) -> str:
    """Replace a placeholder, complaining loudly if the placeholder is absent."""
    if slot not in template:
        raise ValueError(f"Prompt template is missing the {slot} placeholder.")
    return template.replace(slot, value)


def format_score_table(scored: list[dict[str, Any]]) -> str:
    """Render the per-method scores as an aligned text table."""
    if not scored:
        return "(no methods scored)"

    # Collect the union of category names in first-seen order so every method's
    # scores line up in the same columns.
    category_names: list[str] = []
    for method in scored:
        for name in method["categories"]:
            if name not in category_names:
                category_names.append(name)
    if not category_names:
        category_names = [FALLBACK_CATEGORY]

    header = ["#", "method"] + category_names + ["average"]
    rows: list[list[str]] = []
    for index, method in enumerate(scored, start=1):
        cells = [str(index), method["name"]]
        cells += [
            f"{method['categories'][name]:.2f}"
            if name in method["categories"]
            else "-"
            for name in category_names
        ]
        cells.append(f"{method['average_score']:.2f}")
        rows.append(cells)

    widths = [
        max(len(row[column]) for row in [header] + rows)
        for column in range(len(header))
    ]

    def render(cells: list[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip()

    lines = [render(header), render(["-" * width for width in widths])]
    lines += [render(row) for row in rows]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Parse CLI args, resolve the prompt and criteria, then run the pipeline."""
    # Read DEEPSEEK_API_KEY from .env if it is not already in the environment.
    load_env_file()

    parser = argparse.ArgumentParser(
        description="Score step 1's methods per key, average them, then have "
        "DeepSeek generate code for the top k."
    )
    parser.add_argument(
        "--step1-prompt",
        help="Step 1 prompt: inline text, a path to a prompt file, or '-' for stdin. "
        f"Defaults to prompts/{STEP1_PROMPT_FILENAME}.",
    )
    parser.add_argument(
        "--criteria",
        help=f"Evaluation criteria text. Defaults to {EVALUATOR_FILENAME}.",
    )
    parser.add_argument(
        "--criteria-file",
        help=f"Path to the criteria file (default: {EVALUATOR_FILENAME}).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=1,
        help="How many top-scoring methods get code generated (default: 1).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log each sequential step to stderr before it runs.",
    )
    parser.add_argument("--json-out", help="Optional file for the scored json payload.")
    args = parser.parse_args(argv)

    try:
        step1_prompt = resolve_prompt(args.step1_prompt, None, STEP1_PROMPT_FILENAME)
        # Criteria precedence: --criteria-file > --criteria > evaluator.txt.
        if args.criteria and args.criteria_file:
            raise ValueError("Use either --criteria or --criteria-file, not both.")
        if args.criteria_file:
            criteria = load_criteria(Path(args.criteria_file))
        elif args.criteria:
            criteria = args.criteria.strip()
        else:
            criteria = load_criteria()
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        scored, ranked, written = run_harness(
            step1_prompt,
            criteria,
            top_k=args.top_k,
            verbose=args.verbose,
        )
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"=== Scores (criteria: {criteria}) ===")
    print(format_score_table(scored))

    print(f"\n=== Top {len(ranked)} by average score ===")
    for rank, method in enumerate(ranked, start=1):
        print(f"{rank}. {method['name']}  (avg {method['average_score']:.2f})")
        if method["notes"]:
            print(f"   {method['notes']}")

    print("\n=== Generated code ===")
    for path in written:
        print(f"- {path.relative_to(Path(__file__).parent)}")

    if args.json_out:
        payload = {"criteria": criteria, "methods": scored}
        Path(args.json_out).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"\n[written to {args.json_out}]", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
