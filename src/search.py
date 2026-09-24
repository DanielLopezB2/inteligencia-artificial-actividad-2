"""A* route search over (station, line) states with a transfer penalty."""
import heapq
from itertools import count
from math import asin, cos, radians, sin, sqrt
from typing import NamedTuple

from src.graph import Graph

TRANSFER_PENALTY = 5.0  # minutes charged each time the line changes


class Route(NamedTuple):
    stations: list[str]
    lines: list[str]  # line used for each hop
    minutes: float  # ride time only
    transfers: int
    cost: float  # minutes + penalty * transfers


def haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in km between two (lat, lon) points."""
    lat1, lon1, lat2, lon2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(h))


def max_speed(graph: Graph) -> float:
    """Fastest km/min over all edges, so distance / v_max never overestimates a ride.

    h(n) = dist(n, goal) / v_max is admissible (no edge beats v_max, and the straight
    line is the shortest path) and consistent (triangle inequality on distance).
    The transfer penalty is left out of h, which keeps it a lower bound.
    """
    return max(
        haversine_km(graph.coords[a], graph.coords[e.to]) / e.minutes
        for a, edges in graph.edges.items()
        for e in edges
    )


def _rebuild(closed, state, cost: float, transfers: int) -> Route:
    """Walk parent links back from the goal state."""
    stations, lines, minutes = [], [], 0.0
    while state is not None:
        prev, ride = closed[state]
        stations.append(state[0])
        if prev is not None:
            lines.append(state[1])
            minutes += ride
        state = prev
    return Route(stations[::-1], lines[::-1], minutes, transfers, cost)


def find_route(
    graph: Graph, origin: str, destination: str, transfer_penalty: float = TRANSFER_PENALTY
) -> Route | None:
    """Cheapest route (minutes + transfer penalties); ties go to fewer transfers."""
    for name in (origin, destination):
        if name not in graph.edges:
            raise ValueError(f"Unknown station: {name}")
    v_max = max_speed(graph)
    goal = graph.coords[destination]

    def h(station: str) -> float:
        return haversine_km(graph.coords[station], goal) / v_max

    tick = count()  # insertion order keeps the heap deterministic
    start = (origin, None)
    heap = [(h(origin), 0, next(tick), 0.0, 0.0, start, None)]
    closed: dict = {}  # state -> (parent state, ride minutes)
    while heap:
        _, transfers, _, g, ride, state, parent = heapq.heappop(heap)
        if state in closed:
            continue
        closed[state] = (parent, ride)
        station, line = state
        if station == destination:
            return _rebuild(closed, state, g, transfers)
        for e in graph.edges[station]:
            changed = line is not None and e.line != line
            g2 = g + e.minutes + (transfer_penalty if changed else 0.0)
            t2 = transfers + changed
            heapq.heappush(heap, (g2 + h(e.to), t2, next(tick), g2, e.minutes, (e.to, e.line), state))
    return None
