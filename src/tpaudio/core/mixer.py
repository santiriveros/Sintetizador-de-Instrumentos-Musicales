import numpy as np

def mix_tracks(tracks, normalize=True, ceiling_dbfs=-1.0):
    if not tracks:
        return np.zeros(1, dtype=np.float32)
    N = max(len(t) for t in tracks)
    y = np.zeros(N, dtype=np.float32)
    for t in tracks:
        y[:len(t)] += t.astype(np.float32)
    if normalize:
        peak = np.max(np.abs(y)) + 1e-9
        target = 10 ** (ceiling_dbfs / 20.0)
        y = y / peak * target
    return np.clip(y, -1.0, 1.0).astype(np.float32)
