# Intelligent Mass Transit Route Planner

## Project Overview

This project implements a knowledge-based intelligent system capable of finding the best route between two stations in a local mass transit system.

The system combines:

- Knowledge representation.
- Logical rules.
- Graph-based modeling.
- Heuristic search.
- Automated testing.

The main search algorithm will be A\*, which will use the accumulated route cost and a heuristic estimation to select the most promising station.

## Academic Purpose

The project demonstrates the application of artificial intelligence concepts related to:

1. Logic and knowledge representation.
2. Rule-based systems.
3. Heuristic search techniques.
4. Intelligent decision-making.

## Planned System Behavior

The user will provide:

- An origin station.
- A destination station.

The system will then:

1. Validate the input stations.
2. Load the transport knowledge base.
3. Apply logical rules.
4. Build the transport graph.
5. Search for the best route using A\*.
6. Display the selected route and its total cost.

## Route Selection Criteria

The primary criterion will be the lowest estimated travel cost.

The route cost may consider:

- Travel time.
- Number of transfers.
- Distance between stations.
- Availability of transport connections.

If two routes have the same cost, the system will prefer the route with fewer transfers.

## Planned Project Structure

```text
actividad-2/
├── README.md
├── .gitignore
├── data/
├── docs/
├── src/
└── tests/
```
