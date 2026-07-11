"""
Configuracion del simulador de streaming ABR.

Define las estructuras de datos (dataclasses) que parametrizan una simulacion:
la escalera de bitrates, la geometria del buffer, la duracion de chunk y la
perturbacion de red.

Los valores por defecto reproducen el entorno del paper de Netflix
(Huang et al., "A Buffer-Based Approach to Rate Adaptation", SIGCOMM 2014):
buffer de 240 s, chunks de 4 s, 8 niveles de bitrate entre 235 kb/s y 3000 kb/s.

Todas las tasas estan en kb/s y los tiempos en segundos, de modo que
    tamano_chunk [kbit] = bitrate [kb/s] * duracion_chunk [s]
    tiempo_descarga [s] = tamano_chunk [kbit] / capacidad [kb/s]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# Escalera de bitrates por defecto (kb/s). 8 niveles, igual que en el paper/tp.md.
RATE_LADDER_DEFAULT: List[float] = [235, 375, 560, 750, 1050, 1750, 2350, 3000]


@dataclass
class NetworkConfig:
    """
    Parametros de la perturbacion externa: la capacidad de red C(t).

    modo selecciona la forma base de la senal; el resto de los campos la
    ajustan. Sobre cualquier modo se puede superponer ruido multiplicativo
    (ruido_amp) para emular la variabilidad fina observada en la practica.
    """

    modo: str = "escalon"          # constante | escalon | sinusoidal | cuadrada | muy_variable | corte
    nivel: float = 3000.0          # capacidad base (kb/s)
    # --- escalon (caida brusca, escenario de la Figura 4 del paper) ---
    nivel_alto: float = 5000.0     # capacidad antes de la caida (kb/s)
    nivel_bajo: float = 350.0      # capacidad despues de la caida (kb/s)
    t_caida: float = 25.0          # instante de la caida (s)
    # --- sinusoidal / cuadrada ---
    amplitud: float = 1500.0       # amplitud de la oscilacion (kb/s)
    periodo: float = 60.0          # periodo de la oscilacion (s)
    # --- muy_variable (traza tipo Figura 1: 500 kb/s .. 17 Mb/s) ---
    var_min: float = 500.0         # piso del rango variable (kb/s)
    var_max: float = 12000.0       # techo del rango variable (kb/s)
    # --- corte (outage temporal por debajo de Rmin) ---
    t_corte: float = 40.0          # inicio del corte (s)
    dur_corte: float = 25.0        # duracion del corte (s)
    nivel_corte: float = 100.0     # capacidad durante el corte (kb/s)
    # --- ruido comun a todos los modos ---
    ruido_amp: float = 0.0         # amplitud relativa del ruido (0..1)
    periodo_ruido: float = 4.0     # cada cuanto (s) se re-muestrea el ruido
    piso_capacidad: float = 50.0   # capacidad minima fisica (kb/s), nunca baja de aca
    seed: int = 42                 # semilla para reproducibilidad del ruido


@dataclass
class SimConfig:
    """Configuracion completa de una corrida de simulacion."""

    rate_ladder: List[float] = field(default_factory=lambda: list(RATE_LADDER_DEFAULT))
    buffer_max: float = 240.0          # capacidad del buffer B_max (s de video)
    duracion_chunk: float = 4.0        # V (s de video por chunk)
    duracion_video: float = 600.0      # largo del video a reproducir (s)
    # --- geometria del rate map de BBA-0 ---
    reservorio: float = 90.0           # r: zona baja donde se pide Rmin (s)
    upper_reservorio: float = 24.0     # zona alta: se alcanza Rmax en B_max - upper (s)
    red: NetworkConfig = field(default_factory=NetworkConfig)

    @property
    def r_min(self) -> float:
        return min(self.rate_ladder)

    @property
    def r_max(self) -> float:
        return max(self.rate_ladder)

    @property
    def cushion(self) -> float:
        """Tamano del cushion de BBA-0: rampa entre el reservorio y R_max."""
        return self.buffer_max - self.upper_reservorio - self.reservorio

    @property
    def n_chunks(self) -> int:
        return int(round(self.duracion_video / self.duracion_chunk))
