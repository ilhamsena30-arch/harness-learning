---
name: milestone-1-search-foundations
description: 'Teach and practice Milestone 1: test-time compute and search — greedy decoding vs beam search vs MCTS, search-tree expansion, and token budgets. Use when the user asks about beam search, MCTS, greedy decoding, search trees, node expansion, token budgets, or wants to write the first real search code in this repo.'
---

# Milestone 1 — Foundations of Test-Time Compute & Search

## When to Use
- "What is beam search / MCTS / greedy decoding?", "How do search trees spend a token budget?"
- "What am I missing for Milestone 1?", "Let us build search."
- The user keeps saying "top-k" and is ready to learn why that is not beam search.

## Procedure
1. Read `AGENTS.md` at the repo root, then open `harness.py` and locate
   `run_harness`, `rank_methods`, and `generate_code_files`. These are the only
   search-like code in the repo today.
2. Explain before changing code (learning mode — see `AGENTS.md`).
3. Guide the mini-project step by step; do not write it all for the user.
4. After the attempt, record the result (see section 7).

## Reading list
- **Tree of Thoughts (ToT)** — Yao et al., 2023, <https://arxiv.org/abs/2305.10601>. **Primary paper for this milestone.** Search over "thoughts" with self-evaluation, lookahead, and backtracking. Read for the search-tree concept: node = thought, expansion = generating next thoughts.
- **Preview (skim only):** BG-MCTS (Miyamoto et al., 2026, <https://arxiv.org/abs/2602.09574>) is the Milestone 4 target paper. Do not read it in full yet — Milestone 4 covers it in depth. Here it is only a forward pointer.

## 1. What to learn
- Test-time compute: spending inference budget on sampling, scoring, and search instead of training a bigger model.
- Greedy decoding (keep the single best next step), beam search (keep k partial hypotheses alive), and MCTS (tree exploration with rollouts and a budget).
- Vocabulary: node, expansion, partial hypothesis, beam width, rollout, token budget.

## 2. Why it matters
- `harness.py` today does `--top-k` (best-of-k): it picks the best of already-finished candidates. That is the crudest possible search.
- Beam search is the bridge from "generate then rank" to "search while generating". Getting that distinction right is the whole milestone.

## 3. How to implement it
- Model a node as `(partial_path, score)`. Expansion means generating the next-step candidates.
- Implement three searchers over the SAME small problem and compare them:
  - **greedy**: keep only the single best child each step;
  - **beam(width=k)**: keep the k best partial paths each step and prune the rest;
  - **best-of-k**: generate k complete paths, keep the best one (what `harness.py` does today).
- Add a token-budget counter that stops expansion once the budget is spent.
- Suggested new file: `search_basics.py` in the repo root (stdlib only).

## 4. When to use it in an LLM harness
- Best-of-k: candidates are independent and you only need a final pick.
- Beam search: you can score partial output and want diversity under a fixed width.
- MCTS: the space is huge, steps are expensive, and you need budget-aware exploration.
- Token-budget accounting: any time inference cost is constrained.

## 5. Current gap vs this repo
- No tree, no nodes, no expansion, no beam width, no MCTS, no budget counter.
- Nothing to refactor — this milestone must be built from scratch in a new file.

## 6. Mini-project + pass criteria
- Build `search_basics.py` with greedy, beam, and best-of-k over a fixed 3-step problem where each step has 3 scored candidates.
- PASS when: (a) the three searchers produce different outcomes under the same budget; (b) you can state in one paragraph why beam differs from best-of-k; (c) the budget counter stops expansion correctly.

## 7. Record progress
- Append a dated entry under "## Milestone 1 — Search foundations" in `LEARNING_PROGRESS.md` (repo root), using the entry template in that file.
- Update the Milestone 1 row in that file's "Status at a glance" table.
