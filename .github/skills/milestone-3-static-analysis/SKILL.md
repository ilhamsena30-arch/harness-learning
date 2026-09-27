---
name: milestone-3-static-analysis
description: 'Teach and practice Milestone 3: code structures and static analysis — ASTs, static type checking, dependency graphs, and deterministic tool feedback to prune search. Use when the user asks about AST, the ast module, type checking, call graphs, dependency graphs, or deterministic verifiers.'
---

# Milestone 3 — Code Structures & Static Analysis

## When to Use
- "What is an AST?", "How do I type-check generated code?", "What is a dependency graph?"
- "What am I missing for Milestone 3?", "Can I prune candidates without running code?"

## Procedure
1. Read `AGENTS.md`; note that `results/generated_code_*.py` is written to disk but never parsed or executed.
2. Explain before changing code (learning mode — see `AGENTS.md`).
3. Guide the mini-project step by step; do not write it all for the user.
4. After the attempt, record the result (see section 7).

## Reading list
- **PICARD** — Scholak et al., 2021, <https://arxiv.org/abs/2109.05093>. Incremental parsing to reject inadmissible tokens during decoding. Read for deterministic grammar feedback.
- **SynCode** — Ugare et al., 2024, <https://arxiv.org/abs/2403.01632>. Grammar augmentation via a DFA mask; eliminates syntax errors. Read for how a grammar constrains generation.
- **Static Analysis as a Feedback Loop** — Blyth et al., 2025, <https://arxiv.org/abs/2508.14419>. Iterative Bandit/Pylint feedback improves LLM code beyond correctness. Read for tool feedback loops.

## 1. What to learn
- AST: `ast.parse` turns source into a tree; `ast.walk` visits nodes like `FunctionDef`, `Import`, `Call`.
- Static type checking: running mypy/pyright over code without executing it.
- Dependency graph: which functions call which.
- Deterministic tool feedback: a verifier that is a tool, not an LLM opinion.

## 2. Why it matters
- Milestone 2's verifier is an LLM opinion. This milestone makes verification deterministic, which is what lets search prune reliably.

## 3. How to implement it
- `ast.parse(code)` -> catch `SyntaxError` deterministically.
- Walk the tree to collect function names, imports, and calls.
- Build a `{caller: [callees]}` graph from the generated files.
- Suggested new file: `static_checks.py` (stdlib only; no new dependencies).

## 4. When to use it in an LLM harness
- Before executing generated code: parse it first and fail fast on syntax.
- When ranking candidates: prefer ones that type-check or have clean graphs.
- When a deterministic check exists, use it instead of asking the model to judge.

## 5. Current gap vs this repo
- `harness.py` writes code to disk and never looks at it again. There is no `ast` import anywhere, and nothing type-checks. Milestone 3 is entirely unbuilt.

## 6. Mini-project + pass criteria
- Build `static_checks.py` that parses every file in `results/`, reports function names + imports + a caller->callees graph, and flags a deliberately broken file.
- PASS when: (a) a syntactically broken file is reported with its error; (b) the graph correctly lists which generated functions call which helpers.

## 7. Record progress
- Append a dated entry under "## Milestone 3 — Static analysis" in `LEARNING_PROGRESS.md` (repo root), using the entry template in that file.
- Update the Milestone 3 row in that file's "Status at a glance" table.
