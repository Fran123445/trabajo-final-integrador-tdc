"""
Metricas de calidad de experiencia (QoE) a partir de un SimResult.

Se calculan las mismas magnitudes que reporta el paper para comparar algoritmos:
    - rebuffers por hora de reproduccion (metrica principal del paper).
    - fraccion de tiempo en rebuffer (%).
    - bitrate medio entregado (kb/s) y bitrate medio en estado estable.
    - cantidad y frecuencia de cambios de bitrate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .config import SimConfig
from .simulator import SimResult


@dataclass
class Metricas:
    nombre: str
    rebuffers_por_hora: float
    rebuffer_pct: float
    n_rebuffers: int
    rebuffer_total_s: float
    bitrate_medio: float
    bitrate_estable: float          # excluye el arranque (primeros 2 min de video)
    cambios: int
    cambios_por_min: float


def calcular_metricas(res: SimResult, cfg: SimConfig,
                      arranque_s: float = 120.0) -> Metricas:
    horas = res.video_reproducido / 3600.0 if res.video_reproducido > 0 else 1e-9
    total = res.video_reproducido + res.rebuffer_total

    # Bitrate medio ponderado por tiempo de video (cada chunk aporta V segundos).
    bitrate_medio = sum(res.bitrate) / len(res.bitrate) if res.bitrate else 0.0

    # Bitrate en estado estable: chunks despues de los primeros ``arranque_s`` de video.
    V = cfg.duracion_chunk
    k_arranque = int(arranque_s / V)
    estables = res.bitrate[k_arranque:]
    bitrate_estable = sum(estables) / len(estables) if estables else bitrate_medio

    minutos = res.video_reproducido / 60.0 if res.video_reproducido > 0 else 1e-9

    return Metricas(
        nombre=res.nombre,
        rebuffers_por_hora=len(res.rebuffers) / horas,
        rebuffer_pct=100.0 * res.rebuffer_total / total if total > 0 else 0.0,
        n_rebuffers=len(res.rebuffers),
        rebuffer_total_s=res.rebuffer_total,
        bitrate_medio=bitrate_medio,
        bitrate_estable=bitrate_estable,
        cambios=res.cambios,
        cambios_por_min=res.cambios / minutos,
    )


def tabla_comparativa(metricas: List[Metricas],
                      referencia: str = "Original") -> List[Dict]:
    """
    Arma filas de tabla comparando cada algoritmo, normalizando el rebuffer al
    algoritmo de referencia (como en el paper: Original = 100%).
    """
    ref = next((m for m in metricas if m.nombre == referencia), None)
    ref_reb = ref.rebuffers_por_hora if ref and ref.rebuffers_por_hora > 0 else None
    ref_rate = ref.bitrate_medio if ref else None

    filas = []
    for m in metricas:
        reb_norm = (100.0 * m.rebuffers_por_hora / ref_reb) if ref_reb else float("nan")
        rate_delta = (m.bitrate_medio - ref_rate) if ref_rate is not None else float("nan")
        filas.append({
            "Algoritmo": m.nombre,
            "Rebuffers/hora": round(m.rebuffers_por_hora, 2),
            "Rebuffer %": round(m.rebuffer_pct, 2),
            "Rebuffer vs Original [%]": round(reb_norm, 1),
            "Bitrate medio [kb/s]": round(m.bitrate_medio, 0),
            "Bitrate estable [kb/s]": round(m.bitrate_estable, 0),
            "Δ Bitrate vs Original [kb/s]": round(rate_delta, 0),
            "Cambios/min": round(m.cambios_por_min, 2),
        })
    return filas
