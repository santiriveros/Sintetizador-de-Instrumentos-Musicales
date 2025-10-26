import numpy as np
from .base import Synth
from ..core.envelopes import adsr_env
from ..core.dsp import midi2freq

class Additive(Synth):
    def __init__(self, partials=None, amps=None, adsr=None):
        if partials is None: partials = np.array([1,3,5,7,9], dtype=np.float32)
        if amps is None: amps = np.array([1.0,0.6,0.4,0.25,0.18], dtype=np.float32)
        self.partials = np.array(partials, dtype=np.float32)
        self.amps = np.array(amps, dtype=np.float32)
        self.amps /= np.max(np.abs(self.amps)) + 1e-12
        self.adsr = adsr or dict(attack_ms=12, decay_ms=60, sustain=0.6, release_ms=120)

    def render_note(self, pitch, dur_s, velocity, sr):
        N = int(sr * dur_s)
        t = np.arange(N, dtype=np.float32) / sr
        f0 = midi2freq(pitch)
        sig = np.zeros(N, dtype=np.float32)
        for k, a in zip(self.partials, self.amps):
            sig += a * np.sin(2*np.pi*(k*f0)*t, dtype=np.float32)
        env = adsr_env(sr, dur_s, **self.adsr)
        sig = sig[:len(env)] * env * (velocity / 127.0)
        return sig.astype(np.float32)
