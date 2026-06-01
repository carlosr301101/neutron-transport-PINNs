Ordem de quadratura $S_2$

Meio homogêneo

$\psi_1(x)$ - Letf-to-Right

$\psi_2(x)$ - Right-to-Left

Modelo

$\mu_1 \frac{d}{dx}\psi_1(x) + \sigma_{t}\psi_1(x) = \frac{1}{2}\sigma_{s0,i}\left( \psi_1(x)\omega_1 + \psi_2(x)\omega_2 \right)$

$\mu_2 \frac{d}{dx}\psi_2(x) + \sigma_{t}\psi_2(x) = \frac{1}{2}\sigma_{s0,i}\left( \psi_1(x)\omega_1 + \psi_2(x)\omega_2 \right)$

$\psi_1(0)$ = 1

$\psi_2(100)$ = 0

Parametros de quadratura

$\mu_{1,2} = \pm \frac{\sqrt(3)}{3}$

$\omega_{1,2} = 1$

Conjunto de treino 18 amostras 
|$s$  | $\sigma_{s0} $|
 --------------- | --------------- |
|1	| 0.10|
|2  | 0.15|
|3  | 0.20|
|4  | 0.25|
|...|...|
|17 |  0.90 |
|18 | 0.95	|

Condição de contorno fluxo incidente 
$\Psi_1 (0) = 1$
$\Psi_2(100) = 0$

Leitura dos detectores, fluxo escalar nos contornos

$ \phi(0) = \frac{1}{2} \left ( \psi_1 (0) * \omega_1 + \psi_2(0) * \omega(2) \right) $

$ \phi(100) = \frac{1}{2} \left ( \psi_1 (100) * \omega_1 + \psi_2(100) * \omega(2) \right) $

Conjunto de validação 32 amostras com valores aleatorios $ 0.1 \ge \sigma_{s0} \le 0.95$