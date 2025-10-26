import numpy as np
import soundfile as sf
from src.tpaudio.synth.karplus import render_note_ks

SR = 48000

# DEBUG: imprimí parámetros al entrar
print(">>> Generando KS A4 (440Hz aprox para MIDI 69)")
y = render_note_ks(
    pitch=69, dur_s=1.0, velocity=110, sr=SR,
    rho=0.999, S=0.45, pick_pos=0.15  # brillante/steel
)

# Normalizar y exportar
y = y.astype(np.float32)
y /= (np.max(np.abs(y)) + 1e-9)
sf.write("ks_single.wav", y, SR)
print(">>> ks_single.wav generado")
