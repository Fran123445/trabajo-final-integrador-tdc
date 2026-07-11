"""
Motor de simulacion en lazo cerrado.

Reproduce la dinamica del buffer chunk por chunk (el modelo discreto de la
Figura 11 del paper) haciendo interactuar tres piezas:

    controlador  -> AlgoritmoABR.seleccionar(): elige el bitrate del proximo chunk.
    proceso      -> el buffer de reproduccion, un integrador que se llena con V s
                    por chunk descargado y se vacia a tasa unitaria (1 s/s).
    perturbacion -> NetworkTrace: la capacidad C(t) durante cada descarga.

Modelo de cada chunk k (con B = ocupacion del buffer):
    tamano   = bitrate * V                             [kbit]
    t_desc   = tamano / C(t)                           [s]  (C muestreada al iniciar)
    - Mientras se descarga, la reproduccion drena el buffer t_desc segundos.
      Si el buffer se vacia antes, hay rebuffering (congelamiento) por el resto.
    - Al completarse, entran V s de video al buffer.
    - Si el buffer supera B_max, el cliente espera (patron ON-OFF).

El primer chunk modela el prebuffering inicial (join delay), no cuenta como
rebuffer. La reproduccion arranca una vez descargado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .algorithms import AlgoritmoABR, EstadoDecision
from .config import SimConfig
from .network import NetworkTrace


@dataclass
class SimResult:
    """Series temporales y datos crudos de una corrida (una por algoritmo)."""

    nombre: str
    # Series indexadas por chunk
    tiempo: List[float] = field(default_factory=list)        # tiempo real al completar el chunk (s)
    buffer: List[float] = field(default_factory=list)        # ocupacion tras agregar el chunk (s)
    bitrate: List[float] = field(default_factory=list)       # bitrate elegido (kb/s)
    capacidad: List[float] = field(default_factory=list)     # C(t) durante la descarga (kb/s)
    throughput: List[float] = field(default_factory=list)    # throughput medido (kb/s)
    # Eventos de rebuffer: lista de (tiempo, duracion)
    rebuffers: List[tuple] = field(default_factory=list)
    # Agregados
    rebuffer_total: float = 0.0        # s congelados
    video_reproducido: float = 0.0     # s de video efectivamente reproducidos
    cambios: int = 0                   # cantidad de cambios de bitrate


def simular(algo: AlgoritmoABR, cfg: SimConfig) -> SimResult:
    """Corre una simulacion completa para un algoritmo y devuelve su SimResult."""
    algo.reset()
    red = NetworkTrace(cfg.red)
    res = SimResult(nombre=algo.nombre)

    V = cfg.duracion_chunk
    B = 0.0                     # buffer (s)
    t = 0.0                     # tiempo real (s)
    throughput_hist: List[float] = []
    bitrate_previo = cfg.r_min

    for k in range(cfg.n_chunks):
        estado = EstadoDecision(
            buffer=B,
            bitrate_previo=bitrate_previo,
            k=k,
            cfg=cfg,
            throughput_hist=throughput_hist,
        )
        bitrate = algo.seleccionar(estado)

        tamano = bitrate * V                        # kbit
        cap = red.capacity_at(t)                    # kb/s
        t_desc = tamano / cap                       # s
        throughput = tamano / t_desc                # = cap (descarga a C constante)

        if k == 0:
            # Prebuffering inicial: no hay reproduccion todavia.
            B += V
        else:
            # Reproduccion durante la descarga (drena el buffer).
            if t_desc > B:
                congelado = t_desc - B
                res.rebuffers.append((t + B, congelado))
                res.rebuffer_total += congelado
                res.video_reproducido += B
                B = 0.0
            else:
                B -= t_desc
                res.video_reproducido += t_desc
            # Llega el chunk: entran V s de video.
            B += V

        t += t_desc

        # Control de nivel maximo: si el buffer se pasa, el cliente espera (ON-OFF).
        if B > cfg.buffer_max:
            espera = B - cfg.buffer_max
            res.video_reproducido += espera        # se sigue reproduciendo durante la espera
            B = cfg.buffer_max
            t += espera

        if k > 0 and bitrate != bitrate_previo:
            res.cambios += 1

        # Registro
        res.tiempo.append(t)
        res.buffer.append(B)
        res.bitrate.append(bitrate)
        res.capacidad.append(cap)
        res.throughput.append(throughput)

        # Actualizacion de la memoria para la proxima decision.
        throughput_hist.append(throughput)
        bitrate_previo = bitrate

    return res
