# src/tpaudio/synth/adsr.py
import numpy as np

def render_kick_additive(
    dur_s: float = 0.35,
    sr: int = 48000,
    f_start_hz: float = 140.0,
    f_end_hz: float = 48.0,
    tau_freq_ms: float = 24.0,
    amps=(1.0, 0.5, 0.25, 0.15, 0.10),
    ratios=(1.0, 1.6, 2.3, 3.5, 4.2),
    tau_amp_ms=(120, 90, 70, 55, 45),
    click_ms: float = 4.0,
    click_mix: float = 0.06,
    hp_hz: float = 22.0,
    drive: float = 0.9,
) -> np.ndarray:
    """
    Kick aditivo con 3–5 parciales inarmónicos y caída de frecuencia común.
    - f(t) = f_end + (f_start - f_end) * exp(-t/tau_f)
    - Cada parcial k: y_k(t) = a_k * exp(-t/tau_a_k) * sin( 2π * ∫ (r_k f(t)) dt + φ_k )
    - 'click' inicial opcional (ruido corto con decaimiento exponencial)
    - HP 1er orden + soft-clip suave + fades anti-click + normalizado
    """
    N = int(sr * dur_s)
    t = np.arange(N, dtype=np.float32) / sr

    # Caída de pitch (exponencial)
    tau_f = max(1e-6, tau_freq_ms / 1000.0)
    f_inst = f_end_hz + (f_start_hz - f_end_hz) * np.exp(-t / tau_f)

    # Suma aditiva
    y = np.zeros_like(t, dtype=np.float32)
    for a, r, tau_a_ms in zip(amps, ratios, tau_amp_ms):
        env = np.exp(-t / max(1e-6, (tau_a_ms / 1000.0))).astype(np.float32)
        phase = 2.0 * np.pi * np.cumsum(f_inst * float(r)) / sr
        phi0 = np.random.rand() * 2.0 * np.pi
        y += (a * env * np.sin(phase + phi0)).astype(np.float32)

    # Click inicial (ruido con decaimiento rápido)
    if click_ms > 0 and click_mix > 0:
        L = max(1, int(sr * (click_ms / 1000.0)))
        n = np.zeros_like(y, dtype=np.float32)
        n[:L] = np.random.randn(L).astype(np.float32)
        n[:L] *= np.exp(-np.linspace(0, 1, L, dtype=np.float32) * 6.0)
        y = (1.0 - float(click_mix)) * y + float(click_mix) * n

    # HP 1er orden (limpia DC/rumble)
    if hp_hz and hp_hz > 0:
        alpha = np.exp(-2.0 * np.pi * float(hp_hz) / sr)
        yhp = np.zeros_like(y, dtype=np.float32)
        xm1 = 0.0
        ym1 = 0.0
        for i, xi in enumerate(y):
            yhp[i] = alpha * (ym1 + xi - xm1)
            xm1, ym1 = xi, yhp[i]
        y = yhp

    # Soft-clip suave
    if drive and drive > 0:
        y = np.tanh(float(drive) * y).astype(np.float32)

    # Fades anti-click
    Lf = max(1, int(0.004 * sr))
    Lf = min(Lf, len(y))
    fade = np.linspace(0, 1, Lf, dtype=np.float32)
    y[:Lf] *= fade
    y[-Lf:] *= fade[::-1]

    # Normalizado
    y /= (np.max(np.abs(y)) + 1e-9)

    # 🔥 BOOST: aumentar volumen final (post normalización)
    y /= (np.max(np.abs(y)) + 1e-9)
    y *= 1.3  # Aumenta 30% el nivel general (ajustá 1.2–1.5)
    
    return y.astype(np.float32)
