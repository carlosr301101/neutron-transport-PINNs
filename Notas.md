# Creacion de batch de datos

* Se necesita hacer una batch de datos para la parte de entrenamiento, para esto se pueden generar multiples configuraciones y guardarlas en la carpeta de inputs, cada una con un nombre diferente.

* Se ne cesita cambiar los datos con un pequeno desplazamiento para que el modelo no se sobre ajuste a un solo tipo de datos, esto se puede hacer cambiando los valores de las zonas, o cambiando los valores de la matriz de fuentes.

* Se puede generar inputs con diferentes mallas de zonas, con diferentes valores de sigma_t y sigma_s, con diferentes valores de NR_X y con diferentes valores de XDOM.

* Se puede hacer variaciones en la matriz de fuentes, cambiando los valores de QMAP, o cambiando los valores de BC.

## Resolucion de problemas con los solvers

1. Todos los modelos son de 2-Dimensiones.

2. Definir una estrategia para escoger que tipo de solver se va a usar. Pudiera ser escogido aleatorio, o enfocarnos en alguno solo.
  Los solvers que tienen disponibles son (NTS_DD,NTS_LD, NTS_RM_CN, NTS_RM_LLN, NTS_STEP)
3. Los algoritmos estan fixados a un tipo de entrada en especifica, por ejemplo:
4. Hay que definir una estrategia para ver como creamos los datos sinteticos para el entrenamiento del modelo.
5. Estuve teniendo ahi una conversacion con ChatGPT y me gustaria saber su opinion sobre el tema [link_d_chat](https://chatgpt.com/share/69cacaac-51bc-83e9-9f7e-4f38e39aea58). En este chat hizo  unos comentarios bien interesantes sobre el abordaje del uso de una PINN para la resolucion del problema inicial. Entonces no se si modificar un poco ese primer enfoque que tuvo Ricardo y que fue lo que habiamos analizado en Cuba.

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
1e-05
```

Donde

```json
{
  "N": 4,              // Number of discrete ordinates (even)
  "NZ": 1,             // Number of material zones
  "zones": [
{
      "sigma_t": 0.5,  // Total cross-section
      "sigma_s": 0.3   // Scattering cross-section (must be < sigma_t)
    }
  ],
  "NR_X": 2,           // Number of X regions
  "XDOM": [            // X domain definition
    {"length": 10.0, "nodes": 5},
    {"length": 10.0, "nodes": 5}
  ],
  "NR_Y": 2,           // Number of Y regions
  "YDOM": [            // Y domain definition
    {"length": 10.0, "nodes": 5},
    {"length": 10.0, "nodes": 5}
  ],
  "ZMAP": [[1, 1], [1, 1]],            // Zone map (NR_Y x NR_X)
  "QMAP": [[1.0, 1.0], [1.0, 1.0]],    // Source map (NR_Y x NR_X)
  "BC": [0.0, 0.0, 0.0, 0.0],          // Boundary conditions [L,R,B,T]
  "TOL": 1e-5                          // Convergence tolerance
}
```

### Validacion de datos

Hasta estos momentos solo he podido validar los modelos de DD y STEP, los demas modelos no han podido ser validados por problemas con la convergencia, o por problemas con la implementacion de los algoritmos. Directamente los dejo calculando y se demoran mucho y no hay impllementado un logger en los modulos de C.

### Salida de los modelos

Todos los modelos dan este tipo de salida.

```json
{
  "STATUS": 0,
  "ITER": 38,
  "CPU": -9.8489400000e-01,
  "MFLUX": [
    [
      2.3081949488e+00,
      3.2673091558e+00,
      3.6615130536e+00,
      3.9095196811e+00,
      4.0400903858e+00,
      4.1009162642e+00,
      4.1025278964e+00,
      4.0316029707e+00,
      3.8883801484e+00,
      ...,
    ],
   "MFLOW": [
[
[ 9.5270533763e-01, 2.0645996455e+00, 2.2408557017e+00, 2.2691190000e+00, 2.2817772304e+00, 2.2832552974e+00, 2.2819324095e+00, 2.2695699136e+00, 2.2431057329e+00, 2.0787648274e+00 ],
[ 1.4894340699e+00, 3.6715831165e+00, 4.4717697524e+00, 4.6078681948e+00, 4.6454497183e+00, 4.6551047144e+00, 4.6517885846e+00, 4.6267568282e+00, 4.5666473910e+00, 4.2366590168e+00 ],
[ 1.3353434123e+00, 3.3575181806e+00, 4.3484122610e+00, 4.7169796246e+00, 4.7983883117e+00, 4.8188080503e+00, 4.8155048491e+00, 4.7862014435e+00, 4.7073460624e+00, 4.3465931420e+00 ],...,
  ]  
```

Y asi con Xflow , Yflow.
