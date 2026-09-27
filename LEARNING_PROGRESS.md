# Learning Progress — harness-learning

> Maintained by the milestone skills in `.github/skills/`. Each skill appends a
> dated entry after you attempt its mini-project. Read this file before resuming
> so an agent knows exactly where you stopped.
>
> This lives as a separate file (not inside `AGENTS.md`) on purpose: `AGENTS.md`
> loads into context on every interaction, so progress notes stay here to keep
> that file cheap and instruction-only.

## Status at a glance

| Milestone | Status | Last entry |
|---|---|---|
| 1 — Search foundations | PARTIAL — concepts understood, code authored with reference | 2026-09-27 |
| 2 — PRMs & verifiers | not started (harness pipeline exists) | — |
| 3 — Static analysis | not started | — |
| 4 — Paper prototype | not started | — |

## Entry template

Use this shape for every log entry (one per attempt):

```
- **Date:** YYYY-MM-DD
- **What I tried:** one or two sentences
- **Pass / fail:** PASS | FAIL | PARTIAL
- **What I learned:** the one concept that landed
- **What changed in the repo:** files added/edited, or "none"
```

## Milestone 1 — Search foundations

- **Date:** 2026-09-27
- **What I tried:** Built `search_basics.py` with greedy, beam, and best-of-k over a
  3-step tree. Wrote `greedy_search` myself. Attempted `beam_search` twice and hit
  the same mental blocker both times (treating the beam as one path, and pruning
  inside the generate loop). Read the `correct_beam_search` reference; `best_of_k`
  was authored for me.
- **Pass / fail:** PARTIAL
- **What I learned:**
  - Beam differs from best-of-k because beam keeps k **partial** hypotheses alive
    and prunes *while* generating, so a locally weak step (B: 6 < A: 9) can still
    recover and win (B1 → 11.0). Best-of-k generates k **complete** paths first and
    only prunes at the end, so it is blind to a weak-then-strong branch.
  - Two bugs to remember: (1) each round's output must have the **same type** as
    its input (a float score cannot be expanded next round — paths are what you
    keep, scores are only for ranking); (2) **generate and prune must be separate
    blocks**, never interleaved.
  - Budget matters: best-of-k is budget-fragile (returns root at budget < 5),
    beam degrades gracefully (reaches the 11.0 optimum at budget 2).
- **What changed in the repo:** added `search_basics.py`
- **Not yet demonstrated:** writing `beam_search` / `best_of_k` unaided. Currently
  at the read-and-recognize stage, not yet produce-from-memory.
- **Re-attempt flag:** revisit before Milestone 4 — BG-MCTS is built directly on
  beam search.

## Milestone 2 — PRMs & verifiers

(no entries yet)

## Milestone 3 — Static analysis

(no entries yet)

## Milestone 4 — Paper prototype

(no entries yet)
