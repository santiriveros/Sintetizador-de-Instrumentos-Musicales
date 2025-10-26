import numpy as np
from typing import Optional, Dict, Any
from ..core.dsp import midi2freq
from ..core.envelopes import adsr_env

def render_note_piano_additive(
    pitch: int,
    dur_s: float,
    velocity: int,
    sr: int = 48000,
    n_partials: int = 30,
    B: float = 3e-4,
    amp_decay_exp: float = 1.2,
    partial_decay_base: float = 0.85,
    noise_mix: float = 0.08,
    adsr: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    f0 = midi2freq(pitch)
    N = int(sr * dur_s)
    t = np.arange(N, dtype=np.float32) / sr
    fnyq = sr / 2.0
    rng = np.random.default_rng(12345)
    v_scale = float(velocity) / 127.0
    bright_boost = 0.5 + 0.5 * v_scale
    y = np.zeros(N, dtype=np.float32)
    for k in range(1, n_partials + 1):
        fk = k * f0 * np.sqrt(1.0 + B * (k ** 2))
        if fk >= fnyq:
            break
        ak = 1.0 / (k ** amp_decay_exp)
        ak *= (1.0 + bright_boost * 0.15 * (k - 1) / max(1, n_partials - 1))
        tau = (0.6 * dur_s) * (partial_decay_base ** (k - 1)) + 1e-6
        env = np.exp(-t / tau).astype(np.float32)
        phase = 2.0 * np.pi * fk * t + 2.0 * np.pi * rng.random()
        y += (ak * np.sin(phase, dtype=np.float32) * env).astype(np.float32)
    if noise_mix > 0.0:
        Lh = max(1, int(0.02 * sr))
        hammer = rng.standard_normal(Lh).astype(np.float32)
        for i in range(1, Lh):
            hammer[i] = 0.6 * hammer[i] + 0.4 * hammer[i - 1]
        hammer *= np.linspace(1.0, 0.0, Lh, dtype=np.float32)
        y[:Lh] += noise_mix * hammer
    y *= v_scale
    if adsr is None:
        adsr = dict(attack_ms=2, decay_ms=900, sustain=0.0, release_ms=250)
    env = adsr_env(sr, dur_s, **adsr)
    env = env[:len(y)]
    y *= env
    Lf = max(1, int(0.004 * sr))
    Lf = min(Lf, len(y))
    fade = np.linspace(0, 1, Lf, dtype=np.float32)
    y[:Lf] *= fade
    y[-Lf:] *= fade[::-1]
    y /= (np.max(np.abs(y)) + 1e-9)
    return y.astype(np.float32)

