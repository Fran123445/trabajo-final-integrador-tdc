"""
Demo por linea de comandos (sin UI): corre los algoritmos sobre varios escenarios
de red e imprime la tabla comparativa de metricas. Sirve como verificacion rapida
de que los resultados son coherentes con el paper.

Uso:
    python -m sim.run_demo
"""

from __future__ import annotations

import sys
from pathlib import Path

# Al ejecutar como script (`python sim/run_demo.py`) se reconstruye el contexto de
# paquete a partir del nombre real de la carpeta, para no depender de que se llame
# "sim". Con `python -m ...run_demo` __package__ ya viene seteado y esto se saltea.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = Path(__file__).resolve().parent.name

from .config import SimConfig, NetworkConfig
from .algorithms import algoritmos_disponibles
from .simulator import simular
from .metrics import calcular_metricas, tabla_comparativa


def correr_escenario(titulo: str, cfg: SimConfig, nombres):
    print("\n" + "=" * 78)
    print(titulo)
    print("=" * 78)
    fabrica = algoritmos_disponibles()
    metricas = []
    for nombre in nombres:
        algo = fabrica[nombre]()
        res = simular(algo, cfg)
        metricas.append(calcular_metricas(res, cfg))

    filas = tabla_comparativa(metricas)
    cols = ["Algoritmo", "Rebuffers/hora", "Rebuffer %", "Rebuffer vs Original [%]",
            "Bitrate medio [kb/s]", "Bitrate estable [kb/s]", "Cambios/min"]
    anchos = {c: max(len(c), *(len(str(f[c])) for f in filas)) for c in cols}
    print("  ".join(c.ljust(anchos[c]) for c in cols))
    for f in filas:
        print("  ".join(str(f[c]).ljust(anchos[c]) for c in cols))


def main():
    nombres = ["Original", "BBA-0", "Rmin siempre"]

    # 1) Caida brusca (escenario Figura 4): 5 Mb/s -> 350 kb/s a los 25 s.
    correr_escenario(
        "Escenario 1: caida brusca de capacidad (5 Mb/s -> 350 kb/s a los 25 s)",
        SimConfig(duracion_video=600,
                  red=NetworkConfig(modo="escalon", nivel_alto=5000,
                                    nivel_bajo=350, t_caida=25)),
        nombres,
    )

    # 2) Red muy variable (traza tipo Figura 1).
    correr_escenario(
        "Escenario 2: red muy variable (500 kb/s .. 12 Mb/s)",
        SimConfig(duracion_video=900,
                  red=NetworkConfig(modo="muy_variable", var_min=500,
                                    var_max=12000, periodo_ruido=4, seed=1)),
        nombres,
    )

    # 3) Oscilacion sinusoidal moderada con ruido.
    correr_escenario(
        "Escenario 3: capacidad sinusoidal (1500 +/- 1200 kb/s) con ruido",
        SimConfig(duracion_video=900,
                  red=NetworkConfig(modo="sinusoidal", nivel=1500, amplitud=1200,
                                    periodo=90, ruido_amp=0.2, seed=3)),
        nombres,
    )


if __name__ == "__main__":
    main()
