import numpy as np

def midi2freq(p: int) -> float:
    return 440.0 * 2 ** ((p - 69) / 12)

def hp1(x, a=0.995):
    y = np.zeros_like(x, dtype=np.float32)
    xm1 = 0.0
    ym1 = 0.0
    for i, xi in enumerate(x):
        yi = xi - xm1 + a * ym1
        y[i] = yi
        xm1 = xi
        ym1 = yi
    return y

def frac_delay_read(buf, r_index):
    n = len(buf)
    i0 = int(r_index) % n
    i1 = (i0 - 1) % n
    frac = r_index - int(r_index)
    return (1.0 - frac) * buf[i0] + frac * buf[i1]
