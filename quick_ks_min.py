# Karplus–Strong mínimo, sin fracción, sin filtros extra (debería sonar sí o sí)
import numpy as np, soundfile as sf

sr = 48000
f0 = 220.0            # A3 (cambiá a gusto)
dur = 2.0
L = int(sr / f0)      # delay entero
N = int(sr * dur)

buf = np.random.uniform(-1, 1, L).astype(np.float32) * 0.5
out = np.zeros(N, dtype=np.float32)

i = 0
rho = 0.996           # sustain (subilo a 0.998 si querés más cola)
for n in range(N):
    y = buf[i]
    # promedio 2 puntos (low-pass) + pérdida -> ESENCIAL para que oscile
    buf[i] = rho * 0.5 * (buf[i] + buf[(i - 1) % L])
    out[n] = y
    i = (i + 1) % L

# Normalizar seguro
mx = np.max(np.abs(out)) + 1e-9
out = (out / mx).astype(np.float32)
sf.write("ks_min.wav", out, sr)
print("Listo: ks_min.wav  |  peak =", float(mx), "  RMS ~", float(np.sqrt(np.mean(out**2))))
