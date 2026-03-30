# 📖 NTS_DD.c - Guía de Uso del Algoritmo de Transporte de Neutrones

**Programa**: NTS_DD.c  
**Método**: Domain Decomposition + Discrete Ordinates (SN)  
**Aplicación**: Solución de la ecuación de transporte de neutrones en 2D  
**Fecha**: 27 de Marzo de 2026

---

## 📑 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Estructura de Entrada](#estructura-de-entrada)
3. [Parámetros Detallados](#parámetros-detallados)
4. [Ejemplos Prácticos](#ejemplos-prácticos)
5. [Compilación y Ejecución](#compilación-y-ejecución)
6. [Salida del Programa](#salida-del-programa)
7. [Validación y Consejos](#validación-y-consejos)

---

## 🎯 Introducción

### ¿Qué es NTS_DD?

NTS_DD es un programa que resuelve la **ecuación de transporte de neutrones** en un dominio 2D usando:

- **Discretización Angular**: Método de Ordenadas Discretas (SN) - discretiza todas las direcciones en M ordenadas
- **Discretización Espacial**: Malla cartesiana en 2D (X, Y)
- **Solución Iterativa**: Método Domain Decomposition que divide el dominio en subdominios
- **Heterogeneidad Material**: Soporta múltiples zonas con diferentes propiedades nucleares

### ¿Para Qué Sirve?

Simular:
- ✓ Transporte de neutrones en reactores, blindajes, etc.
- ✓ Difusión de partículas en medios heterogéneos
- ✓ Problemas con fuentes externas y condiciones de frontera complejas
- ✓ Análisis de crítica en sistemas nucleares

---

## 📥 Estructura de Entrada

El programa lee un archivo de **texto plano (.txt)** con **11 parámetros en orden específico**:

```
N                    ← Parámetro 1
NZ                   ← Parámetro 2
[NZ líneas de zonas] ← Parámetro 3
NR_X                 ← Parámetro 4
[NR_X líneas X]      ← Parámetro 5
NR_Y                 ← Parámetro 6
[NR_Y líneas Y]      ← Parámetro 7
[NR_Y×NR_X matriz]   ← Parámetro 8 (ZMAP)
[NR_Y×NR_X matriz]   ← Parámetro 9 (QMAP)
[4 valores BC]       ← Parámetro 10
[1 valor tol]        ← Parámetro 11
```

### Ejemplo Mínimo

```
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
```

---

## 🔧 Parámetros Detallados

### 1. **N** - Orden de la Cuadratura

**¿Qué es?** Define el número de direcciones discretas usadas para aproximar el continuo angular.

**Valores válidos**: 2, 4, 6, 8, 10, 12, 14, 16, 18 (DEBE SER PAR)

**Fórmula**: M = N × (N + 2) / 2 = Número de ordenadas discretas

| N | M (direcciones) | Velocidad | Precisión | Recomendado para |
|---|--|--|--|--|
| 2 | 3 | ⚡⚡⚡ Muy rápido | ⭐ Baja | Pruebas rápidas |
| 4 | 12 | ⚡⚡ Rápido | ⭐⭐⭐ Buena | **Uso general** |
| 6 | 24 | ⚡ Moderado | ⭐⭐⭐ Buena | Problemas medianos |
| 8 | 36 | Lento | ⭐⭐⭐⭐ Alta | Problemas complejos |
| 16 | 144 | ⚠️ Muy lento | ⭐⭐⭐⭐⭐ Muy alta | Máxima precisión |

**Ejemplo**: 
```
4    ← Genera 12 direcciones: M = 4*(4+2)/2 = 12
```

---

### 2. **NZ** - Número de Zonas Materiales

**¿Qué es?** Número de regiones con propiedades nucleares diferentes.

**Restricción**: NZ ≥ 1

**Nota**: Una "zona" es una región con secciones transversales (σ_t, σ_s) uniformes.

**Ejemplo**:
```
2    ← Dos zonas (materiales diferentes)
```

---

### 3. **ZONAS** - Propiedades de Cada Zona

**Formato**: NZ líneas, cada una con 2 valores: `sigma_t sigma_s`

**Parámetros**:
- **sigma_t (σ_t)**: Sección transversal total [cm⁻¹]
- **sigma_s (σ_s)**: Sección transversal de dispersión [cm⁻¹]
- **sigma_a (σ_a)**: Sección transversal de absorción = σ_t - σ_s (calculada internamente)

**Restricción**: σ_s < σ_t (siempre)

**Ejemplo**:
```
0.5 0.3     ← Zona 1: σ_t=0.5, σ_s=0.3, σ_a=0.2 cm⁻¹
1.0 0.7     ← Zona 2: σ_t=1.0, σ_s=0.7, σ_a=0.3 cm⁻¹
```

**Interpretación Física**:
- σ_t grande → Material opaco (bloquea neutrones)
- σ_s/σ_t grande → Material dispersor (scatter)
- σ_a/σ_t grande → Material absorbente (elimina neutrones)

---

### 4. **NR_X** - Número de Regiones en Dirección X

**¿Qué es?** Subdivisiones del dominio en dirección X para Domain Decomposition.

**Restricción**: NR_X ≥ 1

**Ejemplo**:
```
2    ← Dominio dividido en 2 regiones en X
```

---

### 5. **XDOM** - Discretización en Dirección X

**Formato**: NR_X líneas, cada una con 2 valores: `length_cm num_nodes`

**Parámetros**:
- **length_cm**: Ancho de la región en centímetros
- **num_nodes**: Número de puntos de malla en esa región

**Recomendación**: 5-8 nodos por región (mínimo 3)

**Ejemplo**:
```
10.0 5      ← Región X1: 10 cm de ancho, 5 nodos (Δx = 2 cm)
10.0 5      ← Región X2: 10 cm de ancho, 5 nodos
```

**Interpretación**: Dominio X total = 20 cm, puntos de malla = 10

---

### 6. **NR_Y** - Número de Regiones en Dirección Y

**¿Qué es?** Subdivisiones del dominio en dirección Y.

**Restricción**: NR_Y ≥ 1

**Ejemplo**:
```
2    ← Dominio dividido en 2 regiones en Y
```

---

### 7. **YDOM** - Discretización en Dirección Y

**Formato**: NR_Y líneas, cada una con 2 valores: `length_cm num_nodes`

**Parámetros**: Idénticos a XDOM

**Ejemplo**:
```
10.0 5      ← Región Y1: 10 cm de alto, 5 nodos
10.0 5      ← Región Y2: 10 cm de alto, 5 nodos
```

**Resultado**: Dominio Y = 20 cm, puntos de malla = 10

---

### 8. **ZMAP** - Mapa de Zonas

**¿Qué es?** Matriz que asigna cada región geométrica a una zona material.

**Dimensiones**: NR_Y filas × NR_X columnas

**Valores**: Enteros de 1 a NZ

**Orden de lectura**: Por filas (Y primero)

**Ejemplo**:
```
1 2
2 1
```

**Interpretación**:
```
        X1    X2
    +-----+-----+
Y2  |  2  |  1  |
    +-----+-----+
Y1  |  1  |  2  |
    +-----+-----+
```

Nota: Índice (0,0) = zona 1, (0,1) = zona 2, etc.

---

### 9. **QMAP** - Mapa de Fuentes Externas

**¿Qué es?** Matriz que especifica fuentes de neutrones en cada región.

**Dimensiones**: NR_Y filas × NR_X columnas

**Valores**: Números reales ≥ 0

**Unidades**: neutrones/cm²/s (o unidades normalizadas)

**Restricción**: Sin fuentes negativas

**Ejemplo**:
```
1.0 0.5
0.5 1.0
```

**Interpretación**: Región (0,0) tiene fuente 1.0, región (0,1) tiene fuente 0.5, etc.

---

### 10. **BC** - Condiciones de Frontera

**¿Qué es?** 4 valores que especifican condiciones en los 4 bordes del dominio.

**Formato**: `BOTTOM TOP LEFT RIGHT`

**Coordenadas**:
- **BOTTOM**: Frontera en y = 0 (borde inferior)
- **TOP**: Frontera en y = máximo (borde superior)
- **LEFT**: Frontera en x = 0 (borde izquierdo)
- **RIGHT**: Frontera en x = máximo (borde derecho)

**Valores Válidos**:

| Valor | Tipo | Significado | Uso |
|-------|------|-------------|-----|
| `-1.0` | Simetría | Reflexión especular | Problemas simétricos |
| `0.0` | Vacío | Sin flujo entrante | **Más común** |
| `> 0` | Flujo especificado | Fuente de frontera constante | Condiciones impuestas |

**Ejemplo**:
```
0.0 0.0 0.0 0.0
```
Significa: Vacío en todos los lados (sin flujo entrante de ninguna dirección)

**Otro ejemplo**:
```
1.0 0.5 0.5 2.0
```
Significa:
- Bottom (y=0): flujo = 1.0 entrando
- Top (y=máx): flujo = 0.5 entrando
- Left (x=0): flujo = 0.5 entrando
- Right (x=máx): flujo = 2.0 entrando

---

### 11. **TOLERANCIA** - Criterio de Convergencia

**¿Qué es?** Tolerancia relativa para el criterio de convergencia iterativo.

**Rango válido**: 0 < tol < 1

**Criterio**: ||φ_nuevo - φ_anterior|| / ||φ_nuevo|| < tol

| Tolerancia | Iteraciones Típicas | Velocidad | Precisión | Recomendación |
|--|--|--|--|--|
| `1e-4` | 10-20 | ⚡⚡⚡ Muy rápido | ⭐⭐ Aceptable | Pruebas |
| `1e-5` | 20-100 | ⚡⚡ Rápido | ⭐⭐⭐ Buena | **Estándar** |
| `1e-6` | 100-500 | ⚡ Lento | ⭐⭐⭐⭐ Alta | Análisis preciso |
| `1e-7` | 500+ | ⚠️ Muy lento | ⭐⭐⭐⭐⭐ Muy alta | Máxima precisión |

**Recomendación**: `1e-5` para balance óptimo

**Ejemplo**:
```
1e-5
```

---

## 📋 Ejemplos Prácticos

### Ejemplo 1: Problema Simple Uniforme

**Descripción**: Dominio uniforme 20×20 cm, una sola zona, fuente uniforme, bordes al vacío.

```
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
```

**Interpretación**:
- Cuadratura: Orden 4 (12 direcciones)
- Geometría: 20×20 cm dividido en 2×2 regiones
- Malla: 5 nodos/región = 10×10 puntos totales
- Material: Uniforme (Zona 1 en todo el dominio)
- Fuentes: Uniforme (1.0 en todas partes)
- Bordes: Vacío (0.0)
- Tolerancia: 1e-5

**Expectativa**: Resultado simétrico

---

### Ejemplo 2: Problema Heterogéneo

**Descripción**: Dos materiales en patrón tablero, fuentes variables.

```
4
2
0.5 0.3
1.0 0.7
2
10.0 5
10.0 5
2
10.0 5
10.0 5
1 2
2 1
1.0 0.5
0.5 1.0
0.0 0.0 0.0 0.0
1e-5
```

**Interpretación**:
- Dos zonas: Zona 1 (σ_t=0.5), Zona 2 (σ_t=1.0, más absorbente)
- Zonas en patrón checkerboard (diagonal)
- Fuentes variables (mayor en esquina (0,0))
- Bordes al vacío

**Expectativa**: Mayor flujo donde hay más fuente y menos absorción

---

### Ejemplo 3: Con Condiciones de Frontera Especificadas

**Descripción**: Flujo de entrada especificado en bordes.

```
6
2
0.5 0.3
0.8 0.5
2
10.0 6
10.0 6
2
10.0 6
10.0 6
1 2
2 1
1.0 1.0
1.0 1.0
1.0 0.5 0.5 2.0
1e-5
```

**Interpretación**:
- Cuadratura mayor (N=6, 24 direcciones)
- Flujos entrantes: Bottom=1.0, Top=0.5, Left=0.5, Right=2.0
- Asimetría en bordes → resultado asimétrico

---

### Ejemplo 4: Con Simetría

**Descripción**: Aprovechar simetría para reducir cálculo.

```
4
1
0.5 0.3
1
20.0 10
1
20.0 10
1
1.0
-1.0 0.0 -1.0 0.0
1e-5
```

**Interpretación**:
- Bottom = -1.0 (simetría)
- Left = -1.0 (simetría)
- Top = 0.0 (vacío)
- Right = 0.0 (vacío)
- Solo 1 región, 1 zona, dominio no dividido

---

## 🔨 Compilación y Ejecución

### Paso 1: Compilar el Programa

```bash
cd /home/int64/Documents/Master_PPGMC/Trabajos/nts

gcc -O2 -o programs/linux/NTS_DD programs/NTS_DD.c -lm
```

**Flags importantes**:
- `-O2`: Optimización de compilador
- `-lm`: Link biblioteca matemática (necesaria)

### Paso 2: Crear Archivo de Entrada

```bash
cat > mi_problema.txt << 'EOF'
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
```

### Paso 3: Ejecutar

```bash
# Ver en pantalla
./programs/linux/NTS_DD mi_problema.txt

# Guardar en archivo JSON
./programs/linux/NTS_DD mi_problema.txt > resultado.json
```

### Paso 4: Analizar Resultados

```bash
# Ver primeras líneas
head -50 resultado.json

# Extraer status e iteraciones
grep -E '"STATUS"|"ITER"|"CPU"' resultado.json
```

---

## 📤 Salida del Programa

### Formato JSON

```json
{
  "STATUS": 0,           // 0=éxito, 1/2/3=error
  "ITER": 28,            // Número de iteraciones
  "CPU": 0.998883,       // Tiempo en segundos
  "MFLUX": [             // Flujo escalar (matriz)
    [...],
    [...],
    ...
  ],
  "MFLOW": [...],        // Flujo angular (tensor 3D)
  "XFLOW": [...],        // Flujo en bordes Y
  "YFLOW": [...]         // Flujo en bordes X
}
```

### Campos de Salida

| Campo | Tipo | Descripción |
|-------|------|-------------|
| **STATUS** | int | Código de estado: 0=éxito, 1=args, 2=lectura, 3=memoria |
| **ITER** | int | Iteraciones para convergencia (típico: 10-100) |
| **CPU** | double | Tiempo de cálculo en segundos |
| **MFLUX** | matriz | Flujo escalar en cada nodo [valores positivos] |
| **MFLOW** | tensor 3D | Flujo angular para cada ordenada y nodo |
| **XFLOW** | matriz | Flujo angular en bordes Y |
| **YFLOW** | matriz | Flujo angular en bordes X |

### Códigos de Error

| Código | Significado |
|--------|------------|
| 0 | ✅ Éxito |
| 1 | ❌ Falta argumento (nombre de archivo) |
| 2 | ❌ Error leyendo archivo (formato incorrecto) |
| 3 | ❌ Error de memoria (malla muy grande) |

---

## ✅ Validación y Consejos

### Checklist de Validación

Antes de ejecutar, verificar:

- [ ] **N es par** entre 2-18
- [ ] **NZ ≥ 1**
- [ ] **Para cada zona**: σ_s < σ_t
- [ ] **Todas las longitudes > 0**
- [ ] **Todos los nodos > 0** (recomendado ≥ 3)
- [ ] **ZMAP**: Valores de 1 a NZ
- [ ] **QMAP**: Todos ≥ 0 (no negativos)
- [ ] **BC**: -1.0, 0.0, o positivo
- [ ] **Tolerancia**: 0 < tol < 1
- [ ] **Dimensiones consistentes**: cm, cm⁻¹

### Problemas Comunes

| Problema | Causa | Solución |
|----------|-------|----------|
| ERROR: No input file | Falta argumento | `./NTS_DD archivo.txt` |
| STATUS=2 | Formato de entrada incorrecto | Verificar orden y tipo de parámetros |
| STATUS=3 | Memoria insuficiente | Reducir nodos por región |
| ITER > 1000 | Divergencia | Aumentar tolerancia (ej: 1e-4) |
| MFLUX = 0 | Sin fuentes | Aumentar valores en QMAP |
| Muy lento | Malla muy fina o N muy alto | Usar N=4, 5-8 nodos/región |

### Consejos Prácticos

1. **Empieza simple**: Usa Ejemplo 1 primero para familiarizarte
2. **Incrementa complejidad**: Luego prueba con múltiples zonas
3. **Balance velocidad-precisión**: N=4, tol=1e-5, 5-8 nodos/región
4. **Verifica unidades**: Todo en cm y cm⁻¹
5. **Simetría cuando sea posible**: BC=-1.0 reduce cálculo
6. **Prueba tolerancias**: 1e-5 es muy bueno para la mayoría
7. **Monitorea iteraciones**: >500 indica problema

### Interpretación de Resultados

- **MFLUX positivo**: ✅ Correcto (flujo siempre positivo)
- **MFLUX simétrico**: Esperado si zona y BC simétricas
- **MFLUX máximo en fuentes**: ✅ Correcto
- **MFLUX menor en material absorbente**: ✅ Correcto
- **ITER típico**: 10-100 con tol=1e-5

---

## 📚 Referencia Rápida

### Parámetros Recomendados

```
Aplicación              N    Nodos/región   Tolerancia
─────────────────────────────────────────────────────
Prueba rápida           2    3-4            1e-4
Uso general            4    5-8            1e-5   ✓
Análisis detallado     6-8  8-10           1e-5
Máxima precisión       10-16 10-20         1e-6-7
```

### Fórmulas Útiles

```
Número de direcciones:      M = N*(N+2)/2
Tamaño de malla:            Total_nodos = NR_X*nodos_x * NR_Y*nodos_y
Dimensiones ZMAP/QMAP:      NR_Y filas × NR_X columnas
Absorption:                 σ_a = σ_t - σ_s
```

---

**¡Listo para comenzar!** 🚀

Consulta `NTS_DD_EXAMPLE_INPUT.json` para ver todos los ejemplos en formato JSON.
