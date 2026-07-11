"""
Graficos (matplotlib) para la UI. Cada funcion arma y devuelve una figura.

Se mantienen deliberadamente simples y consistentes: una figura por concepto,
colores estables por algoritmo, para leer de un vistazo la comparacion
Original vs BBA.
"""

from __future__ import annotations

from typing import Dict, List

import matplotlib.pyplot as plt

from .config import SimConfig
from .network import NetworkTrace
from .simulator import SimResult
from .algorithms import BBA0

# Paleta estable por algoritmo.
COLORES = {
    "Original": "#d1495b",      # rojo
    "BBA-0": "#3d85c6",         # azul
    "Rmin siempre": "#7f7f7f",  # gris
}


def _color(nombre: str) -> str:
    return COLORES.get(nombre, "#333333")


def fig_capacidad_bitrate(resultados: Dict[str, SimResult], cfg: SimConfig):
    """Capacidad de red C(t) vs el bitrate elegido por cada algoritmo."""
    fig, ax = plt.subplots(figsize=(9, 4))

    # Traza de capacidad (referencia): tomada del primer resultado.
    primero = next(iter(resultados.values()))
    t_final = primero.tiempo[-1] if primero.tiempo else cfg.duracion_video
    red = NetworkTrace(cfg.red)
    ts, cs = red.sample(t_final, dt=0.5)
    ax.plot(ts, cs, color="#bbbbbb", lw=1.2, label="Capacidad C(t)", zorder=1)

    for nombre, res in resultados.items():
        ax.step(res.tiempo, res.bitrate, where="post", lw=1.8,
                color=_color(nombre), label=nombre, zorder=2)

    ax.axhline(cfg.r_min, ls=":", color="#999999", lw=1)
    ax.set_xlabel("Tiempo real (s)")
    ax.set_ylabel("kb/s")
    ax.set_title("Capacidad de red vs bitrate seleccionado")
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def fig_buffer(resultados: Dict[str, SimResult], cfg: SimConfig):
    """Ocupacion del buffer B(t); sombrea los intervalos de rebuffer."""
    fig, ax = plt.subplots(figsize=(9, 4))

    for nombre, res in resultados.items():
        ax.plot(res.tiempo, res.buffer, lw=1.8, color=_color(nombre), label=nombre)
        for (t0, dur) in res.rebuffers:
            ax.axvspan(t0, t0 + dur, color=_color(nombre), alpha=0.12)

    ax.axhline(cfg.reservorio, ls="--", color="#cc8800", lw=1,
               label=f"Reservorio ({cfg.reservorio:.0f}s)")
    ax.axhline(cfg.buffer_max, ls=":", color="#999999", lw=1,
               label=f"B_max ({cfg.buffer_max:.0f}s)")
    ax.set_xlabel("Tiempo real (s)")
    ax.set_ylabel("Buffer (s de video)")
    ax.set_title("Ocupacion del buffer (zonas sombreadas = rebuffer)")
    ax.legend(loc="lower right", fontsize=8, ncol=2)
    ax.set_ylim(bottom=0)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def fig_metricas_barras(filas: List[dict]):
    """Barras comparativas: rebuffers/hora y bitrate medio."""
    nombres = [f["Algoritmo"] for f in filas]
    reb = [f["Rebuffers/hora"] for f in filas]
    rate = [f["Bitrate medio [kb/s]"] for f in filas]
    colores = [_color(n) for n in nombres]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.6))

    ax1.bar(nombres, reb, color=colores)
    ax1.set_title("Rebuffers por hora (menor es mejor)")
    ax1.set_ylabel("rebuffers/h")
    ax1.tick_params(axis="x", rotation=30, labelsize=8)
    ax1.grid(axis="y", alpha=0.25)

    ax2.bar(nombres, rate, color=colores)
    ax2.set_title("Bitrate medio (mayor es mejor)")
    ax2.set_ylabel("kb/s")
    ax2.tick_params(axis="x", rotation=30, labelsize=8)
    ax2.grid(axis="y", alpha=0.25)

    fig.tight_layout()
    return fig


def fig_rate_map(cfg: SimConfig):
    """
    Rate map f(B) de BBA-0 con reservorio, cushion y frontera de seguridad.

    La frontera de seguridad (Seccion 3.2 del paper) es f(B) <= Rmin*(B - r)/V:
    cualquier mapa por debajo garantiza descargar un chunk antes de vaciar el buffer.
    """
    bba0 = BBA0()
    Bs = [i * cfg.buffer_max / 300 for i in range(301)]
    fs = [bba0.rate_map(B, cfg) for B in Bs]

    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(Bs, fs, color=COLORES["BBA-0"], lw=2.2, label="Rate map f(B)")

    # Frontera de seguridad.
    r, V = cfg.reservorio, cfg.duracion_chunk
    seg_b = [B for B in Bs if B > r]
    seg_f = [min(cfg.r_max * 1.2, cfg.r_min * (B - r) / V) for B in seg_b]
    ax.plot(seg_b, seg_f, ls="--", color="#d1495b", lw=1.5, label="Frontera de seguridad")

    # Niveles discretos de bitrate.
    for R in cfg.rate_ladder:
        ax.axhline(R, color="#dddddd", lw=0.8, zorder=0)

    ax.axvspan(0, r, color="#cc8800", alpha=0.10)
    ax.axvspan(r, r + cfg.cushion, color="#3d85c6", alpha=0.06)
    ax.axvspan(r + cfg.cushion, cfg.buffer_max, color="#2e8b57", alpha=0.08)
    ax.text(r / 2, cfg.r_max * 0.95, "reservorio", fontsize=8, ha="center", color="#996600")
    ax.text(r + cfg.cushion / 2, cfg.r_max * 0.5, "cushion", fontsize=8, ha="center", color="#22557a")

    ax.set_xlabel("Ocupacion del buffer B (s)")
    ax.set_ylabel("Bitrate (kb/s)")
    ax.set_title("Ley de control de BBA-0: rate map")
    ax.set_xlim(0, cfg.buffer_max)
    ax.set_ylim(0, cfg.r_max * 1.15)
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.15)
    fig.tight_layout()
    return fig
