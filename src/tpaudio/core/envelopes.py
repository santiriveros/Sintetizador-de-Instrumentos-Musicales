import numpy as np

def adsr_env(sr, dur_s, attack_ms=10, decay_ms=60, sustain=0.6, release_ms=120):
    N = int(sr * dur_s)
    A = int(sr * attack_ms / 1000)
    D = int(sr * decay_ms / 1000)
    R = int(sr * release_ms / 1000)
    S = max(N - (A + D + R), 0)
    parts = []
    if A > 0: parts.append(np.linspace(0.0, 1.0, A, endpoint=False))
    if D > 0: parts.append(np.linspace(1.0, sustain, D, endpoint=False))
    if S > 0: parts.append(np.full(S, sustain, dtype=np.float32))
    if R > 0: parts.append(np.linspace(sustain, 0.0, R, endpoint=True))
    if not parts:
        return np.ones(N, dtype=np.float32)
    env = np.concatenate(parts).astype(np.float32)
    if len(env) < N:
        env = np.pad(env, (0, N - len(env)))
    return env[:N]
