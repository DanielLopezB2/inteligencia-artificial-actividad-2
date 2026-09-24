# Intelligent Mass Transit Route Planner

## Project Overview

This project implements a knowledge-based intelligent system that finds the best route between two stations of TransMilenio (Bogotá), using a reduced real network of 4 lines and 20 stations.

The system combines:

- Knowledge representation.
- Logical rules.
- Graph-based modeling.
- Heuristic search.
- Automated testing.

The search algorithm is A\*, which uses the accumulated route cost and a heuristic estimation to select the most promising station.

## Academic Purpose

The project demonstrates the application of artificial intelligence concepts related to:

1. Logic and knowledge representation.
2. Rule-based systems.
3. Heuristic search techniques.
4. Intelligent decision-making.

## Quick Start

```bash
python -m src.cli "Portal Américas" "Calle 100"
```

The output is in Spanish by default; use `--lang en` for English. Full setup, options and examples are in [docs/INSTRUCCIONES.md](docs/INSTRUCCIONES.md) (Spanish). Test evidence is in [docs/informe-pruebas.pdf](docs/informe-pruebas.pdf).

## System Behavior

The user provides an origin station and a destination station. The system then:

1. Validates the input stations (case and accent insensitive, with suggestions).
2. Loads the transport knowledge base.
3. Applies logical rules (Horn clauses, forward chaining) to derive adjacency and transfer stations.
4. Builds the transport graph.
5. Searches for the best route using A\*.
6. Displays the selected route and its total cost.

## Route Selection Criteria

The primary criterion is the lowest total cost: travel minutes plus a penalty of 5 minutes (configurable with `--penalty`) each time the route changes line.

The heuristic uses the straight-line (haversine) distance to the destination divided by the maximum speed observed in the network, so it never overestimates the real cost.

If two routes have the same cost, the system prefers the route with fewer transfers.

## Project Structure

```text
actividad-2/
├── README.md
├── requirements.txt
├── data/
│   └── network.json          # stations, lines and segments (approximate estimates)
├── docs/
│   ├── INSTRUCCIONES.md      # how to run (Spanish)
│   ├── informe-pruebas.md    # test report (Spanish)
│   └── informe-pruebas.pdf
├── src/
│   ├── knowledge_base.py     # Horn-clause engine, rules and data loader
│   ├── graph.py              # graph built from knowledge-base facts
│   ├── search.py             # A* with transfer penalty
│   └── cli.py                # command-line interface (es/en)
└── tests/
```

## Limitations

Times and coordinates in `data/network.json` are approximate estimates for academic use, and adjacent stations may skip real intermediate stops. Check them against the official TransMilenio map before using the results for anything else.
