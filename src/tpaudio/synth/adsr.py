# src/tpaudio/synth/adsr.py
import numpy as np
from typing import Optional, Dict, Any
from ..core.dsp import midi2freq
from ..core.envelopes import adsr_env


def _waveform(f0: float, dur_s: float, sr: int, waveform: str = "sine") -> np.ndarray:
    """
    Genera una forma de onda básica band-limited:
    - 'sine'    → senoidal pura
    - 'square'  → armónicos impares (1/k)
    - 'saw'     → armónicos 1/k
    - 'additive'→ parciales 1..5 por defecto
    """
    N = int(sr * dur_s)
    t = np.arange(N, dtype=np.float32) / sr
    y = np.zeros(N, dtype=np.float32)

    if waveform == "sine":
        return np.sin(2 * np.pi * f0 * t, dtype=np.float32)

    if waveform == "square":
        k = 1
        while True:
            fk = k * f0
            if fk >= sr / 2:
                break
            y += (1.0 / k) * np.sin(2 * np.pi * fk * t, dtype=np.float32)
            k += 2
        y /= (np.max(np.abs(y)) + 1e-9)
        return y

    if waveform == "saw":
        k = 1
        sign = 1.0
        while True:
            fk = k * f0
            if fk >= sr / 2:
                break
            y += (sign / k) * np.sin(2 * np.pi * fk * t, dtype=np.float32)
            k += 1
            sign *= -1.0
        y /= (np.max(np.abs(y)) + 1e-9)
        return y

    # 'additive' por defecto
    partials = [1, 2, 3, 4, 5]
    amps = [1.0, 0.6, 0.4, 0.25, 0.15]
    for k, a in zip(partials, amps):
        fk = k * f0
        if fk >= sr / 2:
            continue
        y += a * np.sin(2 * np.pi * fk * t, dtype=np.float32)
    y /= (np.max(np.abs(y)) + 1e-9)
    return y


def render_note_adsr(
    pitch: int,
    dur_s: float,
    velocity: int,
    sr: int = 48000,
    waveform: str = "additive",
    adsr: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """
    Sintetizador ADSR genérico:
      1) Oscilador (sine/square/saw/additive)
      2) Envolvente ADSR
      3) Escala por velocity
      4) Fades cortos + normalización
    """
    f0 = midi2freq(pitch)
    y = _waveform(f0, dur_s, sr, waveform=waveform)

    # velocity
    y *= float(velocity) / 127.0

    # ADSR (por defecto tipo “piano simple”)
    if adsr is None:
        adsr = {"attack_ms": 2, "decay_ms": 900, "sustain": 0.0, "release_ms": 200}

    env = adsr_env(
        sr,
        dur_s,
        attack_ms=adsr.get("attack_ms", 2),
        decay_ms=adsr.get("decay_ms", 900),
        sustain=adsr.get("sustain", 0.0),
        release_ms=adsr.get("release_ms", 200),
    )
    env = env[: len(y)]
    y *= env

    # fades anti-click
    Lf = max(1, int(0.004 * sr))
    Lf = min(Lf, len(y))
    fade = np.linspace(0, 1, Lf, dtype=np.float32)
    y[:Lf] *= fade
    y[-Lf:] *= fade[::-1]

    # normalizar
    y /= (np.max(np.abs(y)) + 1e-9)
    return y.astype(np.float32)
