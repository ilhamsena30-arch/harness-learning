---
name: milestone-4-paper-prototype
description: 'Teach and practice Milestone 4: paper alignment and toy prototype — deconstruct Miyamoto et al. 2026 and build an AST-guided tree search on a multi-function coding task. Use when the user asks about Miyamoto 2026, paper alignment, search policies, or the final toy prototype.'
---

# Milestone 4 — Paper Alignment & Toy Prototype

## When to Use
- "What does Miyamoto et al. 2026 actually do?", "Let us build the toy prototype."
- "What am I missing for Milestone 4?"

## Procedure
1. Read `AGENTS.md`. The target paper is Miyamoto et al. 2026 (BG-MCTS), <https://arxiv.org/abs/2602.09574>; fetch it if needed.
2. Deconstruct the paper into: input, search policy, reward/verifier, pruning rule, budget.
3. Build the prototype by composing Milestones 1-3. Do not write it all at once.
4. After the attempt, record the result (see section 7).

## Reading list
- **BG-MCTS** — Miyamoto et al., 2026, <https://arxiv.org/abs/2602.09574>. **Primary paper — the target.** Tree-search policy aligned to a fixed token budget.
- **Scaling LLM Test-Time Compute Optimally** — Snell et al., 2024, <https://arxiv.org/abs/2408.03314>. Compute-optimal test-time scaling; process-based verifiers beat best-of-N.
- **Tree of Thoughts** — Yao et al., 2023, <https://arxiv.org/abs/2305.10601>. **Prerequisite — already read in Milestone 1.** The search framework your prototype composes with AST feedback.

## 1. What to learn
- How to read a paper and extract its search policy and math into runnable code.
- How AST feedback (M3) guides a search tree (M1) scored by a verifier (M2).

## 2. Why it matters
- This is the capstone: it proves the three earlier milestones compose into one working system.

## 3. How to implement it
- Define the task: a multi-function coding task where each function has candidate implementations.
- Generate candidates -> `ast.parse` each (M3) -> score (M2) -> expand/keep nodes under a budget (M1).
- Suggested new file: `ast_search.py`, importing helpers from the earlier milestone files.

## 4. When to use it in an LLM harness
- When a task decomposes into multiple functions and structure can guide search.
- When you want pruning based on code structure rather than model vibes.

## 5. Current gap vs this repo
- Nothing exists: no paper notes, no tree, no AST guidance. Milestones 1-3 must land first.

## 6. Mini-project + pass criteria
- Build `ast_search.py` end-to-end: generate multiple implementations per function, prune broken ones via `ast`, score the rest, and pick the best via tree search under a fixed budget.
- PASS when: (a) the run produces one chosen implementation per function; (b) you can point to the exact line where AST feedback pruned a candidate.

## 7. Record progress
- Append a dated entry under "## Milestone 4 — Paper prototype" in `LEARNING_PROGRESS.md` (repo root), using the entry template in that file.
- Update the Milestone 4 row in that file's "Status at a glance" table.
