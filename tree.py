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