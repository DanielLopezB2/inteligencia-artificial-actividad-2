# Instrucciones de ejecución

Planificador de rutas de TransMilenio (Bogotá) en Python puro: base de conocimiento con reglas lógicas + búsqueda A*.

## 1. Requisitos

- Python 3.10 o superior (desarrollado con Python 3.14).
- Git.
- No hay dependencias para ejecutar el programa. `pytest` solo se necesita para las pruebas.

## 2. Instalación

```bash
git clone https://github.com/DanielLopezB2/inteligencia-artificial-actividad-2
cd inteligencia-artificial-actividad-2

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt  # solo necesario para las pruebas
```

## 3. Ejecución

Todos los comandos se ejecutan desde la raíz del repositorio.

```bash
python -m src.cli "Portal Américas" "Calle 100"
```

| Uso | Comando |
|---|---|
| Ruta entre dos estaciones | `python -m src.cli "Portal Américas" "Calle 100"` |
| Modo interactivo (pregunta origen y destino) | `python -m src.cli` |
| Listar estaciones por línea | `python -m src.cli --list` |
| Cambiar la penalización por transbordo (minutos, por defecto 5) | `python -m src.cli "Portal Américas" "Calle 100" --penalty 0` |
| Usar otro archivo de red | `python -m src.cli --data ruta/otra_red.json "A" "B"` |

Los nombres no distinguen mayúsculas ni tildes: `heroes` equivale a `Héroes`. Si una estación no existe, el programa sugiere nombres parecidos.

## 4. Cómo leer la salida

```text
Route: Portal Américas -> Calle 100
Ride Americas: Portal Américas -> Ricaurte (4 stops, 17 min)
Transfer at Ricaurte: Americas -> NQS
Ride NQS: Ricaurte -> Centro Memoria (1 stop, 5 min)
...
Ride time: 38 min | Transfers: 3 | Total cost: 53.0 (penalty 5.0 min per transfer)
```

- `Ride <línea>`: un tramo continuo en una misma línea (estación inicial -> final, paradas y minutos).
- `Transfer at <estación>`: cambio de línea.
- Última línea: tiempo de viaje, número de transbordos y costo total (`minutos + penalización x transbordos`).

Códigos de salida: `0` éxito o misma estación; `1` estación desconocida o sin ruta; `2` argumentos inválidos (por ejemplo `--penalty` negativo).

## 5. Pruebas

```bash
python -m pytest -q
```

Resultado esperado: `50 passed`.

## 6. Estructura del proyecto

```text
actividad-2/
├── README.md
├── requirements.txt
├── data/
│   └── network.json         # estaciones, líneas y tramos (4 líneas, 20 estaciones)
├── docs/
│   ├── INSTRUCCIONES.md
│   ├── informe-pruebas.md
│   └── informe-pruebas.pdf
├── src/
│   ├── knowledge_base.py    # motor de reglas Horn + carga y validación de datos
│   ├── graph.py             # grafo construido solo a partir de hechos
│   ├── search.py            # A* con penalización por transbordo
│   └── cli.py               # interfaz de línea de comandos
└── tests/
    ├── test_knowledge_base.py
    ├── test_graph.py
    ├── test_search.py
    └── test_cli.py
```

## 7. Cómo funciona

1. **Base de conocimiento.** `network.json` se carga como hechos (`station`, `on_line`, `segment`, `location`). Un motor de encadenamiento hacia adelante aplica reglas Horn hasta el punto fijo y deriva `adjacent` (tramos en ambos sentidos) y `transfer_station` (estación con dos líneas distintas).
2. **Grafo.** `build_graph` convierte los hechos en aristas `(destino, línea, minutos)` y coordenadas.
3. **A\*.** Busca sobre estados `(estación, línea)`. El costo es `minutos + penalización por transbordo`. A igual costo, gana la ruta con menos transbordos.
4. **Heurística.** Distancia haversine al destino dividida por la velocidad máxima observada en la red. Es admisible y consistente, y no incluye la penalización, por lo que siempre subestima.
