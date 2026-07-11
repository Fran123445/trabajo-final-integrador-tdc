# Simulador de control ABR — Original vs BBA

Simulador del algoritmo de adaptación de bitrate (ABR) de Netflix modelado como un
**sistema de control de lazo cerrado**, para el TP de Teoría de Control. Compara el
**algoritmo anterior (Original**, basado en estimar la capacidad de red) contra el
enfoque **BBA (Buffer-Based Approach)** del paper de Huang et al. (SIGCOMM 2014).

## El sistema de control

| Bloque | En el simulador |
|---|---|
| **Proceso** | `simulator.py` — dinámica `dB/dt = C/R − 1` chunk a chunk |
| **Controlador** (ley de mapeo f(B)) | `algorithms.py` |
| **Perturbación externa** (capacidad de red C(t)) | `network.py` |
| **Realimentación** (ocupación del buffer, H = 1) | el propio lazo en `simulator.py` |

## Cómo ejecutar

Requiere Python 3.9+. Desde la carpeta del proyecto (la que contiene `sim/`):

```bash
pip install -r requirements.txt
streamlit run sim/app.py
```

Se abre en el navegador (por defecto http://localhost:8501). Desde la barra
lateral se cambian los parámetros y las gráficas/métricas se actualizan en vivo.

Para una verificación rápida por consola (sin UI):

```bash
python -m sim.run_demo
```

## Qué se puede configurar (barra lateral)

- **Red / perturbación:** modo de C(t) — constante, caída brusca (escalón),
  sinusoidal, onda cuadrada, muy variable, u outage — con sus parámetros y ruido.
- **Bitrates / tamaños de chunk:** escalera de bitrates y duración de chunk `V`
  (el tamaño de chunk es `bitrate × V`).
- **Buffer:** `B_max`, reservorio `r` y reservorio superior (geometría de BBA-0).
- **Algoritmos a comparar:** Original, BBA-0, Rmin siempre.

## Algoritmos

- **Original** — estima la capacidad futura (media armónica del pasado reciente) y
  pide el bitrate más alto que soporta. Al mirar hacia atrás, se retrasa ante
  caídas bruscas y provoca rebuffers innecesarios (mecanismo de la Fig. 4 del paper).
- **BBA-0** — rate map lineal por tramos + cuantizador con histéresis (Algoritmo 1).
- **Rmin siempre** — cota inferior de rebuffering (referencia).

## Estructura

```
sim/
  config.py       Configuración (dataclasses, escalera de bitrates, geometría).
  network.py      Capacidad de red C(t) — perturbación externa.
  algorithms.py   Leyes de control: Original, BBA-0, Rmin siempre.
  simulator.py    Motor de lazo cerrado (dinámica del buffer).
  metrics.py      Métricas de QoE y tabla comparativa.
  plots.py        Gráficas (matplotlib).
  app.py          UI en el navegador (Streamlit).
  run_demo.py     Demo por consola (sin UI).
```
