from dataclasses import dataclass
import numpy as np


try:
    from scipy.signal import fftconvolve
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False


def _ensure_f32(x: np.ndarray) -> np.ndarray:
    return x.astype(np.float32, copy=False)


def _one_pole_lpf(x: np.ndarray, alpha: float) -> np.ndarray:
    """Filtro paso-bajo simple (por brillo de cola). alpha ~ 0..1"""
    y = np.empty_like(x)
    acc = np.float32(0.0)
    a = np.float32(alpha)
    for i in range(x.shape[0]):
        acc = acc + a * (x[i] - acc)
        y[i] = acc
    return y


@dataclass
class Reverb:
    room_size: float = 0.5      
    decay_s: float = 1.8        
    pre_delay_ms: float = 20.0
    brightness: float = 0.6     
    mix: float = 0.25           

    def _build_ir(self, n: int, fs: int) -> np.ndarray:
        """Construye una IR exponencial (cola) con duración proporcional al room_size/decay_s."""

        delay_len = int(max(1, self.room_size * 0.06 * fs))
        # envolvente exponencial T60≈decay_s
        t = np.arange(delay_len, dtype=np.float32)
        if self.decay_s <= 0.05:
            ir = np.zeros(1, dtype=np.float32)
            ir[0] = 1.0
            return ir
        ir = np.exp((-6.9077554 * t) / (self.decay_s * fs)).astype(np.float32)
        if ir.sum() > 0:
            ir = ir / (ir.sum() + 1e-12)
        return ir

    def process(self, x: np.ndarray, fs: int) -> np.ndarray:
        orig_dtype = x.dtype
        x = _ensure_f32(np.asarray(x))
        n = x.shape[0]

        # IR (construida una vez por llamada)
        ir = self._build_ir(n, fs)

        # Convolución
        if _HAS_SCIPY:
            wet = fftconvolve(x, ir, mode="full", axes=-1)[:n].astype(np.float32, copy=False)
        else:
            wet = np.convolve(x, ir, mode='full')[:n].astype(np.float32, copy=False)

        # Pre-delay
        pre = int(round(max(0.0, self.pre_delay_ms) * 1e-3 * fs))
        if pre > 0:
            if pre >= n:
                wet = np.zeros_like(wet)
            else:
                wet = np.concatenate([np.zeros(pre, dtype=np.float32), wet])[:n]

        fc = 1000.0 + 9000.0 * float(np.clip(self.brightness, 0.0, 1.0))
        alpha = np.float32((2.0 * np.pi * fc) / (2.0 * np.pi * fc + fs))
        wet = _one_pole_lpf(wet, alpha)

        # Mezcla
        mix = float(np.clip(self.mix, 0.0, 1.0))
        y = (1.0 - mix) * x + mix * wet

        return y.astype(orig_dtype, copy=False)
