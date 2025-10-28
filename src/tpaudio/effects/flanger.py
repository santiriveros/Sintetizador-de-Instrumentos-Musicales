from dataclasses import dataclass
import numpy as np

@dataclass
class Flanger:
    rate_hz: float = 0.25
    depth_ms: float = 3.0
    base_ms: float = 2.0
    feedback: float = 0.2
    mix: float = 0.5

    def process(self, x: np.ndarray, fs: int) -> np.ndarray:
        n = len(x)
        y = np.zeros_like(x, dtype=np.float64)
        max_delay_ms = self.base_ms + self.depth_ms
        max_delay_samps = int(np.ceil(max_delay_ms * 1e-3 * fs)) + 2
        buf = np.zeros(max_delay_samps, dtype=np.float64)
        wptr = 0
        t = np.arange(n) / fs
        lfo = np.sin(2 * np.pi * self.rate_hz * t)
        delay_samps = (self.base_ms + self.depth_ms * (0.5 * (lfo + 1.0))) * 1e-3 * fs
        fb = float(np.clip(self.feedback, -0.95, 0.95))
        mix = float(np.clip(self.mix, 0.0, 1.0))
        for i in range(n):
            buf[wptr] = x[i] + fb * buf[wptr]
            read_pos = (wptr - delay_samps[i]) % max_delay_samps
            i0 = int(np.floor(read_pos))
            i1 = (i0 + 1) % max_delay_samps
            frac = read_pos - i0
            delayed = (1 - frac) * buf[i0] + frac * buf[i1]
            y[i] = (1 - mix) * x[i] + mix * delayed
            wptr = (wptr + 1) % max_delay_samps
        return y.astype(x.dtype)
