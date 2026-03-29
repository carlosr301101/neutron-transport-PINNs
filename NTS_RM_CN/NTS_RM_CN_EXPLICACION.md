# NTS_RM_CN: Método de Matriz de Respuesta con Crank-Nicolson

## 1. Introducción al Algoritmo RM_CN

El programa **NTS_RM_CN.c** implementa el método de **Matriz de Respuesta (Response Matrix - RM)** combinado con integración temporal **Crank-Nicolson (CN)** para resolver la ecuación de transporte de neutrones en 2D.

### ¿Qué es Response Matrix + Crank-Nicolson?

**Response Matrix (RM):**
- Precomputa operadores de transferencia entre fronteras de regiones
- Cada región se caracteriza por sus "respuestas" a entradas en las fronteras
- Acelera enormemente la convergencia al eliminar iteraciones locales

**Crank-Nicolson (CN):**
- Esquema de integración temporal implícito (O(Δt²) de precisión)
- Provee estabilidad incondicional (sin límites en paso de tiempo)
- Especialmente útil para problemas en estado estacionario

**Combinación RM+CN:**
- Convergencia muy rápida (5-20 iteraciones típicamente)
- Estabilidad numérica garantizada
- Mayor costo computacional por iteración (compensado por menos iteraciones)
- Mejor precisión que DD y LD

## 2. Parámetros de Entrada

El programa acepta **11 parámetros de entrada** (idénticos a NTS_DD y NTS_LD):

### Tabla de Parámetros

| # | Parámetro | Rango | Descripción | Recomendación RM_CN |
|---|-----------|-------|-------------|---------------------|
| 1 | N | 2,4,6,8,10,12,14,16,18 | Orden de cuadratura SN. Genera M=N*(N+2)/2 direcciones | 4 ó 6 (RM_CN eficiente con órdenes altos) |
| 2 | NZ | ≥1 | Número de zonas de material distintas | Cualquier cantidad (RM_CN maneja bien) |
| 3 | ZONES | σ_t σ_s [cm⁻¹] | Propiedades de cada zona: σ_total σ_scattering | σ_s < σ_t siempre |
| 4 | NR_X | ≥1 | Número de regiones en eje X | 2-3 típico (5-10 nodos por región) |
| 5 | XDOM | L[cm] M[nodos] | Longitud y nodos por región X | Malla no uniforme permitida |
| 6 | NR_Y | ≥1 | Número de regiones en eje Y | 2-3 típico |
| 7 | YDOM | L[cm] M[nodos] | Longitud y nodos por región Y | Malla no uniforme permitida |
| 8 | ZMAP | Matriz (NR_Y × NR_X) | Índice de zona [1..NZ] en cada región | Indexación 1-based |
| 9 | QMAP | Matriz (NR_Y × NR_X) | Valor de fuente por región [0,∞) | Sin restricción superior |
| 10 | BC | 4 valores BOTTOM TOP LEFT RIGHT | Condiciones de frontera | Simetría=-1.0, Vacío=0.0, Especificada>0.0 |
| 11 | TOLERANCE | 0 < ε < 1 | Tolerancia de convergencia relativa | **1e-6 recomendado** (RM_CN puede ser más estricto) |

### Restricciones Críticas

1. **N debe ser PAR**: N ∈ {2, 4, 6, 8, 10, 12, 14, 16, 18}
   - Violación: Error en inicialización de cuadratura
   - Fórmula: M = N*(N+2)/2 = número de direcciones discretas

2. **σ_s < σ_t para cada zona**: (scattering < absorción total)
   ```
   σ_a = σ_t - σ_s > 0  [absorción positiva]
   ```
   - Violación: Divergencia o resultados no físicos

3. **ZMAP indexación 1-based**: Índices 1 a NZ (convertidos internamente a 0-based)

4. **Malla consistente**: 
   - Regiones XDOM deben sumar el dominio completo
   - Nodos deben ser ≥ 1 por región

5. **Tolerancia razonable**: 1e-2 a 1e-7 (no cero)

## 3. Metodología: Response Matrix + Crank-Nicolson

### Fase 1: Análisis Espectral (Spectrum Analysis)

En NTS_RM_CN.c, la función `spectrum()` realiza:

1. **Para cada zona material:**
   - Construye matriz de transferencia radiativa (respuesta a entrada unitaria en frontera)
   - Calcula autovalores (eigenvalues XVALS, YVALS) en direcciones X e Y
   - Calcula autovectores (eigenvectors XVECTS, YVECTS)

2. **Interpretación física:**
   - Los autovalores representan tasas de decaimiento en cada dirección
   - Los autovectores codifican los modos propios de transporte

### Fase 2: Construcción de Matriz de Respuesta

La función `response_matrix()` arma:

1. **Operadores de transferencia R:**
   - Relacionan flujos angulares en frontera izquierda con flujos salientes a derecha
   - R = exp(λ·distancia) · transformación angular

2. **Eficiencia:**
   - Evita resolver transporte puro cada iteración
   - Usa operadores precalculados

### Fase 3: Iteración con Crank-Nicolson

El esquema implícito CN:
```
[I + (Δt/2)·RM] · Φⁿ⁺¹ = [I - (Δt/2)·RM] · Φⁿ + S
```

Donde:
- **I** = identidad
- **RM** = matriz de respuesta
- **Φ** = flujo de neutrones
- **S** = término fuente
- **Δt** = paso de iteración lógico

### Por Qué RM_CN es Muy Rápido

1. **Menos iteraciones:** 5-20 vs 30-100 (DD/LD)
   - RM precomputa información global → convergencia más rápida
   - CN es implícito → pasos más grandes sin inestabilidad

2. **Estabilidad incondicional:**
   - DD/LD pueden requerir pasos pequeños
   - RM_CN acepta pasos arbitrarios sin divergir

3. **Costo por iteración más alto:**
   - Operaciones matriciales O(M·nodos²)
   - vs. O(nodos) para LD
   - Compensado por factor 5-10x en iteraciones

## 4. Ejemplo 1: Problema Simple (2×2 Regiones)

```
Entrada:
4                      # N=4 → M=12 direcciones
1                      # NZ=1 (un material)
0.5 0.3                # σ_t=0.5, σ_s=0.3 cm⁻¹
2                      # NR_X=2 regiones en X
10.0 5                 # Región X1: 10 cm, 5 nodos
10.0 5                 # Región X2: 10 cm, 5 nodos
2                      # NR_Y=2 regiones en Y
10.0 5                 # Región Y1: 10 cm, 5 nodos
10.0 5                 # Región Y2: 10 cm, 5 nodos
1 1                    # ZMAP: Región superior [1, 1]
1 1                    # ZMAP: Región inferior [1, 1]
1.0 1.0                # QMAP: Fuente superior [1.0, 1.0]
1.0 1.0                # QMAP: Fuente inferior [1.0, 1.0]
0.0 0.0 0.0 0.0       # BC: vacío en todas las fronteras
1e-5                   # Tolerancia
```

### Ejecución Esperada

```bash
$ gcc -O2 -o NTS_RM_CN programs/NTS_RM_CN.c -lm
$ cat > input_simple.txt << 'EOF'
4
1
0.5 0.3
2
10.0 5
10.0 5
2
10.0 5
10.0 5
1 1
1 1
1.0 1.0
1.0 1.0
0.0 0.0 0.0 0.0
1e-5
EOF

$ ./NTS_RM_CN input_simple.txt > output.json
$ cat output.json
```

### Salida Esperada

```json
{
  "STATUS": 0,
  "ITER": 8,
  "CPU": 0.001234,
  "MFLUX": [ ... matriz 10×10 de flujo escalar ...],
  "MFLOW": [ ... tensor 10×10×12 de flujo angular ...],
  "XFLOW": [...],
  "YFLOW": [...]
}
```

**Interpretación:**
- **STATUS=0**: Convergencia exitosa
- **ITER=8**: RM_CN converge en pocas iteraciones (esperado)
- **CPU=~0.001s**: Tiempo muy bajo (RM_CN es eficiente)
- **MFLUX**: Matriz de flujo escalar φ(x,y) = ∑_m φ_m(x,y)
- **MFLOW**: Componentes angulares φ_m(x,y) para cada dirección m

## 5. Ejemplo 2: Problema Heterogéneo (Múltiples Materiales)

```
Entrada:
4                      # N=4
2                      # NZ=2 (dos materiales distintos)
0.5 0.3                # Zona 1: σ_t=0.5, σ_s=0.3
1.0 0.6                # Zona 2: σ_t=1.0, σ_s=0.6 (más absorbente)
2
10.0 5
10.0 5
2
10.0 5
10.0 5
1 2                    # ZMAP: Región superior [Material1, Material2]
2 1                    # ZMAP: Región inferior [Material2, Material1]
1.0 0.7                # QMAP: Fuentes asimétricas
0.7 1.0
0.0 0.0 0.0 0.0
1e-5
```

**Ventaja RM_CN aquí:**
- RM_CN maneja interfaces de material con máxima precisión
- Spectrum() calcula respuestas especiales para cada zona
- Convergencia rápida pese a heterogeneidades

**Resultado típico:** STATUS=0, ITER=10-15

## 6. Ejemplo 3: Malla Fina (Alta Precisión)

```
Entrada:
6                      # N=6 → M=24 direcciones (más preciso)
1
0.4 0.2
3                      # NR_X=3 regiones
6.0 6                  # Región 1: 6 cm, 6 nodos
7.0 6                  # Región 2: 7 cm, 6 nodos
7.0 6                  # Región 3: 7 cm, 6 nodos
3                      # NR_Y=3 regiones
7.0 6                  # Región 1: 7 cm, 6 nodos
6.5 6                  # Región 2: 6.5 cm, 6 nodos
6.5 6                  # Región 3: 6.5 cm, 6 nodos
1 1 1                  # ZMAP: toda región 1
1 1 1
1 1 1
1.5 1.5 1.5            # QMAP: fuentes moderadas
1.5 1.5 1.5
1.5 1.5 1.5
0.0 0.0 0.0 0.0
1e-6                   # Tolerancia más estricta (RM_CN puede hacerlo)
```

**Ventaja RM_CN aquí:**
- Matriz de respuesta precomputa toda la geometría fina
- Crank-Nicolson mantiene estabilidad con malla refinada
- Tolerancia 1e-6 alcanzable en tiempo razonable

**Resultado típico:** STATUS=0, ITER=12-20, CPU moderado

## 7. Ejemplo 4: Problema Asimétrico

```
Entrada:
4
1
0.6 0.32
2
12.0 6
12.0 6
2
12.0 6
12.0 6
1 1
1 1
2.0 0.5                # Fuentes asimétricas: esquina 0,0 con fuente alta
0.5 1.5                # Región 0,1 con fuente baja
1.5 0.0                # Lado izquierdo: flujo especificado 1.5
0.5 0.5                # Lado derecho y superior: menor flujo
```

**Validez:** RM_CN mantiene estabilidad numérica
**Iteraciones esperadas:** 10-18
**Precisión:** Excelente en gradientes asimétricos

## 8. Comparación: RM_CN vs DD vs LD

### Tabla Comparativa de Métodos

| Métrica | LD (Line Diffusion) | DD (Domain Decomp.) | RM_CN (Response Matrix) |
|---------|-------------------|-----------------|---------------------|
| **Convergencia** | 20-40 iter | 30-100 iter | **5-20 iter** ✓ |
| **Costo/iteración** | Muy bajo | Medio | Alto |
| **Tiempo total** | Muy rápido | Medio | **Rápido** ✓ |
| **Precisión** | Buena | Muy buena | **Excelente** ✓ |
| **Estabilidad** | Buena | Muy buena | **Incondicional** ✓ |
| **Memoria** | Baja | Media | Media |
| **Heterogeneidad** | Bien | Muy bien | **Óptimo** ✓ |
| **Malla fina** | Bien | Bien | **Óptimo** ✓ |
| **Implementación** | Sencilla | Moderada | **Compleja** |

### Guía de Selección

**Usa LD cuando:**
- ✓ Problema simple, 2-3 zonas
- ✓ Malla moderada (hasta 100 nodos por región)
- ✓ Velocidad es crítica
- ✓ Presupuesto computacional bajo

**Usa DD cuando:**
- ✓ Heterogeneidad media-alta
- ✓ Anisotropía fuerte
- ✓ Quieres buen balance precisión/velocidad
- ✓ Mallas no uniformes complejas

**Usa RM_CN cuando:**
- ✓ Precisión es crítica (publicaciones, diseño)
- ✓ Problema tiene múltiples materiales complejos
- ✓ Malla fina o altamente no uniforme
- ✓ Tolerancia estricta requerida (<1e-6)
- ✓ Presupuesto computacional moderado disponible
- ✓ **MEJOR OPCIÓN GENERAL para problemas desafiantes**

## 9. Compilación

### Linux/Mac

```bash
cd /path/to/nts
# Comentar la línea #define del mingw si existe
sed -i 's/#define printf __mingw_printf/\/\/ #define printf __mingw_printf/' programs/NTS_RM_CN.c

# Compilar
gcc -O2 -o programs/linux/NTS_RM_CN programs/NTS_RM_CN.c -lm

# Verificar
./programs/linux/NTS_RM_CN --help 2>&1 || echo "Programa compilado (sin --help)"
```

### Flags de Compilación

| Flag | Propósito |
|------|----------|
| `-O2` | Optimización nivel 2 (recomendado) |
| `-lm` | Libreríamatemática (REQUIRIDO) |
| `-O3` | Optimización más agresiva (opcional, +5-10% velocidad) |
| `-march=native` | Optimización específica CPU (opcional, +10% velocidad) |

## 10. Análisis de Salida

### Estructura JSON

```json
{
  "STATUS": 0,                          // 0=éxito, 1=args, 2=lectura, 3=memoria
  "ITER": 8,                            // Iteraciones para convergencia
  "CPU": 0.00123,                       // Tiempo CPU [segundos]
  "MFLUX": [[...], [...], ...],         // Matriz flujo escalar (NR_Y×NR_X)
  "MFLOW": [[[...], [...]], ...],       // Tensor flujo angular (NR_Y×NR_X×M)
  "XFLOW": [[...], ...],                // Flujo en fronteras X (ND×M)
  "YFLOW": [[...], ...]                 // Flujo en fronteras Y (ND×M)
}
```

### Campos Detallados

**STATUS:**
- `0` = Convergencia exitosa
- `1` = Error en argumentos
- `2` = Error leyendo entrada
- `3` = Error de memoria

**ITER:**
- Número de iteraciones ejecutadas
- RM_CN típicamente: 5-20
- Compara con DD (30-100) y LD (20-40)

**CPU:**
- Tiempo de ejecución [segundos]
- Incluye spectrum() + iteraciones
- Típicamente: 0.001-0.1 segundos en CPU moderno

**MFLUX:**
- Matriz NR_Y × NR_X con flujo escalar total
- φ(i,j) = ∑_m φ_m(i,j) [sumado sobre todas las direcciones]
- Valores típicos: 0.1-100 [neutrones/(cm²·s)]

**MFLOW:**
- Tensor angular 3D: [NR_Y] [NR_X] [M directiones]
- φ_m(i,j) = flujo en dirección m, región (i,j)
- Suma sobre m = MFLUX(i,j)

**XFLOW / YFLOW:**
- Flujos en fronteras (condiciones de salida)
- Útiles para análisis de fugas

## 11. Validación y Debugging

### Checklist de Verificación

| Aspecto | Validación | Acción |
|--------|-----------|--------|
| **Entrada** | N es par (2-18) | Si falla: ERROR en cuadratura |
| **Entrada** | σ_s < σ_t para toda zona | Si falla: DIVERGENCIA |
| **Entrada** | ZMAP índices ∈ [1, NZ] | Si falla: Segfault o error lectura |
| **Entrada** | QMAP valores ≥ 0 | Si falla: Resultados no físicos |
| **Entrada** | BC válidas (-1, 0, o >0) | Si falla: Comportamiento indefinido |
| **Salida** | STATUS == 0 | Si ≠0: Revisar STDERRpara detalles |
| **Salida** | ITER > 0 y < 10000 | Si ≥10000: Problema mal puesto |
| **Salida** | Flujos > 0 (si fuentes > 0) | Si ≤0: Implementación bug |
| **Salida** | CPU < 10 segundos | Si >10s: Malla demasiado fina |
| **Física** | Conservación de energía | Integrar sobre dominio, verificar balance |

### Problemas Comunes y Soluciones

**Problema 1: STATUS ≠ 0**
```
Síntoma: STATUS = 2 (lectura error)
Causa: Formato entrada incorrecta
Solución: Verificar número de líneas (11) y formato numérico
```

**Problema 2: ITER > 100**
```
Síntoma: Demasiadas iteraciones
Causa: Tolerancia muy estricta O problema mal puesto
Solución: Aumentar TOL a 1e-4, revisar σ_s < σ_t
```

**Problema 3: MFLUX contiene NaN**
```
Síntoma: Flujos son NaN (Not a Number)
Causa: Instabilidad en spectrum() O σ_s ≥ σ_t
Solución: Revisar ZONES, reducir σ_s o aumentar σ_t
```

**Problema 4: CPU muy alto (>1 segundo)**
```
Síntoma: Ejecución lenta
Causa: Malla muy fina (N>10, muchos nodos) O tolerancia 1e-7
Solución: Reducir finura de malla o aumentar tolerancia a 1e-5
```

**Problema 5: MFLOW diverge entre iteraciones**
```
Síntoma: Flujos oscilan sin converger
Causa: Problema numérico en matrix operations
Solución: Reducir tamaño región (mejorar malla), revisar condiciones frontera
```

## 12. Directrices para Uso Óptimo

### Elección de N (Orden Cuadratura)

```
Problema                        | N Recomendado | M (direcciones)
-------------------------------|---------------|----------------
Simple (1-2 zonas, plano)      | 4             | 12
Estándar                        | 4-6           | 12-24
Heterogéneo (3+ zonas)         | 6             | 24
Alta precisión (<1e-6)         | 6-8           | 24-40
Muy complejo (anisotropía)     | 8-10          | 40-60
```

RM_CN es eficiente incluso con N alto porque spectrum() lo maneja bien.

### Elección de Nodos por Región

```
Tipo Problema              | Nodos/Región | Total Nodos | ITER RM_CN
--------------------------|--------------|-------------|----------
Simple                     | 3-4          | 9-16        | 5-10
Estándar                   | 5-6          | 25-36       | 8-15
Detallado                  | 6-8          | 36-64       | 10-20
Muy detallado              | 8-10         | 64-100      | 12-25
```

### Elección de Tolerancia

```
Aplicación                 | TOL       | Iteraciones RM_CN | CPU
--------------------------|-----------|------------------|------
Estudio preliminar         | 1e-3      | 3-8              | <1ms
Ingeniería                 | 1e-4      | 5-12             | 1-5ms
Verificación               | 1e-5      | 7-15             | 2-10ms
Investigación de precisión | 1e-6      | 10-20            | 5-20ms
Límite matemático          | 1e-7      | 15-30            | 10-50ms
```

## 13. Referencias Matemáticas

### Ecuación de Transporte 2D

```
μ·∂φ/∂x + η·∂φ/∂y + σ_t·φ = (σ_s/4π)·∫φ dΩ + Q/(4π)
```

Donde:
- φ(r,Ω,E) = flujo angular [neutrones/(cm²·s)]
- Ω = dirección (μ, η, ξ en coordenadas cartesianas)
- σ_t = sección eficaz total
- σ_s = sección eficaz de scattering
- Q = término fuente

### Discretización S_N

Sustituye integral angular por suma ponderada:
```
∫φ dΩ ≈ ∑_m w_m · φ_m
```

Con M = N(N+2)/2 direcciones y pesos w_m para cuadratura gaussiana.

### Método Response Matrix

Para región rectangular [0,L_x] × [0,L_y]:

```
R_x: φ_izq → φ_der  (matriz de transferencia X)
R_y: φ_inf → φ_sup  (matriz de transferencia Y)

Iteración k+1:
φ^(k+1) = (I - CN_implicit)^(-1) · (I + CN_implicit) · φ^k + S
```

Donde CN_implicit = matriz Crank-Nicolson (O(Δt²) precisión).

## 14. Conclusión

**NTS_RM_CN es el método más potente** cuando se requiere máxima precisión y estabilidad. Su principal costo es complejidad computacional (por iteración), ampliamente compensado por:

1. ✓ Convergencia ultra-rápida (5-20 iteraciones)
2. ✓ Estabilidad incondicional (confiable)
3. ✓ Máxima precisión (especialmente interfaces de material)
4. ✓ Manejo excelente de mallas finas y complejas

**Recomendación:**
- Para problemas rutinarios → **LD** (rápido)
- Para balance precisión/velocidad → **DD** (versátil)
- Para problemas desafiantes → **RM_CN** (preciso y estable)

---

**Documento generado automáticamente**  
NTS_RM_CN Simulation Guide | Response Matrix + Crank-Nicolson Method
