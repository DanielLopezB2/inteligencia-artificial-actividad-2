"""Command-line interface: python -m src.cli [ORIGIN DESTINATION] [--list] [--penalty M]."""
import argparse
import difflib
import sys
import unicodedata
from itertools import groupby
from pathlib import Path

from src.graph import Graph, build_graph
from src.knowledge_base import load_knowledge_base
from src.search import TRANSFER_PENALTY, Route, find_route

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "network.json"


def _normalize(text: str) -> str:
    """Lowercase and strip accents so 'Héroes' and 'HEROES' compare equal."""
    decomposed = unicodedata.normalize("NFD", text.strip().lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def resolve_station(query: str, names) -> str:
    """Return the real station name matching the query, or raise ValueError with suggestions."""
    by_norm = {_normalize(n): n for n in names}
    key = _normalize(query)
    if key in by_norm:
        return by_norm[key]
    message = f"Unknown station: {query!r}."
    close = difflib.get_close_matches(key, by_norm, n=3, cutoff=0.6)
    if close:
        message += f" Did you mean: {', '.join(by_norm[c] for c in close)}?"
    raise ValueError(message)


def _legs(route: Route, graph: Graph) -> list[tuple[str, list[str], float]]:
    """Group consecutive hops on one line into (line, stations, ride minutes) legs."""
    legs, start = [], 0
    for line, hops in groupby(route.lines):
        end = start + len(list(hops))
        stops = route.stations[start : end + 1]
        minutes = sum(_hop_minutes(graph, a, b, line) for a, b in zip(stops, stops[1:]))
        legs.append((line, stops, minutes))
        start = end
    return legs


def _stops(n: int) -> str:
    return f"{n} stop" if n == 1 else f"{n} stops"


def _hop_minutes(graph: Graph, a: str, b: str, line: str) -> float:
    return min(e.minutes for e in graph.edges[a] if e.to == b and e.line == line)


def format_route(route: Route, graph: Graph, penalty: float) -> str:
    """Render a route as plain text: one line per leg, transfers in between, then totals."""
    lines = [f"Route: {route.stations[0]} -> {route.stations[-1]}"]
    previous = None
    for line, stops, minutes in _legs(route, graph):
        if previous is not None:
            lines.append(f"Transfer at {stops[0]}: {previous} -> {line}")
        lines.append(f"Ride {line}: {stops[0]} -> {stops[-1]} ({_stops(len(stops) - 1)}, {minutes:g} min)")
        previous = line
    lines.append(
        f"Ride time: {route.minutes:g} min | Transfers: {route.transfers} | "
        f"Total cost: {route.cost:.1f} (penalty {penalty} min per transfer)"
    )
    return "\n".join(lines)


def format_station_list(facts) -> str:
    """List stations grouped by line, marking those where lines cross."""
    transfers = {f[1] for f in facts if f[0] == "transfer_station"}
    by_line: dict[str, list[str]] = {}
    for _, station, line in sorted(f for f in facts if f[0] == "on_line"):
        by_line.setdefault(line, []).append(station)
    blocks = []
    for line, stations in by_line.items():
        marked = [f"  {s} (transfer)" if s in transfers else f"  {s}" for s in stations]
        blocks.append("\n".join([f"{line}:", *marked]))
    return "\n".join(blocks)


def _non_negative(text: str) -> float:
    value = float(text)
    if value < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return value


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src.cli", description="TransMilenio route planner.")
    p.add_argument("origin", nargs="?", help="origin station (prompted if omitted)")
    p.add_argument("destination", nargs="?", help="destination station (prompted if omitted)")
    p.add_argument("--list", action="store_true", help="list stations by line and exit")
    p.add_argument("--penalty", type=_non_negative, default=TRANSFER_PENALTY, metavar="MINUTES",
                   help=f"minutes charged per transfer (default {TRANSFER_PENALTY})")
    p.add_argument("--data", default=DEFAULT_DATA, help="path to network.json")
    return p


def _plan(args, facts, out) -> int:
    graph = build_graph(facts)
    origin = args.origin or input("Origin station: ")
    destination = args.destination or input("Destination station: ")
    try:
        origin = resolve_station(origin, graph.edges)
        destination = resolve_station(destination, graph.edges)
    except ValueError as err:
        print(err, file=out)
        return 1
    if origin == destination:
        print(f"You are already at {origin}.", file=out)
        return 0
    route = find_route(graph, origin, destination, args.penalty)
    if route is None:
        print(f"No route found from {origin} to {destination}.", file=out)
        return 1
    print(format_route(route, graph, args.penalty), file=out)
    return 0


def main(argv=None, out=sys.stdout) -> int:
    """Run the CLI and return the exit code (argparse errors still exit with 2)."""
    args = _parser().parse_args(argv)
    facts = load_knowledge_base(args.data)
    if args.list:
        print(format_station_list(facts), file=out)
        return 0
    return _plan(args, facts, out)


if __name__ == "__main__":
    raise SystemExit(main())
