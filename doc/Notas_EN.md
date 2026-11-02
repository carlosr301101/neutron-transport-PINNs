# Data batch creation

- A data batch is needed for the training stage. Multiple configurations can
  be generated and stored in the inputs folder, each with a different name.
- The data should be shifted slightly so the model does not overfit a single
  data type. This can be done by changing zone values or source-map values.
- Inputs can be generated with different zone meshes, different `sigma_t`
  and `sigma_s`, different `NR_X`, and different `XDOM`.
- Source-map variations are possible by changing `QMAP` or `BC`.

## Solver troubleshooting

1. All models are 2D.
2. Define a strategy for choosing the solver type. It may be random or
   focused on one solver. Available solvers: `NTS_DD`, `NTS_LD`,
   `NTS_RM_CN`, `NTS_RM_LLN`, `NTS_STEP`.
3. The algorithms are fixed to a specific input type, for example:
4. Define a strategy for creating synthetic training data.
5. There was a conversation with ChatGPT about using a PINN to solve the
   original problem. It raised interesting points about whether to modify
   the first approach proposed by Ricardo and analysed in Cuba.

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

Where:

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

### Data validation

So far only the DD and STEP models have been validated; the other models
could not be validated because of convergence or implementation problems.
They are simply left running for a long time, and no logger is implemented
in the C modules.

### Model output

All models produce this kind of output.

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

The same applies to `XFLOW` and `YFLOW`.

Original Spanish version: [Notas.md](Notas.md).
