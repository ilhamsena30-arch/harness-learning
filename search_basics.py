"""Milestone 1 practice: greedy vs beam vs best-of-k on one tiny search tree.

This file makes ONE distinction concrete:

- greedy       keeps the single best partial path and commits to it each step.
- beam(width)  keeps `width` partial paths alive and prunes the rest each step.
- best-of-k    generates k COMPLETE paths first, then keeps the best one.

`harness.py` already does the third one (its --top-k over finished candidates).
The first two are what a real search tree adds: pruning *while* generating.

Token budget: each node "expansion" (enumerating a node's children) costs
1 token. Every searcher must stop when its budget is spent, which is how a
search tree respects an inference cost limit.
"""

# A 3-step search tree. Each node is {"reward": float, "children": [names]}.
# Path score = sum of the rewards along the path (root counts as 0.0).
TREE = {
    "root": {"reward": 0.0, "children": ["A", "B", "C"]},
    "A": {"reward": 9.0, "children": ["A1", "A2", "A3"]},
    "B": {"reward": 6.0, "children": ["B1", "B2", "B3"]},
    "C": {"reward": 1.0, "children": ["C1", "C2", "C3"]},
    "A1": {"reward": 1.0, "children": ["A1a", "A1b", "A1c"]},
    "A2": {"reward": 1.0, "children": ["A2a", "A2b", "A2c"]},
    "A3": {"reward": 1.0, "children": ["A3a", "A3b", "A3c"]},
    "B1": {"reward": 5.0, "children": ["B1a", "B1b", "B1c"]},
    "B2": {"reward": 4.0, "children": ["B2a", "B2b", "B2c"]},
    "B3": {"reward": 3.0, "children": ["B3a", "B3b", "B3c"]},
    "C1": {"reward": 1.0, "children": ["C1a", "C1b", "C1c"]},
    "C2": {"reward": 1.0, "children": ["C2a", "C2b", "C2c"]},
    "C3": {"reward": 1.0, "children": ["C3a", "C3b", "C3c"]},
}

# The 27 leaves at depth 3 all score 0.0 and have no children.
for _name in (
    "A1a", "A1b", "A1c", "A2a", "A2b", "A2c", "A3a", "A3b", "A3c",
    "B1a", "B1b", "B1c", "B2a", "B2b", "B2c", "B3a", "B3b", "B3c",
    "C1a", "C1b", "C1c", "C2a", "C2b", "C2c", "C3a", "C3b", "C3c",
):
    TREE[_name] = {"reward": 0.0, "children": []}


def path_score(path):
    """Sum the rewards along a path of node names, e.g. ["root", "B", "B1", "B1a"]."""
    return sum(TREE[name]["reward"] for name in path)


def greedy_search(tree, budget=10):
    """Commit to the single best child at each step until a leaf or the budget
    is spent. Return (path, score).

    Think: what does "best child" mean when you can only see one step ahead?

    PROS
      - Cheapest search: it tracks ONE path, so it spends ~`depth` expansions
        in total (here: 3) regardless of how big the tree is.
      - Trivial to read and reason about -- a single loop, no pruning step.
      - Deterministic and fast. Good when each individual step is reliable.

    CONS
      - Myopic: once it picks a child it never reconsiders, so a locally
        best-looking first step can doom the whole path.
      - On this tree it scores 10.0 and never visits branch B at all, missing
        the 11.0 optimum.
      - No diversity: you learn nothing about the branches it rejected.

    USE WHEN
      - Each step is cheap and mostly reliable, or you need a fast baseline
        to compare real search against.
    """
    path = ["root"]
    current = "root"

    # This counter is what the budget actually is. Keep it separate from the
    # `budget` parameter so we count down locally instead of rewriting the
    # caller's argument.
    remaining = budget

    children = tree[current]["children"]
    while children and remaining > 0:
        sorted_children = sorted(
            children,
            key=lambda name: tree[name]["reward"],
            reverse=True,
        )
        highest = sorted_children[0]

        remaining -= 1  # one expansion spent (a leaf costs nothing to visit)
        path.append(highest)
        current = highest
        children = tree[current]["children"]

    return path, path_score(path)


def beam_search(tree, width=2, budget=10):
    """Keep the `width` best partial paths at each step and prune the rest.

    Return the best (path, score) found when the budget is spent or all kept
    paths reach leaves. Partial paths are scored by path_score, not by any
    single node's reward.

    PROS
      - Keeps `width` hypotheses alive, so a locally weak step can still
        recover. Here B looked worse than A (6 vs 9) but led to the 11.0
        optimum -- exactly the case greedy cannot handle.
      - Prunes WHILE generating, so cost scales with `width`, not tree size.
      - `width` is one knob that trades answer quality against token budget.

    CONS
      - ~`width` expansions per level: roughly width-times the cost of greedy.
      - Pruning by `path_score` can discard a path that WOULD have scored higher
        later. The score is a guess about the future, not a fact about it.
      - No guarantee of the true optimum: a bad score function makes search bad.

    USE WHEN
      - You can score partial hypotheses and want diversity under a fixed
        budget (the usual case for LLM harnesses).
    """
    # ---------------------------------------------------------------------
    # SETUP
    # The beam is a LIST of partial paths. Each path is itself a list of
    # node names, e.g. ["root", "A"]. It starts with one path: just the root.
    # ---------------------------------------------------------------------
    # STEP 1 (given to you) — "generate": turn the current beam into a list
    beam = [["root"]]
    candidates = []
    for path in beam:
        node = path[-1]
        for child in tree[node]["children"]:
            candidates.append(path + [child])
        # remaining -= 1   # TODO (Step 3): this needs `remaining` defined first

    # ---------------------------------------------------------------------
    # STEP 2 (your turn) — "prune": keep only the best `width` of `candidates`.
    # Hint: this is the same move as harness.py's rank_methods — sort by
    # path_score, then slice.
    # ---------------------------------------------------------------------
    scores = 0
    max_score = 0
    for candidate in candidates:
        for candidate_root in candidate:
            scores = tree[candidate_root]["reward"]
            scores += scores
            max_score = max(max_score, scores)


    # ---------------------------------------------------------------------
    # STEP 3 (your turn) — "loop": wrap steps 1-2 in a loop that goes one level
    # deeper each round. It must stop when the beam stops growing (all paths
    # are leaves) or when the token budget runs out.
    # Also add `remaining = budget` near the top, so the budget is spent down.
    # ---------------------------------------------------------------------

    # ---------------------------------------------------------------------
    # STEP 4 (your turn) — "return": hand back the best (path, score) currently
    # in the beam, using max(beam, key=...).
    # ---------------------------------------------------------------------
    raise NotImplementedError("TODO: replace this line with your implementation")


def correct_beam_search(tree, width=2, budget=10):
    """REFERENCE implementation — read this only after trying your own.

    Same tree, same width, same budget. The three things your version got
    differently are marked with <<< below.
    """
    # <<< 1. The beam stays a LIST OF PATHS the whole time. Every round it is
    #        replaced by the pruned candidates, so the next round has the same
    #        type as the input (`list[list[str]]`). No scores are stored.
    beam = [["root"]]

    # <<< 2. The budget is a real counter, spent down by expansions.
    remaining = budget

    while remaining > 0:
        # --- generate: every candidate is one step longer than its parent ---
        candidates = []
        for path in beam:                      # outer loop over PATHS
            node = path[-1]                    # a path's newest node
            children = tree[node]["children"]
            if not children:
                continue                       # a leaf costs nothing, expands to nothing
            for child in children:             # inner loop over that node's CHILDREN
                candidates.append(path + [child])   # a NEW list, never path.append()
            remaining -= 1                     # one expansion = one token

        # --- stop condition: nothing left to expand means we are done ---
        if not candidates:
            break

        # --- prune: keep the best `width` paths, ranked by path_score ---
        beam = sorted(candidates, key=path_score, reverse=True)[:width]

    # --- return the best (path, score) currently in the beam ---
    best = max(beam, key=path_score)
    return best, path_score(best)


def best_of_k(tree, k=2, budget=10):
    """Generate the first k COMPLETE paths (left-to-right depth-first) and
    return the best one.

    This mirrors harness.py's --top-k: it only sees the candidates it generates,
    and it never prunes mid-way.

    PROS
      - Simplest possible search: generate k whole answers, then pick. No
        partial scoring is needed at all -- only a final judgment.
      - Candidates are independent, so they can be produced in parallel
        (the one search that parallelises trivially).
      - Works with any generator, because it never inspects the internals.

    CONS
      - Wastes budget on branches it will never use: no mid-way pruning, so a
        hopeless path is still generated to completion.
      - Diversity is only whatever the sampling gave you. If all k candidates
        happen to be bad, keeping k of them changes nothing.
      - Blind to a weak first step that leads somewhere good. Here the first
        two complete paths both live under branch A, so it scores 10.0 and
        never reaches B's 11.0 optimum.

    USE WHEN
      - Candidates are cheap and independent, and one final judgment is enough
        (a natural fit for 'generate N, pick the best' harnesses).
    """
    complete = []          # collected COMPLETE paths (root -> leaf)
    remaining = budget

    # An explicit stack makes the depth-first walk visible. Each entry is a
    # partial path, exactly like the beam in beam_search.
    stack = [["root"]]
    while stack and len(complete) < k and remaining > 0:
        path = stack.pop()
        node = path[-1]
        children = tree[node]["children"]

        if not children:
            complete.append(path)   # reached a leaf: this is a finished candidate
            continue

        remaining -= 1              # one expansion spent
        # Push children in REVERSE so the leftmost child is popped first,
        # giving the left-to-right order promised in the docstring.
        for child in reversed(children):
            stack.append(path + [child])

    # Guard: if the budget was too small to finish even one path, fall back to
    # the root so the caller still gets a valid (path, score) pair.
    if not complete:
        complete = [["root"]]

    best = max(complete, key=path_score)
    return best, path_score(best)


def main():
    """Print the three searchers side by side so their answers can be compared."""
    print("greedy        :", greedy_search(TREE))
    # print("beam(2)       :", beam_search(TREE, width=2))          # your attempt
    print("beam(2) ref   :", correct_beam_search(TREE, width=2))
    print("best-of-2     :", best_of_k(TREE, k=2))


if __name__ == "__main__":
    main()
