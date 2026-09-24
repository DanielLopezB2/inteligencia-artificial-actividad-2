# Informe de pruebas

**Proyecto:** Planificador inteligente de rutas de TransMilenio (Bogotá)
**Curso:** Inteligencia Artificial, Universidad Iberoamericana
**Autor:** DanielLopezB2 (proyecto individual)
**Repositorio:** https://github.com/DanielLopezB2/inteligencia-artificial-actividad-2

## 1. Objetivo

Verificar que el planificador cumple lo que promete: cargar una base de conocimiento validada, inferir hechos con reglas lógicas, construir el grafo y encontrar la ruta de menor costo con A*, con desempate por menos transbordos. Todas las salidas de este informe fueron generadas ejecutando el código real.

## 2. Entorno

| Elemento | Valor |
|---|---|
| Sistema operativo | macOS (Darwin) |
| Python | 3.14.7 |
| pytest | 9.1.1 |
| Dependencias del programa | ninguna (solo biblioteca estándar) |

## 3. Estrategia

- **TDD:** cada feature se desarrolló escribiendo primero las pruebas, viéndolas fallar y luego implementando. La prueba en rojo no queda en el historial de Git, porque cada commit agrupa pruebas y código ya en verde.
- **Una rama por feature:** `feat/knowledge-base`, `feat/graph-builder`, `feat/astar-search`, `feat/cli`, `feat/cli-es`.
- **Integración con `merge --no-ff`**, para conservar el historial de cada feature.
- **Compuerta antes de avanzar:** pruebas automáticas en verde y una prueba funcional del CLI o del módulo antes de empezar el siguiente feature.

## 4. Resultados de `python -m pytest -v`

**Total: 63 pruebas, 63 aprobadas, 0 fallidas (0.31 s).**

| Módulo | Pruebas | Qué cubre |
|---|---|---|
| `tests/test_knowledge_base.py` | 20 | Motor de inferencia (reglas, joins, `!=`, punto fijo, no muta la entrada), `query`, adyacencia simétrica, estaciones de transbordo, integridad de `network.json`, validación de datos (estación o línea desconocida, minutos no positivos). |
| `tests/test_graph.py` | 8 | Estaciones presentes, aristas simétricas con los mismos minutos, vecinos de Ricaurte, transbordos, coordenadas, conectividad, orden determinista, estación aislada. |
| `tests/test_search.py` | 9 | Ruta sin transbordos, ruta con varios transbordos consistente, optimalidad en todos los pares, simetría del costo, desempate por menos transbordos, efecto de la penalización, destino inalcanzable, estación desconocida, origen igual a destino. |
| `tests/test_cli.py` | 26 | Normalización de tildes y mayúsculas, sugerencias, formato de tramos y totales, ruta, misma estación, estación desconocida, `--list`, `--penalty` (y rechazo de negativos), modo interactivo, ejecución desde otro directorio; `--lang` (español por defecto, `--lang en` reproduce la salida en inglés, valor inválido rechazado), catálogos es/en con los mismos identificadores de mensaje, pluralización de paradas, mensajes de misma estación, estación desconocida, sin ruta, marcador de `--list` y prompts interactivos en ambos idiomas. |
| **Total** | **63** | |

## 5. Pruebas funcionales (CLI real)

Cada caso se ejecutó desde la raíz del repositorio con la salida en español (idioma por defecto).

### F1. Ruta en una sola línea

```text
$ python -m src.cli "Portal Américas" "Ricaurte"
Ruta: Portal Américas -> Ricaurte
Tramo Americas: Portal Américas -> Ricaurte (4 paradas, 17 min)
Tiempo de viaje: 17 min | Transbordos: 0 | Costo total: 17.0 (penalización de 5.0 min por transbordo)
```

Veredicto: correcto. Sin transbordos, costo igual al tiempo de viaje.

### F2. Ruta con varios transbordos

```text
$ python -m src.cli "Portal Américas" "Calle 100"
Ruta: Portal Américas -> Calle 100
Tramo Americas: Portal Américas -> Ricaurte (4 paradas, 17 min)
Transbordo en Ricaurte: Americas -> NQS
Tramo NQS: Ricaurte -> Centro Memoria (1 parada, 5 min)
Transbordo en Centro Memoria: NQS -> Calle 26
Tramo Calle 26: Centro Memoria -> Calle 26 (1 parada, 2 min)
Transbordo en Calle 26: Calle 26 -> Caracas
Tramo Caracas: Calle 26 -> Calle 100 (6 paradas, 14 min)
Tiempo de viaje: 38 min | Transbordos: 3 | Costo total: 53.0 (penalización de 5.0 min por transbordo)
```

Veredicto: correcto. 38 min + 3 x 5 min = 53.0.

### F3. Origen igual a destino

```text
$ python -m src.cli "Héroes" "Héroes"
Ya estás en Héroes.
```

Veredicto: correcto. Código de salida 0, sin buscar ruta.

### F4. Entrada sin tildes y en distinta capitalización

```text
$ python -m src.cli "heroes" "PORTAL AMERICAS"
Ruta: Héroes -> Portal Américas
Tramo Caracas: Héroes -> Calle 26 (5 paradas, 12 min)
Transbordo en Calle 26: Caracas -> Calle 26
Tramo Calle 26: Calle 26 -> Centro Memoria (1 parada, 2 min)
Transbordo en Centro Memoria: Calle 26 -> NQS
Tramo NQS: Centro Memoria -> Ricaurte (1 parada, 5 min)
Transbordo en Ricaurte: NQS -> Americas
Tramo Americas: Ricaurte -> Portal Américas (4 paradas, 17 min)
Tiempo de viaje: 36 min | Transbordos: 3 | Costo total: 51.0 (penalización de 5.0 min por transbordo)
```

Veredicto: correcto. Los nombres se resuelven a la forma oficial (`Héroes`, `Portal Américas`).

### F5. Estación desconocida con sugerencia

```text
$ python -m src.cli "Calle 1000" "Ricaurte"
Estación desconocida: 'Calle 1000'. ¿Quisiste decir: Calle 100, Calle 75, Calle 72?
```

Veredicto: correcto. Código de salida 1 y sugerencias útiles.

### F6. `--penalty 0` frente a la penalización por defecto

```text
$ python -m src.cli "Portal Américas" "Calle 100" --penalty 0
Ruta: Portal Américas -> Calle 100
Tramo Americas: Portal Américas -> Ricaurte (4 paradas, 17 min)
Transbordo en Ricaurte: Americas -> NQS
Tramo NQS: Ricaurte -> Centro Memoria (1 parada, 5 min)
Transbordo en Centro Memoria: NQS -> Calle 26
Tramo Calle 26: Centro Memoria -> Calle 26 (1 parada, 2 min)
Transbordo en Calle 26: Calle 26 -> Caracas
Tramo Caracas: Calle 26 -> Calle 100 (6 paradas, 14 min)
Tiempo de viaje: 38 min | Transbordos: 3 | Costo total: 38.0 (penalización de 0.0 min por transbordo)
```

| Penalización | Costo total | Ruta |
|---|---|---|
| 5 (por defecto, F2) | 53.0 | 3 transbordos |
| 0 | 38.0 | 3 transbordos |

Veredicto: correcto. El costo cambia (53.0 -> 38.0). La ruta es la misma porque en esta red reducida el trayecto óptimo no cambia con la penalización; se comprobó en los 380 pares (0 rutas distintas entre penalización 0 y 5).

### F7. Modo interactivo (entrada por stdin)

```text
$ printf 'Portal Américas\nCalle 100\n' | python -m src.cli
Estación de origen: Estación de destino: Ruta: Portal Américas -> Calle 100
Tramo Americas: Portal Américas -> Ricaurte (4 paradas, 17 min)
Transbordo en Ricaurte: Americas -> NQS
Tramo NQS: Ricaurte -> Centro Memoria (1 parada, 5 min)
Transbordo en Centro Memoria: NQS -> Calle 26
Tramo Calle 26: Centro Memoria -> Calle 26 (1 parada, 2 min)
Transbordo en Calle 26: Calle 26 -> Caracas
Tramo Caracas: Calle 26 -> Calle 100 (6 paradas, 14 min)
Tiempo de viaje: 38 min | Transbordos: 3 | Costo total: 53.0 (penalización de 5.0 min por transbordo)
```

Veredicto: correcto. Los prompts no llevan salto de línea porque stdin no es una terminal.

### F8. Penalización negativa

```text
$ python -m src.cli "Ricaurte" "Calle 100" --penalty -1
usage: python -m src.cli [-h] [--list] [--penalty MINUTES] [--lang {en,es}]
                         [--data DATA]
                         [origin] [destination]
python -m src.cli: error: argument --penalty: must be >= 0
```

Veredicto: correcto. Rechazado con código de salida 2. El mensaje de uso ahora incluye la opción `--lang`.

### F9. Salida en inglés con `--lang en`

```text
$ python -m src.cli "Portal Américas" "Calle 100" --lang en
Route: Portal Américas -> Calle 100
Ride Americas: Portal Américas -> Ricaurte (4 stops, 17 min)
Transfer at Ricaurte: Americas -> NQS
Ride NQS: Ricaurte -> Centro Memoria (1 stop, 5 min)
Transfer at Centro Memoria: NQS -> Calle 26
Ride Calle 26: Centro Memoria -> Calle 26 (1 stop, 2 min)
Transfer at Calle 26: Calle 26 -> Caracas
Ride Caracas: Calle 26 -> Calle 100 (6 stops, 14 min)
Ride time: 38 min | Transfers: 3 | Total cost: 53.0 (penalty 5.0 min per transfer)
```

Veredicto: correcto. Misma ruta y mismos totales que F2. La salida en inglés es idéntica, byte a byte, a la de la versión anterior al soporte bilingüe (lo verifica `test_lang_en_reproduces_english_output`).

### Resumen

| Caso | Escenario | Resultado |
|---|---|---|
| F1 | Una línea | OK |
| F2 | Varios transbordos | OK |
| F3 | Misma estación | OK |
| F4 | Tildes y mayúsculas | OK |
| F5 | Estación desconocida | OK |
| F6 | `--penalty 0` vs defecto | OK |
| F7 | Modo interactivo | OK |
| F8 | Penalización negativa | OK |
| F9 | `--lang en` | OK |

## 6. Verificación de optimalidad

Se comparó el costo de `find_route` (A*) con un Dijkstra independiente sobre estados `(estación, línea)`, sin heurística, para todos los pares ordenados de estaciones (20 x 19).

```text
pares comparados: 380
discrepancias:    0
```

Veredicto: A* devuelve el costo óptimo en los 380 pares. La misma comprobación está automatizada en `test_optimal_cost_for_all_pairs`.

## 7. Trazabilidad Git

```text
$ git log --graph --oneline --all
* 397053f feat(cli): add --lang option with Spanish default
*   54823ae merge: docs/test-report into main
|\
| * c60d3e0 docs: add test report with real evidence (md and pdf)
| * a8dc8e0 docs: add execution instructions in Spanish
|/
*   8affc1f merge: feat/cli into main
|\
| * 002120a feat(cli): add command-line route planner
|/
*   f4d74c2 merge: feat/astar-search into main
|\
| * a20f57b feat(search): add A* route search with transfer penalty
|/
*   5a3f307 merge: feat/graph-builder into main
|\
| * d4b70a2 feat(graph): build transport graph from knowledge-base facts
| * e2abd99 feat(kb): expose station coordinates as location facts
|/
* b13f5c8 chore: ignore .atl tooling directory
*   3cbfd19 merge: feat/knowledge-base into main
|\
| * e769c58 refactor(kb): split load_knowledge_base into validation helpers
| * 8fab9b8 feat(kb): add logic inference engine and TransMilenio knowledge base
|/
* 97e4130 docs: add project overview and setup guide
* 0a53cb5 chore: initialize route planning project
```

La salida se capturó antes de integrar la rama `feat/cli-es` y esta actualización de la documentación, por lo que no incluye sus merges.

Ramas de feature integradas en `main` con `--no-ff`: `feat/knowledge-base`, `feat/graph-builder`, `feat/astar-search`, `feat/cli`. La rama `feat/cli-es` (opción `--lang`, español por defecto) aún no está integrada en `main` al momento de escribir este informe. La documentación anterior vivió en `docs/test-report`.

## 8. Limitaciones

- **Datos aproximados.** Tiempos y coordenadas de `data/network.json` son estimaciones para uso académico, no datos oficiales.
- **Paradas intermedias omitidas.** Estaciones adyacentes en el archivo pueden saltarse estaciones reales; el tiempo cubre ese tramo. Por eso el conteo de paradas del CLI no coincide con el real.
- **Red reducida.** Solo 4 líneas (Caracas, Calle 26, NQS, Américas) y 20 estaciones. No incluye rutas zonales, alimentadoras ni otras troncales.
- **Sin validación oficial.** Antes de usar los resultados fuera del curso, deben contrastarse con el mapa oficial de TransMilenio.
- **Modelo de costo simple.** Penalización fija por transbordo; no considera horarios, frecuencias, esperas ni tarifas.
- **Un solo autor.** El proyecto fue desarrollado por una persona, sin revisión de código por terceros.
