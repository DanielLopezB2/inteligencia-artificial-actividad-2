from collections import deque
from pathlib import Path

import pytest

from src.graph import Edge, build_graph
from src.knowledge_base import load_knowledge_base

NETWORK = Path(__file__).resolve().parent.parent / "data" / "network.json"


@pytest.fixture(scope="module")
def graph():
    return build_graph(load_knowledge_base(NETWORK))


def test_all_stations_present(graph):
    assert len(graph.edges) == 20


def test_adjacency_is_symmetric_with_same_minutes(graph):
    for station, edges in graph.edges.items():
        for edge in edges:
            assert Edge(station, edge.line, edge.minutes) in graph.edges[edge.to]


def test_ricaurte_neighbors(graph):
    neighbors = {e.to: e.minutes for e in graph.edges["Ricaurte"]}
    assert neighbors == {"Centro Memoria": 5, "Puente Aranda": 4}


def test_transfer_stations(graph):
    assert graph.transfer_stations == {"Calle 26", "Centro Memoria", "Ricaurte"}


def test_every_station_has_coords(graph):
    assert set(graph.coords) == set(graph.edges)


def test_graph_is_connected(graph):
    start = next(iter(graph.edges))
    seen, queue = {start}, deque([start])
    while queue:
        for edge in graph.edges[queue.popleft()]:
            if edge.to not in seen:
                seen.add(edge.to)
                queue.append(edge.to)
    assert seen == set(graph.edges)


def test_neighbors_are_sorted(graph):
    for edges in graph.edges.values():
        assert edges == sorted(edges)


def test_isolated_station_has_empty_edge_list():
    facts = {
        ("station", "A"),
        ("station", "B"),
        ("station", "Z"),
        ("adjacent", "A", "B", "L1", 2),
        ("adjacent", "B", "A", "L1", 2),
        ("location", "Z", 4.6, -74.0),
    }
    graph = build_graph(facts)
    assert graph.edges["Z"] == []
    assert graph.edges["A"] == [Edge("B", "L1", 2)]
    assert graph.coords["Z"] == (4.6, -74.0)
