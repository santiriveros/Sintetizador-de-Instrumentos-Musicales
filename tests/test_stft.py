import numpy as np
from src.tpaudio.analysis.spectrogram import save_spectrogram
def test_spec(tmp_path):
    import soundfile as sf
    sr=48000
    t=np.linspace(0,0.1,int(sr*0.1),endpoint=False,dtype='float32')
    x=np.sin(2*np.pi*440*t).astype('float32')
    wav=tmp_path/'t.wav'; sf.write(wav, x, sr)
    png=tmp_path/'s.png'
    save_spectrogram(x, sr, str(png))
    assert png.exists()
