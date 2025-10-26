import numpy as np

def simple_reverb(signal, sr, t_delays_ms=(29, 37, 43, 53), gains=(0.7, 0.6, 0.55, 0.5), mix=0.2):
    N = len(signal)
    out = np.copy(signal).astype(np.float32)
    for td_ms, g in zip(t_delays_ms, gains):
        d = max(1, int(sr * td_ms / 1000))
        buf = np.zeros_like(out)
        if d < N:
            buf[d:] = out[:-d]
            out += g * buf
    out = out / (np.max(np.abs(out)) + 1e-9)
    return (1 - mix) * signal + mix * out
