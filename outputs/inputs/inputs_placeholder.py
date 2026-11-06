config_dict = {
    "num_regions": 1,
    "num_zones": 1,
    "NC": [101],
    "HR": [20],
    "IZL": [1],
    "SCT": [1.0],
    "SCS": [kk],
    "NU_SIGF": [0.0],       # nu*Sigma_f [cm^-1] por zona; 0 = sin fisión
    "Q": [0],
    "N": 8,
    "SPATIAL_SCHEME": "DD",  # DD | STEP | SC
    "reflex_izq": False,
    "reflex_der": False,
    "bound_left": [1, 1, 1, 1],
    "bound_right": [0, 0, 0, 0],
    "MODE": "fixed_source",  # fixed_source | eigenvalue | fixed_k | driven
}

# Para el benchmark multiplicativo de 20 cm (vacío, sigma_t=1.0,
# sigma_s=0.9, nu*Sigma_f=0.11), usa:
#   "NU_SIGF": [0.11], "MODE": "eigenvalue",
#   "Q": [0], "bound_left": [0]*4, "bound_right": [0]*4
#
# Opcionales del modo multiplicativo:
#   "K_EFF": 1.0,       # solo fixed_k (driven fuerza k=1)
#   "TOL_K": 1e-6,
#   "MAX_OUTER": 200,
#   "K0": 1.1,
#   "POWER_KW": 10.0,   # activa la normalización de potencia
#   "E_F_MEV": 200.0,
#   "NU": 2.4,          # o usa "SIGMA_F": [0.045833]
#   "AREA_CM2": 1.0,
