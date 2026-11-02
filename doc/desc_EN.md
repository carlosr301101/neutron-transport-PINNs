# Reference 1D problem — S2 benchmark

Quadrature order $S_2$.

Homogeneous medium.

$\psi_1(x)$ — left-to-right.

$\psi_2(x)$ — right-to-left.

## Model

$$
\mu_1 \frac{d}{dx}\psi_1(x) + \sigma_{t}\psi_1(x)
= \frac{1}{2}\sigma_{s0,i}\left(\psi_1(x)\omega_1 + \psi_2(x)\omega_2\right)
$$

$$
\mu_2 \frac{d}{dx}\psi_2(x) + \sigma_{t}\psi_2(x)
= \frac{1}{2}\sigma_{s0,i}\left(\psi_1(x)\omega_1 + \psi_2(x)\omega_2\right)
$$

$$
\psi_1(0) = 1,\qquad \psi_2(100) = 0
$$

## Quadrature parameters

$$
\mu_{1,2} = \pm \frac{\sqrt{3}}{3},\qquad \omega_{1,2} = 1
$$

## Training set — 18 samples

| $s$ | $\sigma_{s0}$ |
|---|---|
| 1 | 0.10 |
| 2 | 0.15 |
| 3 | 0.20 |
| 4 | 0.25 |
| ... | ... |
| 17 | 0.90 |
| 18 | 0.95 |

## Incoming-flux boundary condition

$$
\Psi_1(0) = 1,\qquad \Psi_2(100) = 0
$$

## Detector readings — scalar flux at the boundaries

$$
\phi(0) = \frac{1}{2}\left(\psi_1(0)\omega_1 + \psi_2(0)\omega_2\right)
$$

$$
\phi(100) = \frac{1}{2}\left(\psi_1(100)\omega_1 + \psi_2(100)\omega_2\right)
$$

## Validation set — 32 random samples

$$
0.1 \le \sigma_{s0} \le 0.95
$$

Original Portuguese version: [desc.md](desc.md).
