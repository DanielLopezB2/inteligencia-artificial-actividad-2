"""Knowledge base for the TransMilenio network: a tiny Horn-clause engine plus loader.

Facts are tuples such as ("segment", "A", "B", "Caracas", 2). Variables are strings
starting with "?". Rules are Rule(head, body); the body may contain the builtin
("!=", "?x", "?y"), which must appear after the atoms that bind its variables.
"""
import json
from pathlib import Path
from typing import Iterator, NamedTuple

Atom = tuple
Bindings = dict


class Rule(NamedTuple):
    head: Atom
    body: list


# ---------------------------------------------------------------- engine

def _is_var(term) -> bool:
    return isinstance(term, str) and term.startswith("?")


def _match(atom: Atom, fact: Atom, bindings: Bindings) -> Bindings | None:
    """Unify one atom with one ground fact; return extended bindings or None."""
    if len(atom) != len(fact):
        return None
    out = dict(bindings)
    for term, value in zip(atom, fact):
        if _is_var(term):
            if out.setdefault(term, value) != value:
                return None
        elif term != value:
            return None
    return out


def _solve(body: list, facts: set, bindings: Bindings) -> Iterator[Bindings]:
    """Yield every binding set that satisfies all atoms of the body."""
    if not body:
        yield bindings
        return
    first, rest = body[0], body[1:]
    if first[0] == "!=":
        left, right = (bindings.get(t, t) for t in first[1:])
        if left != right:
            yield from _solve(rest, facts, bindings)
        return
    for fact in facts:
        extended = _match(first, fact, bindings)
        if extended is not None:
            yield from _solve(rest, facts, extended)


def _substitute(atom: Atom, bindings: Bindings) -> Atom:
    return tuple(bindings[t] if _is_var(t) else t for t in atom)


def forward_chain(facts, rules) -> set:
    """Apply rules repeatedly until no new fact appears (fixpoint). Input is not mutated."""
    known = set(facts)
    while True:
        new = {
            _substitute(rule.head, b)
            for rule in rules
            for b in _solve(rule.body, known, {})
        } - known
        if not new:
            return known
        known |= new


def query(facts, pattern: Atom) -> list[Bindings]:
    """Return the variable bindings of every fact matching the pattern."""
    return [b for f in facts if (b := _match(pattern, f, {})) is not None]


# ------------------------------------------------- declarative domain rules

RULES = [
    # Segments are stored once, but travel works in both directions.
    Rule(("adjacent", "?a", "?b", "?l", "?m"), [("segment", "?a", "?b", "?l", "?m")]),
    Rule(("adjacent", "?b", "?a", "?l", "?m"), [("segment", "?a", "?b", "?l", "?m")]),
    # A station served by two different lines allows changing lines.
    Rule(
        ("transfer_station", "?s"),
        [("on_line", "?s", "?l1"), ("on_line", "?s", "?l2"), ("!=", "?l1", "?l2")],
    ),
]


# ------------------------------------------------------------------ loader

def load_knowledge_base(path, rules=RULES) -> set:
    """Load network.json, validate it, and return base plus derived facts."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    stations = {s["name"] for s in data["stations"]}
    facts = {("station", name) for name in stations}

    for line, stops in data["lines"].items():
        for stop in stops:
            if stop not in stations:
                raise ValueError(f"unknown station {stop!r} in line {line!r}")
            facts.add(("on_line", stop, line))

    for seg in data["segments"]:
        a, b, line, minutes = seg["station_a"], seg["station_b"], seg["line"], seg["minutes"]
        for name in (a, b):
            if name not in stations:
                raise ValueError(f"unknown station {name!r} in segment {a}-{b}")
        if not isinstance(minutes, (int, float)) or minutes <= 0:
            raise ValueError(f"minutes must be positive in segment {a}-{b}: {minutes!r}")
        for name in (a, b):
            if ("on_line", name, line) not in facts:
                raise ValueError(f"station {name!r} is not on line {line!r} (segment {a}-{b})")
        facts.add(("segment", a, b, line, minutes))

    return forward_chain(facts, rules)
