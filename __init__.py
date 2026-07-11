"""
Simulador de control ABR (Adaptive Bit Rate) basado en buffer.

Modela el ABR de Netflix como un sistema de control de lazo cerrado y compara el
algoritmo anterior (Original, basado en estimacion de capacidad) contra la familia
BBA (Buffer-Based Approach), siguiendo el paper de Huang et al. (SIGCOMM 2014).

Paquetes:
    config      : dataclasses de configuracion.
    network     : generacion de la capacidad de red C(t) (perturbacion externa).
    algorithms  : leyes de control (Original, BBA-0, Rmin siempre).
    simulator   : motor de lazo cerrado (dinamica del buffer).
    metrics     : metricas de QoE y tabla comparativa.
"""

from .config import SimConfig, NetworkConfig, RATE_LADDER_DEFAULT
from .algorithms import algoritmos_disponibles
from .simulator import simular, SimResult
from .metrics import calcular_metricas, tabla_comparativa, Metricas

__all__ = [
    "SimConfig",
    "NetworkConfig",
    "RATE_LADDER_DEFAULT",
    "algoritmos_disponibles",
    "simular",
    "SimResult",
    "calcular_metricas",
    "tabla_comparativa",
    "Metricas",
]
