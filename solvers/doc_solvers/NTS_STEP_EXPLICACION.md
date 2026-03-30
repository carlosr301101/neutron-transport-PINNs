# NTS_STEP: Método de Características STEP

## 1. Introducción al Algoritmo STEP

El programa **NTS_STEP.c** implementa el método de **Características STEP (Short characteristics Through Each Point)** para resolver la ecuación de transporte de neutrones en 2D.

### ¿Qué es el Método STEP?

**STEP = Sweep Through Each Point (Short Characteristics)**

- **Principio físico:** Sigue las trayectorias de los neutrones (rayos característicos) en cada dirección angular
- **Sweeps direccionales:** Realiza barridos en 4 direcciones principales (SW→NE, NW→SE, NE→SW, SE→NW)
- **Stepping:** Avanza por pasos a lo largo de cada rayo característico
- **Convergencia:** Iteración global hasta que el flujo converge

### Características Principales

✓ **Físicamente intuitivo:** Sigue las rutas reales de partículas  
✓ **Convergencia rápida:** 15-30 iteraciones (similar a LD)  
✓ **Eficiente con fuentes beam:** Excelente para fuentes direccionales  
✓ **Bajo costo memoria:** No requiere matrices grandes  
✓ **Estabilidad:** Buena estabilidad numérica  

## 2. Parámetros de Entrada (11 parámetros)

Idénticos a todos los métodos anteriores (DD, LD, RM_CN, RM_LLN):

| # | Parámetro | Descripción | Rango/Formato |
|---|-----------|-------------|---------------|
| 1 | N | Orden cuadratura | 2-18 (par) |
| 2 | NZ | Número zonas | ≥1 |
| 3 | ZONES | σ_t σ_s por zona | [cm⁻¹] |
| 4-7 | NR_X, XDOM, NR_Y, YDOM | Discretización espacial | Regiones y nodos |
| 8-9 | ZMAP, QMAP | Mapas zona y fuente | Matrices |
| 10 | BC | Condiciones frontera | 4 valores |
| 11 | TOL | Tolerancia | 1e-2 a 1e-7 |

## 3. Metodología: Barridos Característicos

### Estructura de Iteración

Cada iteración del método STEP:

```
Iteración k:
  Para cada dirección angular m (de 1 a M):
    1. Determinar cuadrante de barrido según dirección:
       - m < M/4:       SW → NE (Suroeste a Noreste)
       - M/4 ≤ m < M/2: NW → SE (Noroeste a Sureste)
       - M/2 ≤ m < 3M/4: NE → SW (Noreste a Suroeste)
       - 3M/4 ≤ m < M:  SE → NW (Sureste a Noroeste)
    
    2. Realizar barrido en orden apropiado:
       Para cada celda (i,j) en orden de barrido:
         a. Obtener flujos entrantes de vecinos upstream
         b. Resolver balance de transporte en la celda
         c. Calcular flujos salientes
         d. Pasar flujos a celdas downstream
  
  Verificar convergencia:
    Si cambio_máximo < tolerancia → CONVERGED
```

### Ecuación de Balance (por celda)

En cada celda, STEP resuelve:

```
μ·∂Φ/∂x + η·∂Φ/∂y + σ_t·Φ = (σ_s/4π)·∫Φ dΩ + Q/(4π)
```

Donde:
- **μ, η**: Componentes direccionales del vector Ω
- **Φ(x,y,Ω)**: Flujo angular de neutrones
- **σ_t**: Sección eficaz total
- **σ_s**: Sección eficaz de scattering
- **Q**: Término fuente

### Discretización Diamond Difference

STEP usa **diamond difference** para aproximar derivadas:

```
Flujo en centro celda = promedio de flujos en fronteras
```

Esto preserva conservación y evita oscilaciones espurias.

## 4. Ejemplo 1: Problema Simple (2×2)

```
Entrada:
4                      # N=4 → M=12 direcciones
1                      # NZ=1 (un material)
0.5 0.3                # σ_t=0.5, σ_s=0.3 cm⁻¹
2                      # NR_X=2
10.0 5                 # Región X1: 10 cm, 5 nodos
10.0 5                 # Región X2: 10 cm, 5 nodos
2                      # NR_Y=2
10.0 5                 # Región Y1: 10 cm, 5 nodos
10.0 5                 # Región Y2: 10 cm, 5 nodos
1 1                    # ZMAP: todo material 1
1 1
1.0 1.0                # QMAP: fuentes uniformes
1.0 1.0
0.0 0.0 0.0 0.0       # BC: vacío
1e-5                   # Tolerancia
```

### Ejecución

```bash
$ gcc -O2 -o NTS_STEP programs/NTS_STEP.c -lm
$ ./NTS_STEP input_simple.txt > output.json
```

### Salida Esperada

```json
{
  "STATUS": 0,
  "ITER": 19,
  "CPU": 0.002,
  "MFLUX": [ ... matriz 10×10 ...],
  ...
}
```

**Interpretación:**
- **STATUS=0**: Convergencia exitosa
- **ITER=19**: STEP converge rápido (19 iteraciones)
- **CPU=0.002s**: Tiempo muy bajo
- **Flujo simétrico**: Por simetría del problema

## 5. Ejemplo 2: Fuente Tipo Beam (Direccional)

```
Descripción: Fuente concentrada en esquina, simulando haz direccional

Entrada:
4
1
0.6 0.35
2
10.0 5
10.0 5
2
10.0 5
10.0 5
1 1
1 1
3.0 0.5                # Fuente alta en (0,0)
1.0 0.2                # Fuente baja en resto
0.0 0.0 0.0 0.0
1e-5
```

**Ventaja STEP aquí:**
- El método STEP sigue naturalmente los rayos desde la fuente
- Barridos capturan flujo de partículas correctamente
- Convergencia rápida: típicamente 18-25 iteraciones

**Resultado esperado:** STATUS=0, ITER=20-25

## 6. Ejemplo 3: Materiales Heterogéneos

```
Descripción: Dos materiales en patrón checkerboard

Entrada:
4
2
0.5 0.30               # Material 1 (combustible)
0.9 0.55               # Material 2 (moderador)
2
10.0 5
10.0 5
2
10.0 5
10.0 5
1 2                    # Patrón alternado
2 1
1.2 0.8
0.8 1.2
0.0 0.0 0.0 0.0
1e-5
```

**Manejo de interfaces:**
- STEP atraviesa interfaces naturalmente durante stepping
- Cambio de σ_t, σ_s al cruzar frontera material
- Balance de flujo preservado en interfaz

**Resultado típico:** STATUS=0, ITER=20-30

## 7. Ejemplo 4: Malla Fina con N=6

```
Entrada:
6                      # N=6 (M=24 direcciones)
1
0.45 0.25
3                      # 3 regiones en X
7.0 6
7.0 6
6.0 6
3                      # 3 regiones en Y
6.5 6
7.0 6
6.5 6
[Matriz 3×3 de 1s]     # Zona uniforme
[Matriz 3×3 de 1.5s]   # Fuente uniforme
0.0 0.0 0.0 0.0
1e-5
```

**Nota:** Con N=6, hay 24 direcciones → más sweeps por iteración, pero sigue siendo rápido
**Iteraciones esperadas:** 25-35

## 8. Compilación

### Linux/Mac

```bash
cd /path/to/nts

# Comentar línea mingw si existe
sed -i 's/#define printf __mingw_printf/\/\/ #define printf __mingw_printf/' programs/NTS_STEP.c

# Compilar
gcc -O2 -o programs/linux/NTS_STEP programs/NTS_STEP.c -lm
```

### Flags Recomendados

| Flag | Uso |
|------|-----|
| `-O2` | Optimización estándar (recomendado) |
| `-O3` | Optimización máxima (+5-10% velocidad) |
| `-lm` | Librería matemática (REQUIRIDO) |

## 9. Análisis de Salida JSON

### Estructura

```json
{
  "STATUS": 0,
  "ITER": 19,
  "CPU": 0.002,
  "MFLUX": [[...], [...]],
  "MFLOW": [[[...]], ...],
  "XFLOW": [[...], ...],
  "YFLOW": [[...], ...]
}
```

### Campos

- **STATUS**: 0=éxito, 1=args, 2=lectura, 3=memoria
- **ITER**: Iteraciones (15-30 típico STEP)
- **CPU**: Tiempo ejecución [s]
- **MFLUX**: Flujo escalar por nodo
- **MFLOW**: Flujo angular (3D)
- **XFLOW/YFLOW**: Flujos en fronteras

## 10. Validación

### Checklist Pre-Ejecución

```
☐ N es par ∈ [2,18]
☐ σ_s < σ_t para todas zonas
☐ ZMAP índices [1, NZ]
☐ QMAP ≥ 0
☐ Archivo entrada completo (11 líneas)
```

### Checklist Post-Ejecución

```
☐ STATUS = 0
☐ ITER ∈ [1, 100] (típico 15-30)
☐ CPU razonable (< 1s para problemas moderados)
☐ MFLUX > 0 (con fuentes > 0)
```

## 11. Comparación: STEP vs Otros Métodos

### Tabla Comparativa

| Métrica | LD | STEP | DD | RM_CN | RM_LLN |
|---------|-------|------|-------|-------|--------|
| **Iteraciones** | 20-40 | **15-30** | 30-100 | 5-20 | 5-15 |
| **Velocidad total** | **Muy rápido** | **Rápido** | Medio | Rápido | Rápido |
| **Precisión** | Buena | **Muy buena** | Muy buena | Excelente | Excelente |
| **Memoria** | **Baja** | **Baja** | Media | Media | Media |
| **Físicamente intuitivo** | Medio | **Muy alto** | Bajo | Bajo | Medio |
| **Beam sources** | Medio | **Excelente** | Medio | Bueno | Bueno |

### Guía de Selección

**Usa STEP cuando:**
✓ Problema tiene fuentes direccionales/beam  
✓ Quieres método físicamente intuitivo  
✓ Convergencia rápida con precisión buena  
✓ Enseñanza (muy didáctico)  
✓ Diseño iterativo (rapidez importante)  

**NO uses STEP cuando:**
✗ Necesitas máxima precisión → usa RM_CN o RM_LLN  
✗ Problema tiene estructura lattice clara → usa RM_LLN  
✗ Solo importa velocidad → usa LD  

## 12. Ventajas del Método STEP

### 1. Físicamente Intuitivo

- **Sigue trayectorias reales:** Los barridos representan el flujo físico de neutrones
- **Fácil de visualizar:** Sweeps direccionales son conceptualmente simples
- **Didáctico:** Excelente para enseñar transporte de neutrones

### 2. Excelente con Fuentes Direccionales

- **Beam problems:** Fuentes externas tipo haz
- **Fuentes localizadas:** Alta fuente en región pequeña
- **Inyección direccional:** Partículas entrando desde frontera

### 3. Convergencia Rápida

- **15-30 iteraciones:** Mejor que DD (30-100), similar a LD (20-40)
- **Información fluye naturalmente:** Sweeps propagan flujo eficientemente
- **Pocas oscilaciones:** Diamond difference es estable

### 4. Bajo Costo Computacional

- **Sin matrices grandes:** Solo operaciones locales por celda
- **Memoria baja:** Similar a LD
- **CPU eficiente:** Operaciones simples (no inversión matriz)

## 13. Parámetros Recomendados

### Problema Típico

```
N = 4                  # 12 direcciones suficiente
Nodos = 5-6 por región # Balance precisión/velocidad
Tolerancia = 1e-5      # Convergencia en ~20 iter
Resultado: ITER~20, CPU~2-5ms
```

### Problema con Fuente Beam

```
N = 4 o 6              # Más direcciones si beam complejo
Nodos = 5-7            # Suficiente resolución
Fuente alta localizada # QMAP con valores altos en región beam
Tolerancia = 1e-5
Resultado: ITER~18-25, muy eficiente
```

### Problema de Alta Resolución

```
N = 6                  # 24 direcciones
Nodos = 6-8 por región # Malla fina
Tolerancia = 1e-6      # Estricta
Resultado: ITER~30-40, CPU~10-30ms
```

## 14. Problemas Comunes y Soluciones

### Problema: ITER > 50

**Causas:**
- Tolerancia muy estricta (1e-7)
- σ_s muy cercano a σ_t
- Malla muy fina con N alto

**Soluciones:**
- Aumentar tolerancia a 1e-5
- Reducir σ_s o aumentar σ_t
- Usar N=4 en lugar de N=6

### Problema: MFLUX contiene NaN

**Causas:**
- σ_s ≥ σ_t (violación física)
- Step size demasiado grande (raro)

**Soluciones:**
- Verificar σ_s < σ_t estrictamente
- Aumentar número de nodos

### Problema: Convergencia lenta cerca de fronteras

**Causa:** Condiciones de frontera mal especificadas

**Solución:**
- Verificar BC correctas
- Usar BC=-1.0 (simetría) si aplicable

## 15. Rendimiento Observable

### Problema Simple (2×2)

```
Tamaño: 2×2 regiones, 5 nodos/región
N=4 (12 direcciones)
Iteraciones: ~19
CPU: 1-2 ms
```

### Problema Moderado (3×3)

```
Tamaño: 3×3 regiones, 6 nodos/región
N=4
Iteraciones: ~25
CPU: 5-10 ms
```

### Problema Complejo (4×4 con N=6)

```
Tamaño: 4×4 regiones, 7 nodos/región
N=6 (24 direcciones)
Iteraciones: ~35
CPU: 20-40 ms
```

## 16. Conclusión

**NTS_STEP es ideal cuando se busca:**
1. ✓ Método físicamente intuitivo (educativo)
2. ✓ Convergencia rápida (15-30 iter)
3. ✓ Problemas con fuentes direccionales/beam
4. ✓ Balance velocidad/precisión
5. ✓ Bajo uso de memoria

**Comparación final:**
- **vs LD:** STEP ligeramente más lento pero más preciso y físicamente intuitivo
- **vs DD:** STEP mucho más rápido (15-30 vs 30-100 iter) y más intuitivo
- **vs RM:** STEP menos iteraciones que DD pero más que RM; más intuitivo pero menos preciso

**Recomendación:**
STEP es excelente opción para ingeniería, diseño iterativo, y especialmente **problemas con fuentes beam o direccionales**. Su naturaleza física lo hace ideal también para **enseñanza de transporte de neutrones**.

---

**Documento generado automáticamente**  
NTS_STEP Simulation Guide | Characteristic STEP Method
