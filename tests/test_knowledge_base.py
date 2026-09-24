import json
from pathlib import Path

import pytest

from src.knowledge_base import Rule, forward_chain, load_knowledge_base, query

NETWORK = Path(__file__).resolve().parent.parent / "data" / "network.json"


# ---------- engine ----------

def test_forward_chain_keeps_base_facts():
    facts = {("p", "a")}
    assert ("p", "a") in forward_chain(facts, [])


def test_rule_fires_and_binds_variables():
    rules = [Rule(("q", "?x"), [("p", "?x")])]
    result = forward_chain({("p", "a"), ("p", "b")}, rules)
    assert {("q", "a"), ("q", "b")} <= result


def test_rule_with_join():
    rules = [Rule(("gp", "?x", "?z"), [("parent", "?x", "?y"), ("parent", "?y", "?z")])]
    result = forward_chain({("parent", "a", "b"), ("parent", "b", "c")}, rules)
    assert ("gp", "a", "c") in result


def test_not_equal_builtin_filters():
    rules = [Rule(("diff", "?x", "?y"), [("v", "?x"), ("v", "?y"), ("!=", "?x", "?y")])]
    result = forward_chain({("v", 1), ("v", 2)}, rules)
    assert ("diff", 1, 2) in result and ("diff", 2, 1) in result
    assert ("diff", 1, 1) not in result


def test_fixpoint_terminates_on_recursive_rules():
    rules = [
        Rule(("reach", "?x", "?y"), [("edge", "?x", "?y")]),
        Rule(("reach", "?x", "?z"), [("reach", "?x", "?y"), ("edge", "?y", "?z")]),
    ]
    cycle = {("edge", "a", "b"), ("edge", "b", "c"), ("edge", "c", "a")}
    result = forward_chain(cycle, rules)
    assert len([f for f in result if f[0] == "reach"]) == 9


def test_forward_chain_does_not_mutate_input():
    facts = {("p", "a")}
    forward_chain(facts, [Rule(("q", "?x"), [("p", "?x")])])
    assert facts == {("p", "a")}


def test_query_returns_bindings():
    facts = {("p", "a", 1), ("p", "b", 2)}
    assert sorted(query(facts, ("p", "?n", "?v")), key=lambda b: b["?n"]) == [
        {"?n": "a", "?v": 1},
        {"?n": "b", "?v": 2},
    ]


def test_query_with_constant_and_no_match():
    facts = {("p", "a", 1)}
    assert query(facts, ("p", "a", "?v")) == [{"?v": 1}]
    assert query(facts, ("p", "z", "?v")) == []


def test_query_repeated_variable_must_agree():
    facts = {("p", "a", "a"), ("p", "a", "b")}
    assert query(facts, ("p", "?x", "?x")) == [{"?x": "a"}]


# ---------- real data ----------

@pytest.fixture(scope="module")
def kb():
    return load_knowledge_base(NETWORK)


def test_adjacency_is_symmetric_and_keeps_line_and_minutes(kb):
    forward = query(kb, ("adjacent", "Calle 72", "Calle 63", "?l", "?m"))
    backward = query(kb, ("adjacent", "Calle 63", "Calle 72", "?l", "?m"))
    assert forward and forward == backward
    assert forward[0]["?l"] == "Caracas" and forward[0]["?m"] > 0


def test_every_segment_yields_both_adjacent_directions(kb):
    for _, a, b, line, minutes in (f for f in kb if f[0] == "segment"):
        assert ("adjacent", a, b, line, minutes) in kb
        assert ("adjacent", b, a, line, minutes) in kb


def test_transfer_stations_detected(kb):
    transfers = {b["?s"] for b in query(kb, ("transfer_station", "?s"))}
    assert {"Calle 26", "Ricaurte", "Centro Memoria"} <= transfers
    assert "Calle 72" not in transfers


# ---------- data integrity ----------

def test_network_file_integrity():
    data = json.loads(NETWORK.read_text(encoding="utf-8"))
    names = {s["name"] for s in data["stations"]}
    assert 15 <= len(names) <= 25
    segments = {(s["station_a"], s["station_b"], s["line"]) for s in data["segments"]}
    segments |= {(b, a, l) for a, b, l in segments}
    for line, stops in data["lines"].items():
        assert set(stops) <= names
        for a, b in zip(stops, stops[1:]):
            assert (a, b, line) in segments, f"missing segment {a}-{b} on {line}"
    assert "_note" in data


# ---------- validation ----------

def _write(tmp_path, **overrides):
    data = {
        "stations": [
            {"name": "A", "lat": 4.6, "lon": -74.0},
            {"name": "B", "lat": 4.7, "lon": -74.1},
        ],
        "lines": {"L1": ["A", "B"]},
        "segments": [{"station_a": "A", "station_b": "B", "line": "L1", "minutes": 2}],
    }
    data.update(overrides)
    path = tmp_path / "net.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_location_facts_keep_coordinates(tmp_path):
    facts = load_knowledge_base(_write(tmp_path))
    assert ("location", "A", 4.6, -74.0) in facts


def test_valid_minimal_network_loads(tmp_path):
    facts = load_knowledge_base(_write(tmp_path))
    assert ("station", "A") in facts and ("on_line", "A", "L1") in facts


def test_unknown_station_in_line_raises(tmp_path):
    with pytest.raises(ValueError, match="unknown station"):
        load_knowledge_base(_write(tmp_path, lines={"L1": ["A", "Z"]}))


def test_unknown_station_in_segment_raises(tmp_path):
    seg = [{"station_a": "A", "station_b": "Z", "line": "L1", "minutes": 2}]
    with pytest.raises(ValueError, match="unknown station"):
        load_knowledge_base(_write(tmp_path, segments=seg))


@pytest.mark.parametrize("minutes", [0, -3])
def test_non_positive_minutes_raises(tmp_path, minutes):
    seg = [{"station_a": "A", "station_b": "B", "line": "L1", "minutes": minutes}]
    with pytest.raises(ValueError, match="minutes"):
        load_knowledge_base(_write(tmp_path, segments=seg))


def test_segment_station_not_on_declared_line_raises(tmp_path):
    with pytest.raises(ValueError, match="not on line"):
        load_knowledge_base(_write(tmp_path, lines={"L1": ["A"], "L2": ["B"]}))
