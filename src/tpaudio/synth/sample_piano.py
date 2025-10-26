import os
import re
import numpy as np
import soundfile as sf
from typing import Optional, Dict, Any
from ..core.envelopes import adsr_env

# Ruta por defecto a tus samples
DEFAULT_SAMPLE_DIR = r"C:\Users\HP\Documents\ASSD\TP2\tp-audio-full-starter\samples_piano_1"

NOTE_MAP = {
    "C": 0, "C#": 1, "DB": 1,
    "D": 2, "D#": 3, "EB": 3,
    "E": 4,
    "F": 5, "F#": 6, "GB": 6,
    "G": 7, "G#": 8, "AB": 8,
    "A": 9, "A#": 10, "BB": 10,
    "B": 11,
}
NOTE_RE = re.compile(r'^([A-G](?:#|B)?)(-?\d)')

def _name_to_midi(filename: str) -> int:
    name = os.path.splitext(os.path.basename(filename))[0].upper()
    m = NOTE_RE.match(name)
    if not m:
        raise ValueError(f"No se pudo interpretar la nota en '{filename}'")
    note, octv = m.group(1), int(m.group(2))
    return 12 * (octv + 1) + NOTE_MAP[note]

def _vel_tag(filename: str) -> str:
    u = filename.upper()
    if "VH" in u: return "H"
    if "VL" in u: return "L"
    return "M"

def _resample_1d(y: np.ndarray, new_len: int) -> np.ndarray:
    if new_len <= 0: return np.zeros(1, dtype=np.float32)
    if len(y) == new_len: return y.astype(np.float32)
    x_old = np.linspace(0.0, 1.0, num=len(y))
    x_new = np.linspace(0.0, 1.0, num=new_len)
    return np.interp(x_new, x_old, y).astype(np.float32)

def load_samples(folder: Optional[str] = None):
    if folder is None:
        folder = DEFAULT_SAMPLE_DIR
    if not os.path.isdir(folder):
        raise RuntimeError(f"La carpeta no existe: {folder}")
    samples = {}
    for fname in os.listdir(folder):
        if not fname.lower().endswith(".wav"):
            continue
        path = os.path.join(folder, fname)
        try:
            midi = _name_to_midi(fname)
        except Exception:
            continue
        vel = _vel_tag(fname)
        data, sr = sf.read(path, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        samples.setdefault(midi, []).append((vel, data.astype(np.float32), int(sr)))
    if not samples:
        raise RuntimeError(f"No se encontraron .wav válidos en {folder}")
    print(f"[INFO] {len(samples)} notas cargadas desde {folder}")
    return samples

def render_note_sample(
    samples: dict,
    pitch: int,
    dur_s: float,
    velocity: int = 100,
    sr_out: int = 48000,
    adsr: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    base_pitch = min(samples.keys(), key=lambda k: abs(k - pitch))
    layers = samples[base_pitch]
    if velocity > 90:
        chosen = next((tpl for tpl in layers if tpl[0] == "H"), layers[0])
    else:
        chosen = next((tpl for tpl in layers if tpl[0] == "L"), layers[0])
    _, y, sr_samp = chosen
    ratio = 2 ** ((pitch - base_pitch) / 12.0)
    y = _resample_1d(y, max(1, int(len(y) / ratio)))
    y = y / (np.max(np.abs(y)) + 1e-9)
    N_out = int(dur_s * sr_out)
    y = y[:N_out] if len(y) >= N_out else np.pad(y, (0, N_out - len(y)))
    if adsr is None:
        adsr = dict(attack_ms=5, decay_ms=500, sustain=0.4, release_ms=300)
    env = adsr_env(sr_out, dur_s, **adsr)
    env = env[:len(y)]
    y *= env
    y *= float(velocity) / 127.0
    Lf = max(1, int(0.003 * sr_out))
    fade = np.linspace(0.0, 1.0, Lf, dtype=np.float32)
    y[:Lf] *= fade
    y[-Lf:] *= fade[::-1]
    y /= (np.max(np.abs(y)) + 1e-9)
    return y.astype(np.float32)
