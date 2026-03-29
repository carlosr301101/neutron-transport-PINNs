# 📖 NTS_LD.c - Guía de Uso del Método Line Diffusion para Transporte de Neutrones

**Programa**: NTS_LD.c  
**Método**: Line Diffusion (LD) + Discrete Ordinates (SN)  
**Aplicación**: Solución de la ecuación de transporte de neutrones en 2D  
**Fecha**: 27 de Marzo de 2026

---

## 📑 Tabla de Contenidos

1. [¿Qué es NTS_LD?](#qué-es-nts_ld)
2. [Diferencias con NTS_DD](#diferencias-con-nts_dd)
3. [Estructura de Entrada](#estructura-de-entrada)
4. [Parámetros Detallados](#parámetros-detallados)
5. [Ejemplos Prácticos](#ejemplos-prácticos)
6. [Compilación y Ejecución](#compilación-y-ejecución)
7. [Análisis de Resultados](#análisis-de-resultados)
8. [Cuándo Usar LD vs DD](#cuándo-usar-ld-vs-dd)

---

## 🎯 ¿Qué es NTS_LD?

### Definición

**NTS_LD** es un programa que resuelve la **ecuación de transporte de neutrones** en 2D usando:

- **Método Line Diffusion (LD)**: Itera sobre líneas (filas o columnas) del dominio en lugar de bloques
- **Discretización Angular (SN)**: Discretiza direcciones en M ordenadas discretas
- **Malla Cartesiana 2D**: Resuelve en dominio rectangular (X, Y)
- **Heterogeneidad Material**: Soporta múltiples zonas con propiedades distintas

### ¿Para Qué Sirve?

✓ Simular transporte de neutrones en geometrías 2D  
✓ Analizar problemas con fuentes externas complejas  
✓ Estudiar comportamiento de partículas en medios heterogéneos  
✓ Resolver problemas de crítica nuclear  
✓ Comparar convergencia con otros métodos (LD vs DD)  

### Características Principales

- **Iteración Line-by-Line**: Más eficiente para algunos problemas que decomposición de bloques
- **Converge Rápido**: Especialmente en problemas débilmente anisotrópicos
- **Bajo Requerimiento de Memoria**: En comparación con DD
- **Salida JSON**: Fácil de procesar con herramientas modernas

---

## 🔄 Diferencias con NTS_DD

### Comparación de Métodos

| Aspecto | **NTS_DD (Domain Decomposition)** | **NTS_LD (Line Diffusion)** |
|---------|-----------------------------------|---------------------------|
| **Estrategia** | Divide dominio en bloques 2×2 | Itera sobre líneas (filas) |
| **Convergencia** | Buena para problemas 2D | Excelente para débil anisotropía |
| **Memoria** | Mayor (bloques 2D) | Menor (líneas 1D) |
| **Tiempo** | Medio-Alto | Típicamente más rápido |
| **Problemas Anisotrópicos** | Muy robustos | Buenos, pero menos que DD |
| **Estabilidad** | Muy estable | Muy estable |
| **Ideal para** | Problemas generales 2D | Geometrías con estructura lineal |

### Cuándo Usar Cada Uno

**Usar NTS_DD si**:
- Problema altamente anisotrópico
- Fuentes con dirección fuerte
- Geometría 2D compleja
- Necesitas máxima estabilidad

**Usar NTS_LD si**:
- Problema débilmente anisotrópico
- Geometría tipo "bandas" u "capas"
- Necesitas velocidad
- Memoria es limitada
- Analizando línea-por-línea

---

## 📥 Estructura de Entrada

El programa espera un archivo de **texto plano (.txt)** con **11 parámetros exactamente en este orden**:

```
N                    ← Parámetro 1: Orden de cuadratura
NZ                   ← Parámetro 2: Número de zonas
[NZ líneas]          ← Parámetro 3: Propiedades de zonas
NR_X                 ← Parámetro 4: Regiones en X
[NR_X líneas]        ← Parámetro 5: Discretización X
NR_Y                 ← Parámetro 6: Regiones en Y
[NR_Y líneas]        ← Parámetro 7: Discretización Y
[Matriz NR_Y×NR_X]   ← Parámetro 8: Mapa de zonas
[Matriz NR_Y×NR_X]   ← Parámetro 9: Mapa de fuentes
[4 valores]          ← Parámetro 10: Condiciones de frontera
[1 valor]            ← Parámetro 11: Tolerancia
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

Define el número de direcciones discretas (ordenadas) para aproximar el continuo angular.

**Valores válidos**: 2, 4, 6, 8, 10, 12, 14, 16, 18 (DEBEN SER PARES)

**Fórmula**: M = N × (N + 2) / 2

| N | Direcciones | Velocidad | Precisión | Recomendación |
|---|--|--|--|--|
| 2 | 3 | ⚡⚡⚡ Muy rápido | ⭐ Baja | Pruebas |
| 4 | 12 | ⚡⚡ Rápido | ⭐⭐⭐ Buena | **Estándar** |
| 6 | 24 | ⚡ Moderado | ⭐⭐⭐ Buena | Recomendado |
| 8 | 36 | Normal | ⭐⭐⭐⭐ Alta | Buena |
| 16 | 144 | Lento | ⭐⭐⭐⭐⭐ Muy alta | Máxima precisión |

**Ejemplo**:
```
4    ← Genera 12 direcciones discretas
```

**Nota**: LD maneja bien incluso valores altos de N

---

### 2. **NZ** - Número de Zonas Materiales

Especifica cuántas regiones con propiedades nucleares diferentes existen.

**Rango**: NZ ≥ 1

**Ejemplo**:
```
2    ← Dos zonas (materiales diferentes)
```

---

### 3. **ZONAS** - Propiedades de Cada Zona

NZ líneas, cada una con 2 valores: `sigma_t sigma_s`

**Parámetros**:
- **σ_t (sigma_t)**: Sección transversal total [cm⁻¹]
  - Mayor σ_t → Material más opaco
  - Típicamente: 0.1 a 2.0 cm⁻¹
  
- **σ_s (sigma_s)**: Sección transversal de dispersión [cm⁻¹]
  - Debe ser < σ_t (siempre)
  - σ_a = σ_t - σ_s (absorción, calculada internamente)

**Restricción**: σ_s < σ_t (crítica)

**Ejemplo**:
```
0.5 0.3     ← Zona 1: σ_t=0.5, σ_s=0.3, σ_a=0.2
1.2 0.6     ← Zona 2: σ_t=1.2, σ_s=0.6, σ_a=0.6 (más absorbente)
```

**Interpretación Física**:
```
Zona 1: 40% absorción, 60% dispersión
Zona 2: 50% absorción, 50% dispersión
```

---

### 4. **NR_X** - Número de Regiones en Dirección X

Define las subdivisiones del dominio en dirección X para la discretización espacial.

**Rango**: NR_X ≥ 1

**Recomendación**: 2-4 regiones típicamente

**Ejemplo**:
```
2    ← Dominio X dividido en 2 regiones
```

---

### 5. **XDOM** - Discretización en Dirección X

NR_X líneas, cada una: `length_cm num_nodes`

| Campo | Descripción | Rango |
|-------|-------------|-------|
| **length_cm** | Ancho de la región [cm] | > 0 |
| **num_nodes** | Puntos de malla en región | ≥ 3 |

**Recomendación**: 5-8 nodos/región para malla normal

**Ejemplo**:
```
10.0 5      ← Región X1: 10 cm ancho, 5 nodos (Δx=2 cm)
10.0 6      ← Región X2: 10 cm ancho, 6 nodos (Δx=1.67 cm)
```

**Resultado**: Dominio X total = 20 cm, 11 nodos

---

### 6. **NR_Y** - Número de Regiones en Dirección Y

Análogo a NR_X, pero para dirección Y.

**Rango**: NR_Y ≥ 1

---

### 7. **YDOM** - Discretización en Dirección Y

NR_Y líneas con mismo formato que XDOM: `length_cm num_nodes`

**Ejemplo**:
```
10.0 5
10.0 5
```

---

### 8. **ZMAP** - Mapa de Asignación de Zonas

Matriz de **NR_Y filas × NR_X columnas** con índices de zonas (1 a NZ).

**Orden de lectura**: Por filas (Y primero)

**Valores**: 1, 2, ..., NZ

**Ejemplo** (para NR_Y=2, NR_X=2):
```
1 2     ← Fila Y1: Región(Y1,X1)=Zona1, Región(Y1,X2)=Zona2
2 1     ← Fila Y2: Región(Y2,X1)=Zona2, Región(Y2,X2)=Zona1
```

**Visualización**:
```
        X1    X2
    +-----+-----+
Y2  |  2  |  1  |
    +-----+-----+
Y1  |  1  |  2  |
    +-----+-----+
```

---

### 9. **QMAP** - Mapa de Fuentes Externas

Matriz de **NR_Y filas × NR_X columnas** con valores de fuentes (≥ 0).

**Valores**: Números reales ≥ 0

**Unidades**: neutrones/cm²/s (o normalizadas)

**Restricción**: No se permiten fuentes negativas

**Ejemplo**:
```
1.0 0.5     ← Fila Y1: Q(Y1,X1)=1.0, Q(Y1,X2)=0.5
0.5 1.0     ← Fila Y2: Q(Y2,X1)=0.5, Q(Y2,X2)=1.0
```

---

### 10. **BC** - Condiciones de Frontera

4 valores separados: `BOTTOM TOP LEFT RIGHT`

**Significado**:
- **BOTTOM** (y=0): Frontera inferior
- **TOP** (y=máximo): Frontera superior
- **LEFT** (x=0): Frontera izquierda
- **RIGHT** (x=máximo): Frontera derecha

**Valores Válidos**:

| Valor | Tipo | Significado |
|-------|------|------------|
| `-1.0` | Simetría | Reflexión especular (flujo reflejado) |
| `0.0` | Vacío | **MÁS COMÚN**: Sin flujo entrante |
| `> 0` | Flujo especificado | Fuente de frontera con valor constante |

**Ejemplos**:

```
0.0 0.0 0.0 0.0
```
Significado: Vacío en todos los lados (sin entrada de neutrones)

```
1.0 0.5 0.5 2.0
```
Significado: 
- Bottom: flujo 1.0
- Top: flujo 0.5
- Left: flujo 0.5
- Right: flujo 2.0 (entrada más fuerte)

---

### 11. **TOLERANCIA** - Criterio de Convergencia

Un único valor decimal: criterio para convergencia iterativa.

**Rango**: 0 < tol < 1

**Criterio**: ||φ_nuevo - φ_anterior|| / ||φ_nuevo|| < tolerancia

| Tolerancia | Iteraciones | Velocidad | Precisión | Uso |
|--|--|--|--|--|
| `1e-4` | 10-30 | ⚡⚡⚡ Muy rápido | ⭐⭐ Aceptable | Pruebas |
| `1e-5` | 30-100 | ⚡⚡ Rápido | ⭐⭐⭐ Buena | **Estándar** |
| `1e-6` | 100-500 | ⚡ Lento | ⭐⭐⭐⭐ Alta | Análisis |
| `1e-7` | 500+ | Muy lento | ⭐⭐⭐⭐⭐ Muy alta | Máxima |

**Recomendación**: `1e-5` para balance velocidad-precisión

**Ejemplo**:
```
1e-5
```

---

## 📋 Ejemplos Prácticos

### Ejemplo 1: Problema Simple Uniforme

**Archivo**: `simple.txt`

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
- Dominio: 20×20 cm, 10×10 nodos
- Material: Único (σ_t=0.5, σ_s=0.3)
- Fuentes: Uniformes (1.0 en todas partes)
- Bordes: Vacío
- Convergencia: Típicamente 15-40 iteraciones

---

### Ejemplo 2: Problema Heterogéneo

**Archivo**: `hetero.txt`

```
4
2
0.5 0.3
1.2 0.6
2
10.0 5
10.0 5
2
10.0 5
10.0 5
1 2
2 1
1.0 0.8
0.8 1.0
0.0 0.0 0.0 0.0
1e-5
```

**Interpretación**:
- 2 zonas: Zona 1 (débil) y Zona 2 (fuerte)
- Patrón checkerboard (diagonal)
- Fuentes ligeramente mayores en Zona 1
- LD converge rápidamente incluso con heterogeneidad

---

### Ejemplo 3: Con Cuadratura Alta

**Archivo**: `high_quadrature.txt`

```
8
1
0.6 0.35
2
12.0 6
12.0 6
2
12.0 6
12.0 6
1 1
1 1
1.5 1.5
1.5 1.5
0.0 0.0 0.0 0.0
1e-5
```

**Interpretación**:
- N=8 (36 direcciones) para mayor precisión angular
- Dominio 24×24 cm
- Malla más fina (6 nodos/región)
- Mayor tiempo de cálculo, mejor precisión

---

### Ejemplo 4: Con Fuentes de Frontera

**Archivo**: `boundary_sources.txt`

```
6
1
0.4 0.2
3
6.0 4
7.0 4
7.0 4
3
7.0 4
6.5 4
6.5 4
1 1 1
1 1 1
1 1 1
2.0 0.5 0.5 0.5
0.0 0.0 0.0 0.0
1e-5
```

**Interpretación**:
- Geometría con 3 regiones por dirección (no uniforme)
- Fuente de frontera bottom=2.0 (mayor entrada)
- Problema asimétrico
- LD maneja bien este caso

---

## 🔨 Compilación y Ejecución

### Paso 1: Compilación

```bash
cd /home/int64/Documents/Master_PPGMC/Trabajos/nts

# Opción 1: Con optimización
gcc -O2 -o programs/linux/NTS_LD programs/NTS_LD.c -lm

# Opción 2: Simple
gcc -o programs/linux/NTS_LD programs/NTS_LD.c -lm

# Opción 3: Con debugging
gcc -g -o programs/linux/NTS_LD programs/NTS_LD.c -lm
```

**Flags importantes**:
- `-O2`: Optimización de compilador
- `-lm`: Linker de biblioteca matemática (NECESARIO)
- `-g`: Información de debugging (opcional)

---

### Paso 2: Crear Archivo de Entrada

```bash
cat > entrada.txt << 'EOF'
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

---

### Paso 3: Ejecutar

```bash
# Ver salida en pantalla
./programs/linux/NTS_LD entrada.txt

# Guardar en archivo JSON
./programs/linux/NTS_LD entrada.txt > salida.json

# Redireccionar stderr también (si hay warnings)
./programs/linux/NTS_LD entrada.txt > salida.json 2>&1
```

---

### Paso 4: Analizar Resultados

```bash
# Ver primeras líneas
head -100 salida.json

# Ver estructura JSON (con jq si está instalado)
cat salida.json | jq '.' | head -50

# Extraer campos específicos
grep -E 'STATUS|ITER|CPU' salida.json
```

---

## 📊 Análisis de Resultados

### Estructura de Salida JSON

```json
{
  "STATUS": 0,           // 0=éxito, 1/2/3=error
  "ITER": 35,            // Iteraciones para converger
  "CPU": 0.524,          // Tiempo en segundos
  "MFLUX": [             // Matriz: flujo escalar por nodo
    [valores...],
    [valores...],
    ...
  ],
  "MFLOW": [             // Tensor 3D: flujo angular
    [[...], [...], ...],
    [[...], [...], ...],
    ...
  ],
  "XFLOW": [...],        // Flujo en bordes Y
  "YFLOW": [...]         // Flujo en bordes X
}
```

### Campos de Salida

| Campo | Tipo | Descripción |
|-------|------|------------|
| **STATUS** | int | Código de salida (0=OK, 1/2/3=error) |
| **ITER** | int | Iteraciones para converger |
| **CPU** | double | Tiempo de cálculo [segundos] |
| **MFLUX** | matriz 2D | Flujo escalar integral en cada nodo |
| **MFLOW** | tensor 3D | Flujo angular para cada ordenada y nodo |
| **XFLOW** | matriz | Flujo angular en fronteras Y |
| **YFLOW** | matriz | Flujo angular en fronteras X |

### Códigos de Error

| Código | Significado |
|--------|------------|
| 0 | ✅ Éxito completo |
| 1 | ❌ Argumentos incorrectos (falta archivo) |
| 2 | ❌ Error leyendo archivo |
| 3 | ❌ Error de asignación de memoria |

---

## 🎯 Cuándo Usar LD vs DD

### LD Es Mejor Cuando

✓ Problema débilmente anisotrópico  
✓ Necesitas velocidad  
✓ Memoria es limitada  
✓ Geometría con estructura "en líneas" (capas, bandas)  
✓ Iteración eficiente por líneas es ventajosa  

### DD Es Mejor Cuando

✓ Problema fuertemente anisotrópico  
✓ Máxima estabilidad es crítica  
✓ Descomposición 2×2 ayuda convergencia  
✓ Estructura compleja 2D  
✓ Necesitas máxima robustez  

### Regla Práctica

**Intenta LD primero** para problemas 2D estándar. Si:
- Converge rápido → Excelente, usa LD
- Problemas convergencia → Prueba DD

---

## ✅ Validación y Troubleshooting

### Checklist Pre-Ejecución

- [ ] N es par entre 2-18
- [ ] NZ ≥ 1
- [ ] Para cada zona: σ_s < σ_t
- [ ] Todas longitudes > 0
- [ ] Todos nodos > 0
- [ ] ZMAP: índices 1 a NZ
- [ ] QMAP: todos ≥ 0
- [ ] BC: -1, 0, o positivo
- [ ] 0 < tol < 1

### Problemas Comunes

| Problema | Causa | Solución |
|----------|-------|----------|
| STATUS=1 | Falta argumento | `./NTS_LD archivo.txt` |
| STATUS=2 | Formato incorrecto | Verificar orden parámetros |
| STATUS=3 | Memoria insuficiente | Reducir nodos/región |
| ITER>500 | Convergencia lenta | Aumentar tolerancia |
| MFLUX=0 | Sin fuentes | Aumentar QMAP |
| Muy lento | Malla muy fina | Usar malla más gruesa |

---

## 📚 Referencia Rápida

### Parámetros Recomendados

```
Caso                N    Nodos/región  Tolerancia
─────────────────────────────────────────────────
Prueba rápida       2    3-4           1e-4
Análisis normal     4    5-8           1e-5 ✓
Análisis preciso    6    8-10          1e-5
Máxima precisión    8-10 10-15         1e-6
```

### Comparación LD vs DD

```
                LD          DD
Velocidad       ⚡⚡⚡        ⚡⚡
Memoria         ⚡⚡⚡        ⚡⚡
Estabilidad     ⚡⚡⚡        ⚡⚡⚡
Anisotropía     ⚡⚡         ⚡⚡⚡
```

---

**¡Listo para comenzar con NTS_LD!** 🚀

Consulta `NTS_LD_EXAMPLE_INPUT.json` para ejemplos en formato JSON.
