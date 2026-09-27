---
name: milestone-2-prm-verifiers
description: 'Teach and practice Milestone 2: verifiers and process reward models — ORM vs PRM and scoring intermediate reasoning steps instead of only the final answer. Use when the user asks about ORM, PRM, process reward, verifier, reward model, or step-level scoring in the harness pipeline.'
---

# Milestone 2 — Verifiers & Process Reward Models (PRMs)

## When to Use
- "ORM vs PRM?", "How do I score a reasoning step?", "What is a process reward model?"
- "What am I missing for Milestone 2?", "Is step 3 a PRM?"

## Procedure
1. Read `AGENTS.md`, then open `harness.py` at `run_step_3`, `score_methods`, and `prompts/step_3.txt`.
2. Explain before changing code (learning mode — see `AGENTS.md`).
3. Guide the mini-project step by step; do not write it all for the user.
4. After the attempt, record the result (see section 7).

## Reading list
- **Let's Verify Step by Step** — Lightman et al., 2023, <https://arxiv.org/abs/2305.20050>. Process vs outcome supervision; releases PRM800K. The canonical ORM-vs-PRM comparison.
- **Solving math word problems with process- and outcome-based feedback** — Uesato et al., 2022, <https://arxiv.org/abs/2211.14275>. First comprehensive process vs outcome comparison (GSM8K).
- **Math-Shepherd** — Wang et al., 2024, <https://arxiv.org/abs/2312.08935>. Automatic process supervision — a PRM trained without human step labels.

## 1. What to learn
- ORM (Outcome Reward Model): one label for a completed answer, at the end.
- PRM (Process Reward Model): one label per intermediate step, so credit can be assigned to the step that went wrong.
- A verifier is anything that judges a candidate — a model, or deterministic tooling (Milestone 3 territory).

## 2. Why it matters
- `harness.py` step 3 already scores each candidate mid-pipeline, so it leans PRM-ward. Naming that distinction precisely is the milestone.
- Step-level credit is what lets you localize an error instead of only knowing "the final answer was wrong".

## 3. How to implement it
- Represent a reasoning attempt as a list of steps: `[step_1, step_2, ..., final]`.
- ORM: score only the final element. PRM: score every element.
- Build a tiny scorer (a dict mapping step -> 0.0..1.0, or one LLM call per step) and compare the two.
- Suggested new file: `reward_models.py` (stdlib only; no trained model is required to learn the shape).

## 4. When to use it in an LLM harness
- ORM: judging a final answer, e.g. "does this code pass the tests".
- PRM: debugging a multi-step answer, credit assignment, or guiding search toward the bad step.
- Deterministic verifier: when a tool (test runner, type checker) can judge more reliably than an LLM opinion.

## 5. Current gap vs this repo
- Step 3 is an LLM giving an opinion per key, then Python averages. It is a PRM stand-in, not a PRM: it scores completed candidates, not steps within one chain, and nothing is trained.

## 6. Mini-project + pass criteria
- Build `reward_models.py` with one deliberately corrupted 4-step trajectory. Score it once with an ORM and once with a PRM.
- PASS when: (a) the PRM scores flag the bad step but the ORM cannot; (b) you can explain in one paragraph why that difference exists.

## 7. Record progress
- Append a dated entry under "## Milestone 2 — PRMs & verifiers" in `LEARNING_PROGRESS.md` (repo root), using the entry template in that file.
- Update the Milestone 2 row in that file's "Status at a glance" table.
