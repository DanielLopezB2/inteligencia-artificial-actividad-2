import heapq
from itertools import permutations
from pathlib import Path

import pytest

from src.graph import Edge, Graph, build_graph
from src.knowledge_base import load_knowledge_base
from src.search import TRANSFER_PENALTY, Route, find_route

NETWORK = Path(__file__).resolve().parent.parent / "data" / "network.json"


@pytest.fixture(scope="module")
def graph():
    return build_graph(load_knowledge_base(NETWORK))


def dijkstra_cost(graph, origin, destination, penalty=TRANSFER_PENALTY):
    """Brute-force reference over (station, line) states; no heuristic."""
    heap = [(0.0, 0, origin, None)]
    best = {}
    while heap:
        cost, n, station, line = heapq.heappop(heap)
        if (station, line) in best:
            continue
        best[(station, line)] = cost
        if station == destination:
            return cost
        for e in graph.edges[station]:
            extra = penalty if line is not None and e.line != line else 0.0
            heapq.heappush(heap, (cost + e.minutes + extra, n + 1, e.to, e.line))
    return None


def line_graph(*edges, coords=None):
    """Build a symmetric graph from (a, b, line, minutes) tuples, all on the equator."""
    adj: dict[str, list[Edge]] = {}
    for a, b, line, minutes in edges:
        adj.setdefault(a, []).append(Edge(b, line, minutes))
        adj.setdefault(b, []).append(Edge(a, line, minutes))
    names = sorted(adj)
    coords = coords or {n: (0.0, i * 0.01) for i, n in enumerate(names)}
    return Graph(adj, coords, set())


def test_single_line_route_has_no_transfers(graph):
    route = find_route(graph, "Portal Américas", "Ricaurte")
    assert route.stations[0] == "Portal Américas"
    assert route.stations[-1] == "Ricaurte"
    assert route.transfers == 0
    assert route.cost == route.minutes


def test_multi_transfer_route_is_consistent(graph):
    route = find_route(graph, "Portal Américas", "Calle 100")
    assert route.transfers >= 1
    assert len(route.lines) == len(route.stations) - 1
    changes = sum(a != b for a, b in zip(route.lines, route.lines[1:]))
    assert changes == route.transfers
    total = 0.0
    for a, b, line in zip(route.stations, route.stations[1:], route.lines):
        edge = next(e for e in graph.edges[a] if e.to == b and e.line == line)
        total += edge.minutes
    assert route.minutes == total
    assert route.cost == total + TRANSFER_PENALTY * route.transfers


def test_optimal_cost_for_all_pairs(graph):
    for a, b in permutations(graph.edges, 2):
        route = find_route(graph, a, b)
        assert route.cost == pytest.approx(dijkstra_cost(graph, a, b)), (a, b)


def test_cost_is_symmetric(graph):
    for a, b in permutations(graph.edges, 2):
        assert find_route(graph, a, b).cost == pytest.approx(find_route(graph, b, a).cost)


def test_tie_break_prefers_fewer_transfers():
    # A->D: direct on L1 costs 10; via B on L2 then L3 costs 5 + 0 + ... = 10 with 1 transfer.
    g = line_graph(
        ("A", "B", "L1", 5), ("B", "D", "L1", 5),
        ("A", "C", "L2", 2.5), ("C", "D", "L3", 2.5),
    )
    route = find_route(g, "A", "D", transfer_penalty=5.0)
    # L2->L3 route: 5 minutes + 5 penalty = 10, same as L1 route (10, 0 transfers).
    assert route.cost == 10
    assert route.transfers == 0
    assert route.lines == ["L1", "L1"]


def test_higher_penalty_changes_route():
    g = line_graph(
        ("A", "B", "L1", 10), ("B", "D", "L1", 10),
        ("A", "C", "L2", 4), ("C", "D", "L3", 4),
    )
    cheap = find_route(g, "A", "D", transfer_penalty=1.0)
    costly = find_route(g, "A", "D", transfer_penalty=20.0)
    assert cheap.stations == ["A", "C", "D"] and cheap.transfers == 1
    assert costly.stations == ["A", "B", "D"] and costly.transfers == 0


def test_unreachable_returns_none():
    g = line_graph(("A", "B", "L1", 3), ("C", "D", "L2", 3))
    assert find_route(g, "A", "D") is None


def test_unknown_station_raises(graph):
    with pytest.raises(ValueError, match="Atlantis"):
        find_route(graph, "Atlantis", "Ricaurte")
    with pytest.raises(ValueError, match="Nowhere"):
        find_route(graph, "Ricaurte", "Nowhere")


def test_origin_equals_destination(graph):
    route = find_route(graph, "Ricaurte", "Ricaurte")
    assert route == Route(["Ricaurte"], [], 0.0, 0, 0.0)
