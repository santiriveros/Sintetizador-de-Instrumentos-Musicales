import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import stft

def save_spectrogram(wav, sr, path_png, nperseg=1024, noverlap=None):
    if noverlap is None:
        noverlap = nperseg // 4
    f, t, Z = stft(wav, sr, nperseg=nperseg, noverlap=noverlap)
    mag = 20*np.log10(np.abs(Z)+1e-9)
    plt.figure(figsize=(8,4))
    plt.pcolormesh(t, f, mag, shading='gouraud')
    plt.xlabel("Tiempo [s]"); plt.ylabel("Frecuencia [Hz]")
    plt.title("Espectrograma")
    plt.colorbar(label="dB")
    plt.tight_layout()
    plt.savefig(path_png, dpi=200)
    plt.close()
