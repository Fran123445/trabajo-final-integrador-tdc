"""
Algoritmos de adaptacion de bitrate (ABR) = la ley de control del lazo.

Cada algoritmo implementa seleccionar(estado) -> bitrate a partir del
EstadoDecision que le entrega el simulador antes de descargar cada chunk.

Se implementan:

    RminSiempre : cota inferior de rebuffer (siempre pide Rmin).
    Original    : el algoritmo anterior. Estima la capacidad futura a partir
                  del pasado reciente (media armonica) y pide el bitrate mas alto
                  que la estimacion soporta. Al estimar hacia atras, se retrasa
                  ante caidas bruscas -> sobreestima -> rebuffers innecesarios.
    BBA0        : basado en buffer. Rate map lineal por tramos + cuantizador con
                  histeresis (Algoritmo 1 del paper). Reservorio fijo de 90 s.

Convencion: bitrates en kb/s, tiempos y buffer en s, tamanos de chunk en kbit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .config import SimConfig


@dataclass
class EstadoDecision:
    """Todo lo que un algoritmo puede necesitar para elegir el proximo bitrate."""

    buffer: float                       # ocupacion actual B(t) en s
    bitrate_previo: float               # bitrate del chunk anterior (kb/s)
    k: int                              # indice del chunk a solicitar
    cfg: SimConfig
    throughput_hist: List[float]        # throughputs medidos de chunks previos (kb/s)


# ---------------------------------------------------------------------------
# Utilidades sobre la escalera de bitrates
# ---------------------------------------------------------------------------
def cuantizar_piso(valor: float, ladder: List[float]) -> float:
    """Mayor bitrate de la escalera <= valor (al menos Rmin)."""
    candidatos = [r for r in ladder if r <= valor]
    return max(candidatos) if candidatos else min(ladder)


def bitrate_superior(actual: float, ladder: List[float]) -> float:
    mayores = [r for r in ladder if r > actual]
    return min(mayores) if mayores else max(ladder)


def bitrate_inferior(actual: float, ladder: List[float]) -> float:
    menores = [r for r in ladder if r < actual]
    return max(menores) if menores else min(ladder)


# ---------------------------------------------------------------------------
# Clase base
# ---------------------------------------------------------------------------
class AlgoritmoABR:
    nombre = "ABR"

    def reset(self) -> None:
        """Reinicia el estado interno antes de una corrida."""

    def seleccionar(self, e: EstadoDecision) -> float:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Rmin siempre (cota inferior de rebuffering)
# ---------------------------------------------------------------------------
class RminSiempre(AlgoritmoABR):
    nombre = "Rmin siempre"

    def seleccionar(self, e: EstadoDecision) -> float:
        return e.cfg.r_min


# ---------------------------------------------------------------------------
# Original: estimacion de capacidad (el algoritmo anterior)
# ---------------------------------------------------------------------------
class Original(AlgoritmoABR):
    """
    ABR basado en estimacion de capacidad, R(t) = F(B)*Chat.

    Estima Chat como la media armonica de los ultimos ``ventana`` throughputs
    (estimador robusto habitual). La media armonica sigue mirando al pasado, por
    lo que ante una caida brusca de C(t) tarda varios chunks en "olvidar" la
    capacidad alta: mientras tanto pide chunks demasiado grandes y el buffer se
    vacia (mecanismo de la Figura 4 del paper). Un guardia de buffer bajo evita
    que quede atrapado en rebuffering perpetuo.
    """

    nombre = "Original"

    def __init__(self, ventana: int = 5, guardia_buffer: float = 8.0):
        self.ventana = ventana
        self.guardia_buffer = guardia_buffer

    def seleccionar(self, e: EstadoDecision) -> float:
        ladder = e.cfg.rate_ladder
        # Arranque: sin historia, arranca en la tasa minima (como slow-start).
        if not e.throughput_hist:
            return e.cfg.r_min

        muestras = e.throughput_hist[-self.ventana:]
        chat = len(muestras) / sum(1.0 / x for x in muestras)  # media armonica

        # Ajuste por buffer F(B): conservador con buffer bajo, neutro con buffer alto.
        if e.buffer < self.guardia_buffer:
            return e.cfg.r_min                       # panico: replegar a Rmin
        if e.buffer < 0.3 * e.cfg.buffer_max:
            factor = 0.9
        else:
            factor = 1.0

        return cuantizar_piso(factor * chat, ladder)


# ---------------------------------------------------------------------------
# BBA-0: rate map lineal por tramos + Algoritmo 1
# ---------------------------------------------------------------------------
class BBA0(AlgoritmoABR):
    """Rate map lineal por tramos con reservorio fijo y cuantizador con histeresis."""

    nombre = "BBA-0"

    def rate_map(self, B: float, cfg: SimConfig) -> float:
        """f(B) continua: Rmin en el reservorio, rampa lineal en el cushion, Rmax arriba."""
        r = cfg.reservorio
        cu = cfg.cushion
        if B <= r:
            return cfg.r_min
        if B >= r + cu:
            return cfg.r_max
        return cfg.r_min + (B - r) / cu * (cfg.r_max - cfg.r_min)

    def seleccionar(self, e: EstadoDecision) -> float:
        cfg = e.cfg
        ladder = cfg.rate_ladder
        r, cu = cfg.reservorio, cfg.cushion
        f = self.rate_map(e.buffer, cfg)
        return _algoritmo1(f, e.bitrate_previo, ladder, e.buffer, r, cu)


def _algoritmo1(f_val: float, previo: float, ladder: List[float],
                B: float, r: float, cu: float) -> float:
    """
    Algoritmo 1 del paper: cuantizador "pegajoso" (sticky).

    Se mantiene en el bitrate actual mientras f(B) no cruce el nivel discreto
    inmediatamente superior o inferior, evitando cambios erraticos.
    """
    r_min, r_max = min(ladder), max(ladder)
    rate_mas = r_max if previo >= r_max else bitrate_superior(previo, ladder)
    rate_menos = r_min if previo <= r_min else bitrate_inferior(previo, ladder)

    if B <= r:
        return r_min
    if B >= r + cu:
        return r_max
    if f_val >= rate_mas:
        return cuantizar_piso(f_val, ladder)          # subir
    if f_val <= rate_menos:
        menores = [x for x in ladder if x > f_val]     # bajar (min{Ri : Ri > f})
        return min(menores) if menores else r_min
    return previo                                      # zona muerta: mantener


# ---------------------------------------------------------------------------
# Registro de algoritmos disponibles para la UI
# ---------------------------------------------------------------------------
def algoritmos_disponibles():
    """Fabrica: nombre -> constructor de una instancia nueva."""
    return {
        "Original": Original,
        "BBA-0": BBA0,
        "Rmin siempre": RminSiempre,
    }
