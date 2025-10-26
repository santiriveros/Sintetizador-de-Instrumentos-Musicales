import numpy as np
from ..core.dsp import midi2freq
from scipy.signal import lfilter


def _ks_basic(f0: float, dur_s: float, sr: int,
              rho: float = 0.998,
              pick_pos: float = 0.20,
              noise_mix: float = 0.02,
              stiffness: float = 0.0) -> np.ndarray:
    """
    Karplus–Strong extendido:
      - Delay fraccional (afinación precisa)
      - Filtro de pérdida (rho)
      - Filtro de dispersión física (stiffness)
      - Excitación por pick_position + forma triangular determinista
    """
    if f0 <= 0:
        return np.zeros(int(sr * dur_s), dtype=np.float32)

    # Longitud fraccional del delay
    N_exact = sr / f0
    N_int = int(np.floor(N_exact))
    frac = N_exact - N_int
    L = max(2, N_int)
    Nsamp = int(sr * dur_s)

    # Excitación determinista + pick position
    buf = np.linspace(1.0, -1.0, L, dtype=np.float32)
    M = max(1, min(L - 1, int(round(pick_pos * L))))
    buf = buf - np.roll(buf, M)

    if noise_mix > 0:
        buf += noise_mix * np.random.randn(L).astype(np.float32)
    buf /= (np.max(np.abs(buf)) + 1e-9)

    # Coeficiente del filtro de rigidez (stiffness)
    a_stiff = float(np.clip(stiffness, 0.0, 0.02))  # valores típicos: 0.001–0.01

    # Bucle KS extendido con interpolación fraccional + dispersión
    y = np.zeros(Nsamp, dtype=np.float32)
    i = 0
    for n in range(Nsamp):
        y[n] = buf[i]

        # Interpolación fraccional
        i_prev = (i - 1) % L
        i_prev2 = (i - 2) % L
        frac_sample = (1 - frac) * buf[i_prev] + frac * buf[i_prev2]

        # Filtro dispersivo (1 + a z^-1) / (1 - a z^-1)
        disp_sample = (1 + a_stiff) * frac_sample - a_stiff * buf[i_prev]

        # Promedio + pérdida + dispersión
        buf[i] = rho * 0.5 * (buf[i] + disp_sample)

        i = (i + 1) % L

    return y


def render_note_ks(pitch: int, dur_s: float, velocity: int,
                   sr: int = 48000,
                   rho: float = 0.998,
                   S: float = 0.50,
                   pick_pos: float = 0.20,
                   noise_mix: float = 0.02,
                   stiffness: float = 0.0,
                   preset_name: str = None) -> np.ndarray:
    """
    Karplus–Strong extendido con dispersión (stiffness) y afinación fraccional.
    """
    f0 = midi2freq(pitch)
    y = _ks_basic(f0, dur_s, sr, rho=rho,
                  pick_pos=pick_pos,
                  noise_mix=noise_mix,
                  stiffness=stiffness)

    # Escala por velocidad MIDI
    y *= (velocity / 127.0)

    # Filtro de cuerpo según preset
    if preset_name == "nylon":
        b = [0.005, 0.0, -0.004, 0.0, 0.003]
        a = [1.0, -0.95, 0.90, -0.70, 0.50]
        y = lfilter(b, a, y).astype(np.float32)
    elif preset_name == "steel":
        b = [0.006, -0.002, 0.0015]
        a = [1.0, -0.92, 0.85]
        y = lfilter(b, a, y).astype(np.float32)
    elif preset_name == "bass":
        b = [0.004, 0.0035, 0.002]
        a = [1.0, -0.96, 0.94]
        y = lfilter(b, a, y).astype(np.float32)
    elif preset_name == "banjo":
        b = [0.01, -0.004, 0.002]
        a = [1.0, -0.75, 0.60]
        y = lfilter(b, a, y).astype(np.float32)

    # Suavizado global (un polo)
    if S is not None:
        y_lp = np.copy(y)
        a = float(np.clip(S, 0.0, 0.999))
        for n in range(1, len(y)):
            y_lp[n] = (1.0 - a) * y[n] + a * y_lp[n - 1]
        y = y_lp

    # Fades anti-click
    Lf = max(1, int(0.004 * sr))
    Lf = min(Lf, len(y))
    win = np.linspace(0.0, 1.0, Lf, dtype=np.float32)
    y[:Lf] *= win
    y[-Lf:] *= win[::-1]

    # Compresión suave + normalización
    y = np.tanh(1.2 * y)
    y /= np.max(np.abs(y)) + 1e-9

    return y.astype(np.float32)
