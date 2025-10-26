import numpy as np

def delay(signal, sr, time_ms=220, feedback=0.25, mix=0.2):
    d = max(1, int(sr * time_ms / 1000))
    out = np.copy(signal).astype(np.float32)
    for n in range(d, len(signal)):
        out[n] += feedback * out[n - d]
    return (1 - mix) * signal + mix * out
