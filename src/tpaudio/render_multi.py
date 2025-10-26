import argparse
from .config import load_presets
from .core.timeline import lay_notes_on_timeline
from .core.mixer import mix_tracks
from .core.audio_io import write_wav
from .midi.loader import load_notes
from .synth.karplus import render_note_ks
from .synth.sample_piano import load_samples, render_note_sample
from .synth.additive import Additive

def _parse_track_list(s: str):
    out = []
    if not s:
        return out
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return sorted(set(out))

def _get_params(presets, synth_key: str, preset_name: str):
    params = {}
    transpose = 0
    if presets and preset_name:
        bank = (presets.get(synth_key) or {})
        params = (bank.get(preset_name) or {}).copy()
        try:
            transpose = int(params.pop("transpose", 0))
        except Exception:
            transpose = 0
    return params, transpose

def _render_notes(notes, synth_type, preset_name, presets, sample_dir, sr):
    if not notes:
        return None
    if synth_type == "sample":
        samples = load_samples(sample_dir)
        def render_fn(pitch, dur, vel, sr):
            return render_note_sample(samples, pitch, dur, vel, sr)
    elif synth_type == "additive":
        synth = Additive()
        def render_fn(pitch, dur, vel, sr):
            return synth.render_note(pitch, dur, vel, sr)
    elif synth_type == "ks":
        params, tr = _get_params(presets, "ks", preset_name)
        def render_fn(pitch, dur, vel, sr, _p=params, _tr=tr):
            return render_note_ks(pitch + _tr, dur, vel, sr,
                                  rho=_p.get("rho", 0.998),
                                  S=_p.get("S", 0.5),
                                  pick_pos=_p.get("pick_pos", 0.2),
                                  noise_mix=_p.get("noise_mix", 0.02),
                                  stiffness=_p.get("stiffness", 0.001),
                                  preset_name=preset_name)
    else:
        raise SystemExit(f"[ERROR] Tipo de sintetizador desconocido: {synth_type}")
    return lay_notes_on_timeline(notes, render_fn)

def render_multi(midi_path: str, instruments: list[str], presets_path: str,
                 out_path: str, sample_dir: str = "samples_piano_1", sr: int = 48000):
    presets = load_presets(presets_path, None)
    notes_all = load_notes(midi_path)
    if not notes_all:
        raise SystemExit(f"[ERROR] No se encontraron notas en {midi_path}")
    print(f"[INFO] Archivo MIDI: {midi_path}")
    print(f"[INFO] Instrumentos: {instruments}")

    mixes = []
    for inst_decl in instruments:
        try:
            name, synth_type, track_s = inst_decl.split(":")
        except ValueError:
            raise SystemExit(f"[ERROR] Formato inválido en --inst: {inst_decl} (usa nombre:tipo:tracks)")
        track_ids = _parse_track_list(track_s)
        notes = [n for n in notes_all if n[0] in track_ids]
        print(f"[{name.upper()}] synth={synth_type}, preset={name}, tracks={track_ids}, notas={len(notes)}")
        y = _render_notes(notes, synth_type, name, presets, sample_dir, sr)
        if y is not None:
            mixes.append(y)

    if not mixes:
        raise SystemExit("[ERROR] No se generó ninguna pista válida.")
    mix = mix_tracks(mixes, normalize=True, ceiling_dbfs=-1.0)
    write_wav(out_path, mix, sr)
    print(f"[OK] Render MULTI → {out_path}")

def main():
    ap = argparse.ArgumentParser(description="Renderiza 1 o más instrumentos desde un MIDI.")
    ap.add_argument("--midi", required=True, help="Ruta al archivo MIDI")
    ap.add_argument("--inst", required=True, action="append",
                    help="Definición: nombre:tipo:tracks (puede repetirse). Ej: piano:sample:0,1  bass:ks:2")
    ap.add_argument("--preset-instruments", required=True, help="Ruta a presets/instruments.yml")
    ap.add_argument("--sample-dir", default="samples_piano_1", help="Carpeta de samples de piano")
    ap.add_argument("--out", default="multi_mix.wav", help="Archivo WAV de salida")
    args = ap.parse_args()
    render_multi(args.midi, args.inst, args.preset_instruments, args.out, args.sample_dir)

if __name__ == "__main__":
    main()

