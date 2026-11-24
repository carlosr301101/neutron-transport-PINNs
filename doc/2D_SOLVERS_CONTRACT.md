# Contrato de entrada/salida de los solvers 2D

Este documento es la referencia canónica del formato que comparten los cinco
solvers 2D en C:

```text
NTS_DD      Domain Decomposition
NTS_LD      Linear Discontinuous
NTS_STEP    Step / characteristic sweeps
NTS_RM_CN   Response Matrix + Crank-Nicolson
NTS_RM_LLN  Response Matrix + Linear Lattice Nodalization
```

El código C es la fuente de verdad. Cualquier capa de Python (modelos
Pydantic, `InputBuilder`, wizard, CLI o TUI) debe generar exactamente este
formato. Si la documentación y el C discrepan, gana el C.

Implementación de referencia: `solvers/runners/NTS_DD.c`
(`input_by_txt` y `json_output`).

## Entrada: `input.txt`

Archivo de texto plano. Los valores se leen en orden con `fscanf`, por lo que
los saltos de línea son separadores, no estructura. La estructura lógica es:

```text
N
NZ
sigma_t[1] sigma_s[1]
...
sigma_t[NZ] sigma_s[NZ]
NR_X
length[1] nodes[1]
...
length[NR_X] nodes[NR_X]
NR_Y
length[1] nodes[1]
...
length[NR_Y] nodes[NR_Y]
ZMAP[1][1] ... ZMAP[1][NR_X]
...
ZMAP[NR_Y][1] ... ZMAP[NR_Y][NR_X]
QMAP[1][1] ... QMAP[1][NR_X]
...
QMAP[NR_Y][1] ... QMAP[NR_Y][NR_X]
BC_left BC_bottom BC_right BC_top
TOL
```

Número total de líneas:

```text
lineas = 6 + NZ + NR_X + 3 * NR_Y
```

Para `NZ = NR_X = NR_Y = 1` son 11 líneas, que es el caso de los golden tests.

### Restricciones por campo

| Campo | Tipo | Restricción | Validado en |
|---|---|---|---|
| `N` | entero | par, `2 <= N <= 18` | C y Python |
| `NZ` | entero | `>= 1` | C y Python |
| `sigma_t` | real | `> 0` | Python |
| `sigma_s` | real | `>= 0`, `< sigma_t` | Python |
| `NR_X` | entero | `>= 1` | C y Python |
| `NR_Y` | entero | `>= 1` | C y Python |
| `length` | real | `> 0` | Python |
| `nodes` | entero | `>= 3` | Python (el C acepta `>= 1`) |
| `ZMAP` | entero | `1 <= z <= NZ` | Python |
| `QMAP` | real | `>= 0` | Python |
| `BC` | real | `-1.0`, `0.0` o `> 0` | C y Python |
| `TOL` | real | `0 < TOL < 1` | C |

`nodes` cuenta **celdas**, no puntos. El paso espacial dentro de una región es:

```text
h_x = length / nodes
h_y = length / nodes
```

El flujo escalar se reporta en el centro de cada celda.

### Orden y semántica de `BC`

```text
BC[0] = LEFT    x = 0
BC[1] = BOTTOM  y = 0
BC[2] = RIGHT   x = Lx
BC[3] = TOP     y = Ly
```

Valores aceptados:

| Valor | Semántica | Significado físico |
|---|---|---|
| `-1.0` | reflectivo | simetría especular; no entra flujo externo |
| `0.0` | vacío | sin flujo entrante |
| `> 0.0` | flujo entrante | flujo constante impuesto en esa cara |

Cualquier otro valor negativo (`-0.5`, `-2.0`, ...) es inválido: el C aborta
con `STATUS = 2`.

Mapa a las variables del C:

```text
XFLOW[i = 0]        <- BC[0]  (LEFT)
XFLOW[i = ntc_x]    <- BC[2]  (RIGHT)
YFLOW[j = 0]        <- BC[1]  (BOTTOM)
YFLOW[j = ntc_y]    <- BC[3]  (TOP)
```

> Cambio de semántica respecto a versiones anteriores: `1.0` ya **no**
> significa reflectivo; significa flujo entrante de valor 1.0. Para
> reflectivo se usa `-1.0`.

## Salida: JSON

El programa escribe el JSON en `stdout`. El runner de Python lo redirige al
archivo de resultados.

### Éxito

```json
{
  "STATUS": 0,
  "ITER": 42,
  "CPU": 1.234e-02,
  "MFLUX": [[...], ...],
  "MFLOW": [[...], ...],
  "XFLOW": [[...], ...],
  "YFLOW": [[...], ...]
}
```

| Campo | Forma | Descripción |
|---|---|---|
| `STATUS` | entero | código de estado |
| `ITER` | entero | iteraciones realizadas |
| `CPU` | real | tiempo de CPU en segundos |
| `MFLUX` | `ntc_y x ntc_x` | flujo escalar por celda |
| `MFLOW` | `M x ntc_y x ntc_x` | flujo angular por celda y ordenada |
| `XFLOW` | `M x ntc_y x (ntc_x + 1)` | flujo angular en caras X |
| `YFLOW` | `M x (ntc_y + 1) x ntc_x` | flujo angular en caras Y |

donde:

```text
ntc_x = sum(nodes de XDOM)
ntc_y = sum(nodes de YDOM)
M     = N * (N + 2) / 2
```

`MFLUX` se imprime con 10 dígitos y notación científica (`%.10Le`), con una
fila por índice `j` y una columna por índice `i`. La primera fila corresponde a
`y = 0`.

### Error

Cuando `STATUS != 0` el JSON contiene **solo** `STATUS`:

```json
{
  "STATUS": 2
}
```

| `STATUS` | Significado |
|---|---|
| `0` | éxito |
| `1` | número de argumentos incorrecto |
| `2` | error de lectura o de validación del input |
| `3` | fallo de reserva de memoria |
| `6` | flujo no finito (NaN o infinito) |

Cualquier consumidor (CLI, TUI, tests) debe tolerar la ausencia de `ITER`,
`CPU` y `MFLUX` cuando `STATUS != 0`.

## Solvers

Los cinco binarios comparten el mismo `input.txt` y el mismo esquema de salida.
Solo cambia el esquema de barrido.

| Solver | Método | Perfil | Cuándo usarlo |
|---|---|---|---|
| `NTS_DD` | Diamond Difference | equilibrio entre precisión y coste | caso general, referencia |
| `NTS_LD` | Linear Discontinuous | rápido, buena difusión | mallas gruesas, estimaciones rápidas |
| `NTS_STEP` | Step / sweeps característicos | estable con fuentes localizadas | haces, fuentes puntuales, problemas direccionales |
| `NTS_RM_CN` | Response Matrix + Crank-Nicolson | pocas iteraciones, alta precisión | mallas refinadas |
| `NTS_RM_LLN` | Response Matrix + Linear Lattice Nodalization | el más rápido por iteración en retículos | ensambles de reactor, problemas tipo lattice |

Todos aceptan exactamente un argumento posicional: la ruta del `input.txt`.

```bash
./NTS_DD input.txt > output.json
```

## Diferencias conocidas con el C

El C tolera `nodes >= 1` y `TOL` en `(0, 1)`. La capa de Python impone
restricciones más estrictas antes de escribir el archivo:

```text
nodes >= 3
1e-7 <= TOL <= 1e-2
```

Esto evita mallas degeneradas y tolerancias que nunca convergen en la práctica.

## Ejemplos de referencia

Los cinco archivos `solvers/doc_solvers/*_EXAMPLE_INPUT.json` describen el
mismo formato. Todos deben ser JSON válido y usar el orden
`LEFT BOTTOM RIGHT TOP`.

## Compilación local (Linux)

Los binarios de `solvers/runners/` se reconstruyen desde las fuentes con:

```bash
gcc -O2 -D__mingw_printf=printf \
    -o solvers/runners/NTS_DD solvers/runners/NTS_DD.c -lm
```

y el mismo comando para `NTS_LD`, `NTS_STEP`, `NTS_RM_CN` y `NTS_RM_LLN`.
`-D__mingw_printf=printf` neutraliza el alias que los fuentes usan para MinGW;
en Windows/MinGW se compila sin ese `-D` y con `-static`.

Los binarios y las fuentes deben mantenerse sincronizados: un binario viejo
puede rechazar un `input.txt` que la fuente actual acepta. El test
`tests/test_2d_solvers.py` ejecuta los cinco binarios y valida `STATUS`,
dimensiones, simetría y el orden de `BC`.

```bash
uv run python -m cli.run_tests -p "test_2d_solvers.py"
```
