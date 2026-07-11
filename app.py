"""
UI en el navegador (Streamlit) del simulador de control ABR.

Permite configurar la red (perturbacion), la escalera de bitrates
(tamanos de chunk) y la geometria del buffer, y compara en vivo el algoritmo
anterior (Original) contra la familia BBA mostrando graficos y metricas.

Ejecutar desde la carpeta del proyecto:
    streamlit run sim/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Al ejecutar como script (`streamlit run sim/app.py`) se reconstruye el contexto de
# paquete a partir del nombre real de la carpeta, para no depender de que se llame
# "sim" y que los imports relativos funcionen igual.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = Path(__file__).resolve().parent.name

import streamlit as st

from .config import SimConfig, NetworkConfig, RATE_LADDER_DEFAULT
from .algorithms import algoritmos_disponibles
from .simulator import simular
from .metrics import calcular_metricas, tabla_comparativa
from . import plots


# --------------------------------------------------------------------------- #
# Presets de escalera de bitrates (definen los tamanos de chunk = bitrate * V).
# --------------------------------------------------------------------------- #
LADDERS = {
    "Netflix (8 niveles, 235..3000)": [235, 375, 560, 750, 1050, 1750, 2350, 3000],
    "HD extendida (235..5000)": [235, 560, 1050, 1750, 2350, 3000, 4300, 5000],
    "Baja resolucion (150..1500)": [150, 300, 500, 750, 1050, 1500],
    "Pocos niveles (235..3000)": [235, 750, 1750, 3000],
}

PRESETS = {
    "Caida brusca (Fig. 4 del paper)": dict(
        modo="escalon", nivel_alto=5000, nivel_bajo=350, t_caida=25,
        duracion_video=600),
    "Red muy variable (Fig. 1)": dict(
        modo="muy_variable", var_min=500, var_max=12000, periodo_ruido=4,
        duracion_video=900),
    "Oscilacion sinusoidal": dict(
        modo="sinusoidal", nivel=1500, amplitud=1200, periodo=90, ruido_amp=0.2,
        duracion_video=900),
    "Cortes periodicos (onda cuadrada)": dict(
        modo="cuadrada", nivel=3150, amplitud=2850, periodo=40, ruido_amp=0.15,
        duracion_video=1200),
    "Outage / corte de red": dict(
        modo="corte", nivel=2000, t_corte=40, dur_corte=25, nivel_corte=100,
        duracion_video=600),
    "Personalizado": {},
}


st.set_page_config(page_title="Simulador ABR – Original vs BBA", layout="wide")
st.title("Simulador de control ABR: algoritmo anterior (Original) vs BBA")
st.caption(
    "Modelo de lazo cerrado del ABR de Netflix. El buffer de reproduccion es el "
    "proceso (integrador); la ley de control elige el bitrate; la capacidad de red "
    "C(t) es la perturbacion externa. Basado en Huang et al., SIGCOMM 2014."
)


# --------------------------------------------------------------------------- #
# Barra lateral: configuracion
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("Configuracion")

    preset_nombre = st.selectbox("Escenario predefinido", list(PRESETS.keys()))
    preset = PRESETS[preset_nombre]

    st.subheader("Red (perturbacion externa)")
    modos = ["constante", "escalon", "sinusoidal", "cuadrada", "muy_variable", "corte"]
    modo = st.selectbox("Modo de C(t)", modos,
                        index=modos.index(preset.get("modo", "escalon")))

    red = NetworkConfig(modo=modo)
    if modo == "constante":
        red.nivel = st.slider("Nivel (kb/s)", 200, 12000, int(preset.get("nivel", 3000)), 50)
    elif modo == "escalon":
        red.nivel_alto = st.slider("Capacidad antes de la caida (kb/s)", 500, 12000,
                                   int(preset.get("nivel_alto", 5000)), 100)
        red.nivel_bajo = st.slider("Capacidad despues de la caida (kb/s)", 100, 5000,
                                   int(preset.get("nivel_bajo", 350)), 50)
        red.t_caida = st.slider("Instante de la caida (s)", 5, 300,
                               int(preset.get("t_caida", 25)), 5)
    elif modo in ("sinusoidal", "cuadrada"):
        red.nivel = st.slider("Nivel medio (kb/s)", 300, 8000, int(preset.get("nivel", 1500)), 50)
        red.amplitud = st.slider("Amplitud (kb/s)", 100, 5000, int(preset.get("amplitud", 1200)), 50)
        red.periodo = st.slider("Periodo (s)", 10, 240, int(preset.get("periodo", 60)), 5)
    elif modo == "muy_variable":
        red.var_min = st.slider("Piso del rango (kb/s)", 100, 3000, int(preset.get("var_min", 500)), 50)
        red.var_max = st.slider("Techo del rango (kb/s)", 2000, 20000, int(preset.get("var_max", 12000)), 500)
        red.periodo_ruido = st.slider("Re-muestreo (s)", 1, 20, int(preset.get("periodo_ruido", 4)), 1)
    elif modo == "corte":
        red.nivel = st.slider("Nivel normal (kb/s)", 300, 8000, int(preset.get("nivel", 2000)), 50)
        red.t_corte = st.slider("Inicio del corte (s)", 5, 300, int(preset.get("t_corte", 40)), 5)
        red.dur_corte = st.slider("Duracion del corte (s)", 5, 120, int(preset.get("dur_corte", 25)), 5)
        red.nivel_corte = st.slider("Capacidad durante el corte (kb/s)", 0, 500,
                                    int(preset.get("nivel_corte", 100)), 10)

    red.ruido_amp = st.slider("Ruido multiplicativo (+/- frac.)", 0.0, 0.8,
                              float(preset.get("ruido_amp", 0.0)), 0.05)
    red.seed = st.number_input("Semilla (reproducibilidad)", 0, 9999, 42, 1)

    st.subheader("Contenido")
    duracion_video = st.slider("Duracion del video (s)", 120, 2400,
                               int(preset.get("duracion_video", 600)), 60)

    st.subheader("Bitrates / tamanos de chunk")
    ladder_nombre = st.selectbox("Escalera de bitrates", list(LADDERS.keys()))
    rate_ladder = LADDERS[ladder_nombre]
    duracion_chunk = st.select_slider("Duracion de chunk V (s)", options=[2, 4, 6, 8, 10], value=4)
    st.caption(
        "Tamano de chunk = bitrate x V. "
        f"Con V={duracion_chunk}s: chunk minimo ~ {min(rate_ladder)*duracion_chunk:.0f} kbit, "
        f"maximo ~ {max(rate_ladder)*duracion_chunk:.0f} kbit."
    )

    st.subheader("Buffer y geometria (BBA-0)")
    buffer_max = st.slider("Buffer maximo B_max (s)", 60, 300, 240, 10)
    reservorio = st.slider("Reservorio r (s)", 8, 150, 90, 2)
    upper_reservorio = st.slider("Reservorio superior (s)", 0, 60, 24, 2)

    st.subheader("Algoritmos a comparar")
    disponibles = list(algoritmos_disponibles().keys())
    seleccionados = st.multiselect("Seleccionar", disponibles,
                                   default=["Original", "BBA-0", "Rmin siempre"])


# --------------------------------------------------------------------------- #
# Armado de la configuracion y ejecucion de las simulaciones
# --------------------------------------------------------------------------- #
cfg = SimConfig(
    rate_ladder=list(rate_ladder),
    buffer_max=float(buffer_max),
    duracion_chunk=float(duracion_chunk),
    duracion_video=float(duracion_video),
    reservorio=float(reservorio),
    upper_reservorio=float(upper_reservorio),
    red=red,
)

if not seleccionados:
    st.warning("Elegi al menos un algoritmo en la barra lateral.")
    st.stop()

fabrica = algoritmos_disponibles()
resultados = {}
metricas = []
for nombre in seleccionados:
    res = simular(fabrica[nombre](), cfg)
    resultados[nombre] = res
    metricas.append(calcular_metricas(res, cfg))

filas = tabla_comparativa(metricas)


# --------------------------------------------------------------------------- #
# Panel principal: metricas + graficos
# --------------------------------------------------------------------------- #
st.subheader("Metricas comparativas")
st.dataframe(filas, width="stretch", hide_index=True)

# Resumen tipo "titular" del paper cuando estan Original y algun BBA.
original = next((m for m in metricas if m.nombre == "Original"), None)
if original:
    cols = st.columns(len([m for m in metricas if m.nombre.startswith("BBA")]) or 1)
    i = 0
    for m in metricas:
        if not m.nombre.startswith("BBA"):
            continue
        if original.rebuffers_por_hora > 0:
            delta_reb = 100.0 * (m.rebuffers_por_hora - original.rebuffers_por_hora) / original.rebuffers_por_hora
            reb_txt = f"{delta_reb:+.0f}% rebuffer"
        else:
            reb_txt = "sin rebuffer" if m.rebuffers_por_hora == 0 else "Original sin rebuffer"
        with cols[i % len(cols)]:
            st.metric(
                label=f"{m.nombre} vs Original",
                value=f"{m.bitrate_medio - original.bitrate_medio:+.0f} kb/s",
                delta=reb_txt,
                delta_color="off",
            )
        i += 1

col1, col2 = st.columns(2)
with col1:
    st.pyplot(plots.fig_capacidad_bitrate(resultados, cfg))
with col2:
    st.pyplot(plots.fig_buffer(resultados, cfg))

st.pyplot(plots.fig_metricas_barras(filas))

with st.expander("Ver la ley de control de BBA-0 (rate map)"):
    st.pyplot(plots.fig_rate_map(cfg))
    st.markdown(
        "- **Reservorio** (naranja): con buffer bajo se pide siempre R_min para "
        "recargar rapido.\n"
        "- **Cushion** (azul): rampa proporcional; el bitrate crece con el buffer "
        "(actua como un controlador proporcional con ganancia Kp = (Rmax−Rmin)/cushion).\n"
        "- **Frontera de seguridad** (rojo): cualquier mapa por debajo garantiza "
        "descargar un chunk antes de vaciar el buffer si C(t) ≥ R_min."
    )

st.caption(
    "Nota: los resultados reproducen los hallazgos cualitativos del paper — BBA "
    "elimina rebuffers innecesarios cuando C(t) ≥ R_min y reduce fuertemente los "
    "cambios de calidad, a cambio de un bitrate algo menor que el del Original. "
    "Las magnitudes exactas dependen del escenario configurado."
)
