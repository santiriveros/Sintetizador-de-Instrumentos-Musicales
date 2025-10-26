from abc import ABC, abstractmethod
import numpy as np

class Synth(ABC):
    @abstractmethod
    def render_note(self, pitch: int, dur_s: float, velocity: int, sr: int) -> np.ndarray:
        ...
