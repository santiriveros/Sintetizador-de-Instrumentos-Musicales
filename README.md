# 🎶 TP Audio – Síntesis y Renderización Multiinstrumento

Proyecto para la materia **Análisis y Síntesis de Sistemas Digitales (ASSD)**  
Instituto Tecnológico de Buenos Aires (ITBA)

Implementación completa del motor de síntesis **Karplus–Strong extendido (fracDelay + stiffness)**,  
con soporte para **síntesis aditiva**, **reproducción por samples**, y **renderización multiinstrumento** desde archivos MIDI.

---

## 🧩 Estructura principal

```
tp-audio-full-starter/
│
├── src/
│   └── tpaudio/
│       ├── main.py                ← modo simple (una pista)
│       ├── render_multi.py        ← modo avanzado (multiinstrumentos)
│       ├── synth/
│       │   ├── karplus.py         ← motor Karplus–Strong físico
│       │   ├── sample_piano.py    ← motor de reproducción por muestras
│       │   ├── additive.py        ← síntesis aditiva
│       │   └── adsr.py            ← algoritmo ADSR exponencial
│       ├── core/                  ← utilidades comunes (mixer, timeline, I/O)
│       ├── midi/loader.py         ← carga y parseo de archivos MIDI
│       └── gui.py                 ← interfaz grafica
│
├── presets/
│   └── instruments.yml            ← parámetros de instrumentos
│
├── samples_piano_1/               ← muestras WAV del piano real
│   └── *.wav
│
├── melodiaX.mid                   ← archivos MIDI de prueba
│
└── README.md                      ← este documento
```

---

## ⚙️ Requisitos

- **Python 3.9+**
- Librerías necesarias:
  ```bash
  pip install numpy scipy soundfile pyyaml mido
  ```
- (Opcional) `matplotlib` si querés generar espectrogramas.

---

## 🧱 Activar entorno virtual

```powershell
- Primero:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
- Segundo:
.venv\Scripts\Activate.ps1
```

Luego instalá las dependencias dentro del entorno:

```powershell
pip install numpy scipy soundfile pyyaml mido
```

---

## 🎛️ Parámetros de instrumentos (YAML)

Definidos en `presets/instruments.yml`:

```yaml
ks:
  nylon:
    rho: 0.9965
    pick_pos: 0.18
    S: 0.45
    noise_mix: 0.02
    stiffness: 0.001
    transpose: 0

  bass:
    rho: 0.9985
    pick_pos: 0.08
    S: 0.55
    noise_mix: 0.015
    stiffness: 0.002
    transpose: 0
```

Cada parámetro controla:
- `rho`: amortiguamiento (sustain)
- `S`: suavizado tonal (filtro post-lazo)
- `pick_pos`: posición de púa (ataque)
- `stiffness`: rigidez física de la cuerda
- `noise_mix`: textura inicial
- `transpose`: cambio de octava (opcional)

```yaml
drums:
  kick_fuerte:
      kind: additive
      params:
        dur_s: 0.35
        f_start_hz: 150.0
        f_end_hz: 50.0
        tau_freq_ms: 22.0
        amps: [1.5, 0.75, 0.4, 0.2, 0.15]
        ratios: [1.0, 1.6, 2.3, 3.5, 4.2]
        tau_amp_ms: [120, 90, 70, 55, 45]
        click_ms: 8.0
        click_mix: 0.15
        hp_hz: 22.0
        drive: 2.0
```

Cada parámetro controla:
- `dur_s`: duración total del sonido del golpe (en segundos).
- `f_start_hz`: frecuencia inicial del oscilador (pitch al inicio del golpe).
- `f_end_hz`: frecuencia final del oscilador (pitch al final del golpe).
- `tau_freq_ms`: constante de tiempo (en milisegundos) del decaimiento exponencial del pitch.
- `ratios`: relación de frecuencias de los parciales armónicos que se suman a la fundamental.
- `amps`: amplitud relativa de cada parcial de ratios.
- `tau_amp_ms`: constante de decaimiento (en milisegundos) de la amplitud de cada parcial.
- `click_ms`: duración del pulso de ruido blanco inicial (en milisegundos).
- `click_mix`: mezcla relativa del ruido inicial con el cuerpo del sonido (0–1).
→ Controla cuánta energía del click se mezcla.
→ Valores altos → golpe más punzante y agresivo.
-`drive`: factor de distorsión suave aplicado a la señal final.
→ Realza armónicos y compresión.
→ Valores > 1.0 generan saturación tipo overdrive.
-`hp_hz`: frecuencia de corte del filtro pasa-altos (high-pass) aplicado al final.
→ Elimina graves muy bajos o DC offset.
→ Subirlo aclara el sonido; bajarlo lo hace más “profundo”.

---

## 🧪 Archivos de salida

- Los `.wav` se guardan en la raíz del proyecto.
- Todos normalizados a **-1 dBFS**.
- Duración y mezcla automática según el MIDI cargado.


## Uso del programa:

1. Dale a compilar al archivo gui.py.
2. Al abrirse la ventana emergente selecciona un archivo midi sobre el cual trabajar.
3. Selecciona que instumentos y con cuales presets pertenecen en cada pista.
4. Escoge efectos a gusto para agregarle al sonido de salida en su totalidad.
5. Crea el archivo .wav y/o al espectograma de tu salida. 

---

🎧 **¡Listo!**  
Ahora podés generar mezclas completas de piano, guitarra, bajo y drums.  
directamente desde cualquier archivo MIDI.