from src.tpaudio.synth.additive import Additive
from src.tpaudio.constants import SR
def test_additive_note():
    a = Additive()
    y = a.render_note(69, 0.2, 100, SR)
    assert y.ndim == 1 and y.size > 0
