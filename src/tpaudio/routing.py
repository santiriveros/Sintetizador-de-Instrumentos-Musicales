from .synth.additive import Additive
from .synth.karplus import render_note_ks
from .effects.delay import delay
from .effects.reverb import simple_reverb

def synth_from_preset(synth_kind: str, preset: dict):
    if synth_kind == 'additive':
        p = preset.get('partials')
        a = preset.get('amps')
        adsr = preset.get('adsr')
        return ('additive', Additive(partials=p, amps=a, adsr=adsr))
    elif synth_kind == 'ks':
        # devolver callable para render KS con params
        rho = preset.get('rho', 0.997)
        S = preset.get('S', 0.55)
        pick_pos = preset.get('pick_pos', 0.2)
        return ('ks', lambda pitch, dur, vel, sr: render_note_ks(pitch, dur, vel, sr, rho=rho, S=S, pick_pos=pick_pos))
    else:
        raise ValueError(f"Sintetizador no soportado: {synth_kind}")

def build_fx_chain(track_id: int, fx_presets: dict):
    chain = []
    per_track = (fx_presets.get('tracks') or {}).get(track_id, [])
    master = fx_presets.get('master') or []

    def add_fx(entry):
        t = entry.get('type')
        if t == 'delay':
            def fx(sig, sr):
                return delay(sig, sr, time_ms=entry.get('time_ms',200),
                             feedback=entry.get('feedback',0.25),
                             mix=entry.get('mix',0.2))
            chain.append(fx)
        elif t == 'reverb':
            def fx(sig, sr):
                return simple_reverb(sig, sr, mix=entry.get('mix',0.15))
            chain.append(fx)
        elif t == 'limiter':
            # handled in mixer or as last fx
            pass

    for e in per_track:
        add_fx(e)
    for e in master:
        add_fx(e)

    return chain
