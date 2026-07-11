# Parámetros del simulador

Referencia de cada parámetro configurable, su rol dentro del sistema de control,
unidad, rango en la UI y valor por defecto. Está organizado igual que la barra
lateral de la aplicación ([app.py](app.py)); los valores por defecto viven en
[config.py](config.py).

Convención de unidades: **tasas en kb/s**, **tiempos y buffer en segundos**,
**tamaños de chunk en kbit**, de modo que:

```
tamaño_chunk [kbit] = bitrate [kb/s] × V [s]
tiempo_descarga [s] = tamaño_chunk [kbit] / capacidad [kb/s]
```

---

## 1. Escenario predefinido

| Parámetro | Qué hace |
|---|---|
| **Escenario predefinido** | Carga de golpe un conjunto de parámetros que ilustra un caso típico (caída brusca, red muy variable, oscilación, cortes periódicos, outage). Es un punto de partida: cualquier valor se puede seguir ajustando a mano. Elegí **Personalizado** para partir de cero. |

---

## 2. Red — la perturbación C(t)

La capacidad de red `C(t)` es la **entrada de perturbación** del lazo: el origen de
toda la variabilidad que el controlador debe rechazar. Es lo único que entra "desde
afuera" al sistema. El modo elige la *forma* de la señal; el resto de los campos la
ajustan.

### Modo de C(t)

| Modo | Descripción | Para qué sirve en el análisis |
|---|---|---|
| **constante** | Capacidad fija en el tiempo. | Caso ideal, sin perturbación: verifica el comportamiento en régimen permanente. |
| **escalon** | Salta de un nivel alto a uno bajo en un instante. | Muestra una caída brusca que hace fallar al Original. |
| **sinusoidal** | Oscila suavemente alrededor de un nivel medio. | Perturbación periódica y suave; muestra oscilación de la respuesta. |
| **cuadrada** | Alterna abruptamente entre alto y bajo. | Perturbación agresiva y repetida; el caso donde Original acumula rebuffers. |
| **muy_variable** | Salta al azar en un rango amplio (ej. 500 kb/s .. 12 Mb/s). | Throughput altamente variable. |
| **corte** | Capacidad normal con un outage temporal por debajo de Rmin. | Caso límite (Sección 7.1): cuando `C < Rmin` ni BBA puede evitar el rebuffer. |

### Parámetros según el modo

| Parámetro | Modo | Unidad | Rango UI | Defecto | Significado |
|---|---|---|---|---|---|
| **Nivel** | constante | kb/s | 200–12000 | 3000 | Capacidad fija. |
| **Capacidad antes de la caída** (`nivel_alto`) | escalon | kb/s | 500–12000 | 5000 | Capacidad inicial, antes del escalón. |
| **Capacidad después de la caída** (`nivel_bajo`) | escalon | kb/s | 100–5000 | 350 | Capacidad tras el escalón. |
| **Instante de la caída** (`t_caida`) | escalon | s | 5–300 | 25 | Momento del escalón. |
| **Nivel medio** (`nivel`) | sinusoidal / cuadrada | kb/s | 300–8000 | 1500 | Valor central de la oscilación. |
| **Amplitud** (`amplitud`) | sinusoidal / cuadrada | kb/s | 100–5000 | 1200 | Cuánto sube y baja respecto del nivel medio. |
| **Periodo** (`periodo`) | sinusoidal / cuadrada | s | 10–240 | 60 | Duración de un ciclo completo. |
| **Piso del rango** (`var_min`) | muy_variable | kb/s | 100–3000 | 500 | Menor capacidad posible. Si es **> Rmin**, BBA queda protegido. |
| **Techo del rango** (`var_max`) | muy_variable | kb/s | 2000–20000 | 12000 | Mayor capacidad posible. |
| **Re-muestreo** (`periodo_ruido`) | muy_variable | s | 1–20 | 4 | Cada cuántos segundos se sortea un nuevo valor. |
| **Nivel normal** (`nivel`) | corte | kb/s | 300–8000 | 2000 | Capacidad fuera del corte. |
| **Inicio del corte** (`t_corte`) | corte | s | 5–300 | 40 | Cuándo empieza el outage. |
| **Duración del corte** (`dur_corte`) | corte | s | 5–120 | 25 | Cuánto dura el outage. |
| **Capacidad durante el corte** (`nivel_corte`) | corte | kb/s | 0–500 | 100 | Capacidad durante el outage (típicamente **< Rmin**). |

### Ruido y reproducibilidad (todos los modos)

| Parámetro | Unidad | Rango UI | Defecto | Significado |
|---|---|---|---|---|
| **Ruido multiplicativo** (`ruido_amp`) | fracción | 0.0–0.8 | 0.0 | Superpone ruido a la señal base: la capacidad se multiplica por un factor en `[1−amp, 1+amp]` re-sorteado cada `periodo_ruido`. Emula la variabilidad fina real (interferencia WiFi, etc.). En 0 la señal es limpia. |
| **Semilla** (`seed`) | entero | 0–9999 | 42 | Fija la secuencia de ruido/variabilidad para que la corrida sea **reproducible**. |
| `piso_capacidad` (no editable en UI) | kb/s | — | 50 | Piso físico: la capacidad nunca baja de aquí, evita divisiones por casi cero. |

---

## 3. Contenido

| Parámetro | Unidad | Rango UI | Defecto | Significado |
|---|---|---|---|---|
| **Duración del video** (`duracion_video`) | s | 120–2400 | 600 | Largo del video a reproducir. Videos más largos diluyen el peso del arranque y acercan a BBA a su régimen permanente. |

---

## 4. Bitrates / tamaños de chunk

Estos parámetros definen la **señal de control cuantizada** (los niveles discretos
de bitrate) y, por lo tanto, los tamaños de chunk posibles.

| Parámetro | Unidad | Opciones | Defecto | Significado |
|---|---|---|---|---|
| **Escalera de bitrates** (`rate_ladder`) | kb/s | 4 presets | Netflix 8 niveles | Conjunto de calidades disponibles. El menor es **Rmin** (cota inferior de actuación) y el mayor **Rmax**. El default reproduce el del paper original: `235, 375, 560, 750, 1050, 1750, 2350, 3000`. |
| **Duración de chunk V** (`duracion_chunk`) | s | 2, 4, 6, 8, 10 | 4 | Segundos de video por fragmento. **El tamaño de chunk es `bitrate × V`**: subir V agranda todos los chunks (más inercia, decisiones más espaciadas). El paper original usa 4 s. |

> Presets de escalera disponibles: *Netflix (8 niveles, 235–3000)*, *HD extendida
> (235–5000)*, *Baja resolución (150–1500)*, *Pocos niveles (235–3000)*.

---

## 5. Buffer y geometría (BBA-0)

Definen el **proceso** (el buffer, que actúa como integrador) y la **geometría de la
ley de control** de BBA-0: dónde empieza y termina la rampa proporcional.

| Parámetro | Unidad | Rango UI | Defecto | Significado |
|---|---|---|---|---|
| **Buffer máximo** (`buffer_max`, `B_max`) | s | 60–300 | 240 | Capacidad del buffer de reproducción (la "carga" del sistema). El paper usa 240 s. Al llenarse, el cliente pausa la descarga. |
| **Reservorio** (`reservorio`, `r`) | s | 8–150 | 90 | Zona baja del buffer donde se pide siempre **Rmin** para recargar rápido. Absorbe la variación por chunk finito. Es el "setpoint" o frontera de seguridad. |
| **Reservorio superior** (`upper_reservorio`) | s | 0–60 | 24 | Margen arriba: la rampa alcanza **Rmax** en `B_max − upper` (con los defaults, a los 216 s = 90% del buffer), no justo en `B_max`. |

> El **cushion** (la rampa proporcional) no se configura directamente: se deduce
> como `cushion = B_max − reservorio − reservorio_superior`. Con los defaults da
> 126 s (entre 90 y 216 s). Sobre esa rampa se define la ganancia proporcional
> `Kp = (Rmax − Rmin) / cushion`.

---

## 6. Algoritmos a comparar

Selección múltiple de las leyes de control a simular en paralelo:

| Algoritmo | Rol |
|---|---|
| **Original** | El algoritmo anterior: estima la capacidad futura (media armónica del pasado) y pide el bitrate más alto que soporta. Se retrasa ante caídas → rebuffers innecesarios. |
| **BBA-0** | Rate map lineal por tramos + cuantizador con histéresis. Reservorio fijo. |
| **Rmin siempre** | Pide siempre Rmin: cota inferior de rebuffering, sirve de referencia. |
