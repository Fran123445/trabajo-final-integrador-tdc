"""
Generacion de la capacidad de red C(t): la perturbacion externa del lazo.

NetworkTrace traduce un NetworkConfig en una funcion capacity_at(t)
deterministica (dada la semilla). Ese es el unico bloque que introduce
variabilidad "desde afuera" al sistema de control.

Modos disponibles (perturbaciones):
    - constante     : capacidad fija (caso ideal, sin perturbacion).
    - escalon       : caida brusca de C en t_caida (escenario Figura 4 del paper).
    - sinusoidal    : oscilacion suave alrededor de un nivel.
    - cuadrada      : alternancia periodica alto/bajo.
    - muy_variable  : rango amplio 500 kb/s .. varios Mb/s (traza tipo Figura 1).
    - corte         : outage temporal por debajo de Rmin (Seccion 7.1 del paper).

Sobre cualquier modo se puede superponer ruido multiplicativo por tramos.
"""

from __future__ import annotations

import math
import random

from .config import NetworkConfig


class NetworkTrace:
    """Capacidad de red en funcion del tiempo, deterministica por semilla."""

    def __init__(self, cfg: NetworkConfig):
        self.cfg = cfg

    def capacity_at(self, t: float) -> float:
        """Capacidad instantanea C(t) en kb/s (t en segundos, t >= 0)."""
        base = self._base_profile(t)
        base *= self._noise_factor(t)
        return max(base, self.cfg.piso_capacidad)

    # ------------------------------------------------------------------ #
    # Forma base de la senal segun el modo elegido
    # ------------------------------------------------------------------ #
    def _base_profile(self, t: float) -> float:
        c = self.cfg
        modo = c.modo

        if modo == "constante":
            return c.nivel

        if modo == "escalon":
            return c.nivel_alto if t < c.t_caida else c.nivel_bajo

        if modo == "sinusoidal":
            return c.nivel + c.amplitud * math.sin(2 * math.pi * t / c.periodo)

        if modo == "cuadrada":
            fase = (t % c.periodo) / c.periodo
            return c.nivel + c.amplitud if fase < 0.5 else c.nivel - c.amplitud

        if modo == "muy_variable":
            # Muestra en escala logaritmica dentro de [var_min, var_max], re-muestreada
            # cada periodo_ruido segundos. Reproduce la enorme variabilidad de la Fig. 1.
            bucket = int(t // c.periodo_ruido)
            rng = random.Random((c.seed, "var", bucket).__hash__())
            lo, hi = math.log(c.var_min), math.log(c.var_max)
            return math.exp(lo + (hi - lo) * rng.random())

        if modo == "corte":
            if c.t_corte <= t < c.t_corte + c.dur_corte:
                return c.nivel_corte
            return c.nivel

        raise ValueError(f"Modo de red desconocido: {modo!r}")

    # ------------------------------------------------------------------ #
    # Ruido multiplicativo por tramos (comun a todos los modos)
    # ------------------------------------------------------------------ #
    def _noise_factor(self, t: float) -> float:
        amp = self.cfg.ruido_amp
        if amp <= 0:
            return 1.0
        bucket = int(t // self.cfg.periodo_ruido)
        rng = random.Random((self.cfg.seed, "noise", bucket).__hash__())
        # Factor uniforme en [1 - amp, 1 + amp]
        return 1.0 + amp * (2.0 * rng.random() - 1.0)

    # ------------------------------------------------------------------ #
    # Utilidad: muestrear la traza en una grilla (para graficar)
    # ------------------------------------------------------------------ #
    def sample(self, t_final: float, dt: float = 0.5):
        """Devuelve (tiempos, capacidades) muestreados hasta t_final."""
        n = int(t_final / dt) + 1
        ts = [i * dt for i in range(n)]
        cs = [self.capacity_at(t) for t in ts]
        return ts, cs
