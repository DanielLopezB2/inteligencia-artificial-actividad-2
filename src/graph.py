"""Transport graph built exclusively from knowledge-base facts."""
from typing import NamedTuple


class Edge(NamedTuple):
    to: str
    line: str
    minutes: float


class Graph(NamedTuple):
    edges: dict[str, list[Edge]]
    coords: dict[str, tuple[float, float]]
    transfer_stations: set[str]


def build_graph(facts) -> Graph:
    """Turn `station`, `adjacent`, `location` and `transfer_station` facts into a Graph."""
    edges: dict[str, list[Edge]] = {f[1]: [] for f in facts if f[0] == "station"}
    for f in facts:
        if f[0] == "adjacent":
            _, a, b, line, minutes = f
            edges[a].append(Edge(b, line, minutes))
    for neighbors in edges.values():
        neighbors.sort()  # deterministic order for reproducible searches
    coords = {f[1]: (f[2], f[3]) for f in facts if f[0] == "location"}
    transfers = {f[1] for f in facts if f[0] == "transfer_station"}
    return Graph(edges, coords, transfers)
