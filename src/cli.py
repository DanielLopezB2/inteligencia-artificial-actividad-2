"""Command-line interface: python -m src.cli [ORIGIN DESTINATION] [--list] [--penalty M] [--lang es|en]."""
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
DEFAULT_LANG = "es"

MESSAGES = {
    "en": {
        "route": "Route: {origin} -> {destination}",
        "leg": "Ride {line}: {origin} -> {destination} ({stops}, {minutes:g} min)",
        "transfer": "Transfer at {station}: {previous} -> {line}",
        "totals": (
            "Ride time: {minutes:g} min | Transfers: {transfers} | "
            "Total cost: {cost:.1f} (penalty {penalty} min per transfer)"
        ),
        "stop_one": "{n} stop",
        "stop_many": "{n} stops",
        "same_station": "You are already at {station}.",
        "unknown_station": "Unknown station: {query!r}.",
        "did_you_mean": " Did you mean: {options}?",
        "no_route": "No route found from {origin} to {destination}.",
        "transfer_marker": "transfer",
        "prompt_origin": "Origin station: ",
        "prompt_destination": "Destination station: ",
    },
    "es": {
        "route": "Ruta: {origin} -> {destination}",
        "leg": "Tramo {line}: {origin} -> {destination} ({stops}, {minutes:g} min)",
        "transfer": "Transbordo en {station}: {previous} -> {line}",
        "totals": (
            "Tiempo de viaje: {minutes:g} min | Transbordos: {transfers} | "
            "Costo total: {cost:.1f} (penalización de {penalty} min por transbordo)"
        ),
        "stop_one": "{n} parada",
        "stop_many": "{n} paradas",
        "same_station": "Ya estás en {station}.",
        "unknown_station": "Estación desconocida: {query!r}.",
        "did_you_mean": " ¿Quisiste decir: {options}?",
        "no_route": "No se encontró una ruta de {origin} a {destination}.",
        "transfer_marker": "transbordo",
        "prompt_origin": "Estación de origen: ",
        "prompt_destination": "Estación de destino: ",
    },
}


def _t(lang: str, key: str, **values) -> str:
    """Look up a message template in the given language and fill it in."""
    return MESSAGES[lang][key].format(**values)


def _normalize(text: str) -> str:
    """Lowercase and strip accents so 'Héroes' and 'HEROES' compare equal."""
    decomposed = unicodedata.normalize("NFD", text.strip().lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def resolve_station(query: str, names, lang: str = DEFAULT_LANG) -> str:
    """Return the real station name matching the query, or raise ValueError with suggestions."""
    by_norm = {_normalize(n): n for n in names}
    key = _normalize(query)
    if key in by_norm:
        return by_norm[key]
    message = _t(lang, "unknown_station", query=query)
    close = difflib.get_close_matches(key, by_norm, n=3, cutoff=0.6)
    if close:
        message += _t(lang, "did_you_mean", options=", ".join(by_norm[c] for c in close))
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


def _stops(n: int, lang: str) -> str:
    return _t(lang, "stop_one" if n == 1 else "stop_many", n=n)


def _hop_minutes(graph: Graph, a: str, b: str, line: str) -> float:
    return min(e.minutes for e in graph.edges[a] if e.to == b and e.line == line)


def format_route(route: Route, graph: Graph, penalty: float, lang: str = DEFAULT_LANG) -> str:
    """Render a route as plain text: one line per leg, transfers in between, then totals."""
    lines = [_t(lang, "route", origin=route.stations[0], destination=route.stations[-1])]
    previous = None
    for line, stops, minutes in _legs(route, graph):
        if previous is not None:
            lines.append(_t(lang, "transfer", station=stops[0], previous=previous, line=line))
        lines.append(_t(lang, "leg", line=line, origin=stops[0], destination=stops[-1],
                        stops=_stops(len(stops) - 1, lang), minutes=minutes))
        previous = line
    lines.append(_t(lang, "totals", minutes=route.minutes, transfers=route.transfers,
                    cost=route.cost, penalty=penalty))
    return "\n".join(lines)


def format_station_list(facts, lang: str = DEFAULT_LANG) -> str:
    """List stations grouped by line, marking those where lines cross."""
    transfers = {f[1] for f in facts if f[0] == "transfer_station"}
    by_line: dict[str, list[str]] = {}
    for _, station, line in sorted(f for f in facts if f[0] == "on_line"):
        by_line.setdefault(line, []).append(station)
    marker = _t(lang, "transfer_marker")
    blocks = []
    for line, stations in by_line.items():
        marked = [f"  {s} ({marker})" if s in transfers else f"  {s}" for s in stations]
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
    p.add_argument("--lang", choices=sorted(MESSAGES), default=DEFAULT_LANG,
                   help=f"output language (default {DEFAULT_LANG})")
    p.add_argument("--data", default=DEFAULT_DATA, help="path to network.json")
    return p


def _plan(args, facts, out) -> int:
    graph = build_graph(facts)
    lang = args.lang
    origin = args.origin or input(_t(lang, "prompt_origin"))
    destination = args.destination or input(_t(lang, "prompt_destination"))
    try:
        origin = resolve_station(origin, graph.edges, lang)
        destination = resolve_station(destination, graph.edges, lang)
    except ValueError as err:
        print(err, file=out)
        return 1
    if origin == destination:
        print(_t(lang, "same_station", station=origin), file=out)
        return 0
    route = find_route(graph, origin, destination, args.penalty)
    if route is None:
        print(_t(lang, "no_route", origin=origin, destination=destination), file=out)
        return 1
    print(format_route(route, graph, args.penalty, lang), file=out)
    return 0


def main(argv=None, out=sys.stdout) -> int:
    """Run the CLI and return the exit code (argparse errors still exit with 2)."""
    args = _parser().parse_args(argv)
    facts = load_knowledge_base(args.data)
    if args.list:
        print(format_station_list(facts, args.lang), file=out)
        return 0
    return _plan(args, facts, out)


if __name__ == "__main__":
    raise SystemExit(main())
