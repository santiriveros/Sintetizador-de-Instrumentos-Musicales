import numpy as np
from ..constants import SR

def lay_notes_on_timeline(notes, render_fn):
    # notes: list of (track, start_s, dur_s, pitch, vel)
    t_end = max(s + dur for _, s, dur, _, _ in notes) + 1.0 if notes else 0.0
    y = np.zeros(int(SR * t_end), dtype=np.float32)
    for _, start, dur, pitch, vel in notes:
        sig = render_fn(pitch, dur, vel, SR)
        i0 = int(start * SR); i1 = i0 + len(sig)
        if i0 < 0: continue
        if i1 > len(y):
            i1 = len(y)
            sig = sig[:i1 - i0]
        y[i0:i1] += sig
    return y
