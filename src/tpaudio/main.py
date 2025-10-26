import argparse
import numpy as np
from collections import defaultdict

from .constants import SR
from .config import load_presets
from .core.audio_io import write_wav
from .core.timeline import lay_notes_on_timeline
from .core.mixer import mix_tracks
from .midi.loader import load_notes

# Sintetizadores
from .synth.karplus import render_note_ks
from .synth.sample_piano import load_samples, render_note_sample
from .synth.adsr import render_note_adsr
from .synth.piano_additive import render_note_piano_additive

# FX
from .effects.reverb import simple_reverb


# -----------------------------
# Defaults de rutas
# -----------------------------
DEFAULT_SAMPLE_DIR = r"C:\Users\HP\Documents\ASSD\TP2\tp-audio-full-starter\samples_piano_1"
DEFAULT_PRESET_INSTR = "presets/instruments.yml"
DEFAULT_PRESET_FX = "presets/effects.yml"


def _normalize(y: np.ndarray) -> np.ndarray:
    return (y / (np.max(np.abs(y)) + 1e-9)).astype(np.float32)


def _get_preset_params(presets, synth: str, preset_name: str):
    """
    Devuelve (params_dict, transpose_semitones) para el synth/preset pedidos.
    Si no existe, imprime los disponibles y devuelve {} y 0.
    """
    params = {}
    transpose = 0

    if not presets:
        print("[WARN] No hay presets cargados (archivo inexistente o error de parseo).")
        return params, transpose

    bank = presets.get(synth)
    if bank is None:
        print(f"[ERR] No existe el banco '{synth}' en el YAML. Bancos disponibles: {list(presets.keys())}")
        return {}, 0

    if not preset_name:
        print(f"[WARN] No se especificó --preset. Usando parámetros por defecto vacíos para '{synth}'.")
        return {}, 0

    if preset_name not in bank:
        print(f"[ERR] No encontré preset '{preset_name}' en banco '{synth}'. "
              f"Disponibles: {list(bank.keys())}")
        return {}, 0

    params = dict(bank[preset_name])  # copia
    # extrae transpose si está
    try:
        transpose = int(params.pop("transpose", 0))
    except Exception:
        transpose = 0

    return params, transpose


# =============================
# Render de escala de prueba
# =============================
def render_scale(
    synth="ks",
    preset=None,
    out="out_scale.wav",
    sample_dir=DEFAULT_SAMPLE_DIR,
    presets=None,
    add_reverb=True,
):
    base_pitches = [60, 62, 64, 65, 67, 69, 71, 72]  # C mayor

    params, transpose = _get_preset_params(presets, synth, preset)
    print(f"[INFO] {synth.upper()} preset='{preset}' params={params} transpose={transpose}")

    # Pre-carga para sample
    samples = None
    if synth == "sample":
        samples = load_samples(sample_dir)
        print(f"[INFO] Samples cargados desde: {sample_dir}")

    y_all = []
    for p in base_pitches:
        p2 = p + transpose  # ← APLICA TRANSPOSE
        if synth == "ks":
            y = render_note_ks(p2, 0.6, 110, SR, preset_name=preset, **params)
        elif synth == "sample":
            y = render_note_sample(samples, p2, 0.6, 110, SR)
        elif synth == "adsr":
            y = render_note_adsr(p2, 0.6, 110, SR)
        elif synth == "piano":
            y = render_note_piano_additive(p2, 0.6, 110, SR)
        else:
            raise SystemExit(f"[ERR] Sintetizador no reconocido: {synth}")

        y_all.append(y)
        y_all.append(np.zeros(int(0.05 * SR), dtype=np.float32))  # pequeño gap

    y = np.concatenate(y_all)
    if add_reverb:
        y = simple_reverb(y, SR, mix=0.15)
    y = _normalize(y)
    write_wav(out, y, SR)
    print(f"[OK] Escala renderizada → {out}")


# =============================
# Render de MIDI
# =============================
def render_midi(
    mid_path,
    synth="ks",
    preset=None,
    out="out_midi.wav",
    sample_dir=DEFAULT_SAMPLE_DIR,
    presets=None,
    add_reverb=True,
):
    notes = load_notes(mid_path)
    if not notes:
        raise SystemExit("No se encontraron notas en el MIDI.")
    print(f"[INFO] Notas cargadas: {len(notes)} desde {mid_path}")

    params, transpose = _get_preset_params(presets, synth, preset)
    print(f"[INFO] {synth.upper()} preset='{preset}' params={params} transpose={transpose}")

    # Pre-carga para sample
    samples = None
    if synth == "sample":
        samples = load_samples(sample_dir)
        print(f"[INFO] Samples cargados desde: {sample_dir}")

    # Agrupar por track para mezclar después
    tracks_audio = []
    by_track = defaultdict(list)
    for (ti, t0, dur, pitch, vel) in notes:
        by_track[ti].append((ti, t0, dur, pitch + transpose, vel))  # ← APLICA TRANSPOSE

    for ti, tnotes in by_track.items():
        print(f"[TRK {ti}] → {synth} ({preset or 'default'})")
        if synth == "ks":
            rf = lambda pitch, dur, vel, sr, _p=params, _n=preset: render_note_ks(
                pitch, dur, vel, sr, preset_name=_n, **_p
            )
        elif synth == "sample":
            rf = lambda pitch, dur, vel, sr, _s=samples: render_note_sample(_s, pitch, dur, vel, sr)
        elif synth == "adsr":
            rf = lambda pitch, dur, vel, sr: render_note_adsr(pitch, dur, vel, sr)
        elif synth == "piano":
            rf = lambda pitch, dur, vel, sr: render_note_piano_additive(pitch, dur, vel, sr)
        else:
            raise SystemExit(f"[ERR] Sintetizador no reconocido: {synth}")

        y_trk = lay_notes_on_timeline(tnotes, rf)
        tracks_audio.append(y_trk)

    y_mix = mix_tracks(tracks_audio, normalize=True, ceiling_dbfs=-1.0)
    if add_reverb:
        y_mix = simple_reverb(y_mix, SR, mix=0.15)
    y_mix = _normalize(y_mix)
    write_wav(out, y_mix, SR)
    print(f"[OK] Render MIDI → {out}")


# =============================
# CLI
# =============================
def main():
    ap = argparse.ArgumentParser(description="TP Audio Synth — presets, transpose y KS mejorado")
    ap.add_argument("--mode", type=str, default=None, choices=["test-scale"], help="Modo de prueba (escala)")
    ap.add_argument("--midi", type=str, default=None, help="Ruta a archivo MIDI")
    ap.add_argument("--out", type=str, default="out.wav", help="Archivo WAV de salida")
    ap.add_argument("--synth", type=str, default="ks",
                    choices=["ks", "sample", "adsr", "piano"], help="Motor de síntesis")
    ap.add_argument("--preset", type=str, default=None,
                    help="Preset del instrumento (nylon, steel, electric, bass, banjo, etc.)")
    ap.add_argument("--sample-dir", type=str, default=DEFAULT_SAMPLE_DIR,
                    help="Carpeta con samples (para --synth sample)")
    ap.add_argument("--no-reverb", action="store_true", help="Desactiva la reverb final")
    ap.add_argument("--preset-instruments", type=str, default=DEFAULT_PRESET_INSTR)
    ap.add_argument("--preset-effects", type=str, default=DEFAULT_PRESET_FX)
    args = ap.parse_args()

    # Carga de presets YAML
    presets = None
    try:
        presets = load_presets(args.preset_instruments, args.preset_effects)
    except Exception as e:
        print("[WARN] No se pudieron cargar presets:", e)

    add_reverb = not args.no_reverb

    if args.mode == "test-scale":
        render_scale(
            synth=args.synth,
            preset=args.preset,
            out=args.out,
            sample_dir=args.sample_dir,
            presets=presets,
            add_reverb=add_reverb,
        )
        return

    if args.midi:
        render_midi(
            args.midi,
            synth=args.synth,
            preset=args.preset,
            out=args.out,
            sample_dir=args.sample_dir,
            presets=presets,
            add_reverb=add_reverb,
        )
        return

    ap.print_help()


if __name__ == "__main__":
    main()
