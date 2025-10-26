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
│       │   └── ...
│       ├── core/                  ← utilidades comunes (mixer, timeline, I/O)
│       ├── midi/loader.py         ← carga y parseo de archivos MIDI
│       └── ...
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
  pip install numpy scipy soundfile pyyaml
  ```
- (Opcional) `matplotlib` si querés generar espectrogramas.

---

## 🧱 Activar entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts ctivate
```

Luego instalá las dependencias:

```powershell
pip install numpy scipy soundfile pyyaml
```

---

## 🎼 Modo simple (una pista)

Renderiza un solo instrumento (por ejemplo guitarra nylon):

```powershell
python -m src.tpaudio.main --midi "melodia11.mid" --synth ks --preset nylon --preset-instruments "presets/instruments.yml" --out "melodia11_nylon.wav"
```

Opciones comunes:

| Argumento | Descripción |
|------------|--------------|
| `--midi` | Ruta al archivo `.mid` |
| `--synth` | Tipo de sintetizador (`ks`, `sample`, `additive`, `adsr`) |
| `--preset` | Nombre del preset dentro de `instruments.yml` |
| `--out` | Archivo WAV de salida |
| `--preset-instruments` | Ruta al YAML de presets |

---

## 🎚️ Modo avanzado (multiinstrumento)

El motor **`render_multi.py`** permite renderizar **1, 2 o más instrumentos simultáneamente**,  
asignando pistas MIDI específicas a cada instrumento.

### Formato de uso:

```
python -m src.tpaudio.render_multi --midi "C:\melodiax.mid" --inst "nombre:tipo:tracks" [--inst ...] --preset-instruments "presets/instruments.yml" --sample-dir "samples_piano_1" --out "archivo.wav"
```

- `nombre`: nombre del preset (por ejemplo `piano`, `nylon`, `bass`)
- `tipo`: tipo de síntesis (`sample`, `ks`, `additive`, etc.)
- `tracks`: canales o rango de canales MIDI (ej: `0,1,3-5`)

---

### 🪕 Ejemplos

#### 🎹 Solo piano (canales 0–15)
```powershell
python -m src.tpaudio.render_multi --midi "melodia13.mid" --inst "piano:sample:0-15" --preset-instruments "presets/instruments.yml" --sample-dir "samples_piano_1" --out "melodia13_piano_solo.wav"
```

#### 🎸 Solo bajo (canales 0–15)
```powershell
python -m src.tpaudio.render_multi --midi "melodia13.mid" --inst "bass:ks:0-15" --preset-instruments "presets/instruments.yml" --sample-dir "samples_piano_1" --out "melodia13_bajo_solo.wav"
```

#### 🎹 Piano + 🎸 Nylon + 🎸 Bajo
```powershell
python -m src.tpaudio.render_multi --midi "melodia13.mid" --inst "piano:sample:4,6,9" --inst "nylon:ks:0,2,3" --inst "bass:ks:7,8" --preset-instruments "presets/instruments.yml" --sample-dir "samples_piano_1" --out "melodia13_piano_nylon_bajo.wav"
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

---

## 🧪 Archivos de salida

- Los `.wav` se guardan en la raíz del proyecto.
- Todos normalizados a **-1 dBFS**.
- Duración y mezcla automática según el MIDI cargado.

---

## 📦 Créditos

Implementación desarrollada por **[Tu Nombre / Equipo]**,  
basada en la extensión del algoritmo **Karplus–Strong (Jaffe & Smith, 1983)**  
con mejoras de dispersión física y soporte multiinstrumento.

---

## 🪄 Tips

- Para probar una escala de prueba rápida:
  ```powershell
  python -m src.tpaudio.main --mode test-scale --synth ks --preset nylon --preset-instruments "presets/instruments.yml" --out "escala_nylon.wav"
  ```
- Podés listar los tracks del MIDI con:
  ```powershell
  python -m src.tpaudio.tools.list_midi_tracks "melodia13.mid"
  ```

---

🎧 **¡Listo!**  
Ahora podés generar mezclas completas de piano, guitarra y bajo  
directamente desde cualquier archivo MIDI.