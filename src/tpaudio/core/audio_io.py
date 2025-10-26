import numpy as np
import soundfile as sf

def write_wav(path: str, audio: np.ndarray, sr: int):
    audio = np.clip(audio, -1.0, 1.0).astype(np.float32)
    sf.write(path, audio, sr)
