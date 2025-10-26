from src.tpaudio.synth.karplus import render_note_ks
from src.tpaudio.constants import SR
def test_ks_note():
    y = render_note_ks(69, 0.2, 100, SR)
    assert y.ndim == 1 and y.size > 0
