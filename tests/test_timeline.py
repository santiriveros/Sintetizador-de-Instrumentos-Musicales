import numpy as np
from src.tpaudio.core.timeline import lay_notes_on_timeline
from src.tpaudio.constants import SR
def test_timeline():
    def stub(p,d,v,sr):
        return np.ones(int(0.1*sr), dtype='float32')
    notes=[(0,0.0,0.1,60,100),(0,0.05,0.1,62,100)]
    y = lay_notes_on_timeline(notes, stub)
    assert y.size >= int(0.15*SR)
