import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src import cli
from src.graph import build_graph
from src.knowledge_base import load_knowledge_base
from src.search import find_route

ROOT = Path(__file__).resolve().parent.parent
NETWORK = ROOT / "data" / "network.json"


def run(*argv):
    out = io.StringIO()
    code = cli.main(list(argv), out=out)
    return code, out.getvalue()


@pytest.fixture(scope="module")
def route():
    graph = build_graph(load_knowledge_base(NETWORK))
    return find_route(graph, "Portal Américas", "Calle 100")


def test_resolve_station_ignores_case_and_accents():
    names = ["Héroes", "Calle 26", "Normandía"]
    assert cli.resolve_station("heroes", names) == "Héroes"
    assert cli.resolve_station("CALLE 26", names) == "Calle 26"
    assert cli.resolve_station("  normandia ", names) == "Normandía"


def test_resolve_station_unknown_lists_suggestions():
    with pytest.raises(ValueError) as exc:
        cli.resolve_station("Calle 2", ["Calle 26", "Calle 72", "Héroes"])
    assert "Unknown station: 'Calle 2'." in str(exc.value)
    assert "Did you mean: " in str(exc.value) and "Calle 26" in str(exc.value)


def test_resolve_station_unknown_without_suggestions():
    with pytest.raises(ValueError) as exc:
        cli.resolve_station("zzzzzz", ["Héroes"])
    assert str(exc.value) == "Unknown station: 'zzzzzz'."


def test_format_route_groups_legs_and_totals(route):
    graph = build_graph(load_knowledge_base(NETWORK))
    text = cli.format_route(route, graph, 5.0)
    assert "Portal Américas -> Calle 100" in text
    assert "Ride Americas: Portal Américas -> Ricaurte (4 stops, 17 min)" in text
    assert text.count("Transfer at") == 3
    assert "(1 stop, 5 min)" in text
    assert "Transfer at Ricaurte: Americas -> NQS" in text
    assert "Ride time: 38 min | Transfers: 3 | Total cost: 53.0 (penalty 5.0 min per transfer)" in text


def test_main_route(route):
    code, text = run("Portal Américas", "Calle 100")
    assert code == 0
    assert "Ride time: 38 min | Transfers: 3 | Total cost: 53.0" in text


def test_main_is_accent_insensitive():
    code, text = run("portal americas", "CALLE 100")
    assert code == 0 and "Transfers: 3" in text


def test_main_same_station():
    code, text = run("Héroes", "heroes")
    assert code == 0
    assert "You are already at Héroes." in text


def test_main_unknown_station():
    code, text = run("Calle 100", "Calle 2")
    assert code == 1
    assert "Unknown station: 'Calle 2'. Did you mean: " in text


def test_main_list_shows_all_stations_and_transfers():
    code, text = run("--list")
    names = build_graph(load_knowledge_base(NETWORK)).edges
    assert code == 0
    assert len(names) == 20 and all(n in text for n in names)
    assert "Ricaurte (transfer)" in text


def test_main_penalty_changes_cost():
    code, text = run("Portal Américas", "Calle 100", "--penalty", "0")
    assert code == 0
    assert "penalty 0.0 min per transfer" in text
    assert "Total cost: 53.0" not in text


def test_main_negative_penalty_rejected():
    with pytest.raises(SystemExit) as exc:
        run("A", "B", "--penalty", "-1")
    assert exc.value.code == 2


def test_main_prompts_when_stations_missing(monkeypatch):
    answers = iter(["Corferias", "calle 75"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    code, text = run()
    assert code == 0 and "Corferias -> Calle 75" in text


def test_module_runs_from_another_directory(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", "Corferias", "Calle 75"],
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Transfers: 1" in result.stdout
