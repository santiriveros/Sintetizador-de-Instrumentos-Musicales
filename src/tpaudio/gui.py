# src/tpaudio/gui.py
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np

# --- Soporte de imports cuando se ejecuta como módulo con PYTHONPATH=src ---
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# --- Imports del proyecto ---
try:
    from tpaudio.constants import SR
    from tpaudio.config import load_presets
    from tpaudio.core.audio_io import write_wav
    from tpaudio.core.timeline import lay_notes_on_timeline
    from tpaudio.core.mixer import mix_tracks
    from tpaudio.midi.loader import load_notes

    from tpaudio.synth.karplus import render_note_ks
    from tpaudio.synth.sample_piano import load_samples, render_note_sample
    from tpaudio.synth.piano_additive import render_note_piano_additive
    from tpaudio.synth.adsr import render_kick_additive

    from tpaudio.effects.reverb import simple_reverb
except Exception as e:
    raise RuntimeError(
        f"No se pudieron importar módulos del paquete tpaudio.\n"
        f"Asegurate de ejecutar con:\n"
        f"$env:PYTHONPATH='{SRC_DIR}' ; python -m tpaudio.gui\n\n{e}"
    )

# --- MIDO para detectar instrumentos GM en el MIDI ---
try:
    import mido
    HAS_MIDO = True
except Exception:
    HAS_MIDO = False

# ===== Config =====
PROJECT_ROOT = r"C:\Users\Admin\OneDrive\Documents\GitHub\Sintetizador-de-Instrumentos-Musicales"
DEFAULT_SAMPLE_DIR = os.path.join(PROJECT_ROOT, "samples_piano_1")
DEFAULT_PRESET_INSTR = os.path.join(PROJECT_ROOT, "presets", "instruments.yml")
DEFAULT_PRESET_FX = os.path.join(PROJECT_ROOT, "presets", "effects.yml")

def _normalize(y: np.ndarray) -> np.ndarray:
    return (y / (np.max(np.abs(y)) + 1e-9)).astype(np.float32)

# ===== Emojis por familia =====
INSTRUMENT_EMOJIS = {
    "piano": "🎹", "organ": "🎹", "keyboard": "🎹",
    "guitar": "🎸", "bass": "🎸",
    "violin": "🎻", "cello": "🎻", "strings": "🎻", "harp": "🎻",
    "flute": "🎶", "piccolo": "🎶", "oboe": "🎶",
    "clarinet": "🎷", "sax": "🎷",
    "trumpet": "🎺", "trombone": "🎺", "horn": "🎺", "tuba": "🎺",
    "drum": "🥁", "percussion": "🥁", "timpani": "🥁",
    "synth": "🎛️", "lead": "🎛️", "pad": "🎛️",
    "voice": "🎤", "vocal": "🎤",
}

GM_PROGRAM_NAMES = [
    "Acoustic Grand Piano","Bright Acoustic Piano","Electric Grand Piano","Honky-tonk Piano",
    "Electric Piano 1","Electric Piano 2","Harpsichord","Clavinet",
    "Celesta","Glockenspiel","Music Box","Vibraphone",
    "Marimba","Xylophone","Tubular Bells","Dulcimer",
    "Drawbar Organ","Percussive Organ","Rock Organ","Church Organ",
    "Reed Organ","Accordion","Harmonica","Tango Accordion",
    "Acoustic Guitar (nylon)","Acoustic Guitar (steel)","Electric Guitar (jazz)","Electric Guitar (clean)",
    "Electric Guitar (muted)","Overdriven Guitar","Distortion Guitar","Guitar harmonics",
    "Acoustic Bass","Electric Bass (finger)","Electric Bass (pick)","Fretless Bass",
    "Slap Bass 1","Slap Bass 2","Synth Bass 1","Synth Bass 2",
    "Violin","Viola","Cello","Contrabass",
    "Tremolo Strings","Pizzicato Strings","Orchestral Harp","Timpani",
    "String Ensemble 1","String Ensemble 2","SynthStrings 1","SynthStrings 2",
    "Choir Aahs","Voice Oohs","Synth Voice","Orchestra Hit",
    "Trumpet","Trombone","Tuba","Muted Trumpet",
    "French Horn","Brass Section","SynthBrass 1","SynthBrass 2",
    "Soprano Sax","Alto Sax","Tenor Sax","Baritone Sax",
    "Oboe","English Horn","Bassoon","Clarinet",
    "Piccolo","Flute","Recorder","Pan Flute",
    "Blown Bottle","Shakuhachi","Whistle","Ocarina",
    "Lead 1 (square)","Lead 2 (sawtooth)","Lead 3 (calliope)","Lead 4 (chiff)",
    "Lead 5 (charang)","Lead 6 (voice)","Lead 7 (fifths)","Lead 8 (bass+lead)",
    "Pad 1 (new age)","Pad 2 (warm)","Pad 3 (polysynth)","Pad 4 (choir)",
    "Pad 5 (bowed)","Pad 6 (metallic)","Pad 7 (halo)","Pad 8 (sweep)",
    "FX 1 (rain)","FX 2 (soundtrack)","FX 3 (crystal)","FX 4 (atmosphere)",
    "FX 5 (brightness)","FX 6 (goblins)","FX 7 (echoes)","FX 8 (sci-fi)",
    "Sitar","Banjo","Shamisen","Koto",
    "Kalimba","Bag pipe","Fiddle","Shanai",
    "Tinkle Bell","Agogo","Steel Drums","Woodblock",
    "Taiko Drum","Melodic Tom","Synth Drum","Reverse Cymbal",
    "Guitar Fret Noise","Breath Noise","Seashore","Bird Tweet",
    "Telephone Ring","Helicopter","Applause","Gunshot"
]

def guess_emoji(instr_name: str) -> str:
    n = (instr_name or "").lower()
    for key, emoji in INSTRUMENT_EMOJIS.items():
        if key in n:
            return emoji
    return "🎵"

def suggest_synth(instr_name: str) -> str:
    n = (instr_name or "").lower()
    if "drum" in n or "percussion" in n or "timpani" in n:
        return "kick"
    if "piano" in n or "keyboard" in n or "organ" in n:
        return "piano"
    if "guitar" in n or "bass" in n:
        return "ks"
    if "string" in n or "violin" in n or "cello" in n or "harp" in n:
        return "ks"
    if "sax" in n or "trumpet" in n or "trombone" in n or "horn" in n or "tuba" in n:
        return "ks"
    if "synth" in n or "lead" in n or "pad" in n:
        return "piano"
    return "ks"

def detect_midi_instruments(mid_path: str):
    """Devuelve lista de (track_index, instrument_name, emoji) usando mido."""
    results = []
    if not HAS_MIDO:
        return results
    try:
        mid = mido.MidiFile(mid_path)
        for i, track in enumerate(mid.tracks):
            name = None
            for msg in track:
                if msg.type == "program_change":
                    prog = int(msg.program)
                    name = GM_PROGRAM_NAMES[prog] if 0 <= prog < len(GM_PROGRAM_NAMES) else f"Program {prog}"
                    break
            if not name:
                for msg in track:
                    if hasattr(msg, "channel") and msg.channel == 9:
                        name = "Drum Kit (Channel 10)"
                        break
            if not name:
                name = "Unknown / No Program Change"
            results.append((i, name, guess_emoji(name)))
    except Exception as e:
        print("[WARN] Error leyendo instrumentos del MIDI:", e)
    return results

# ===== Helpers =====
def list_mid_files_in_root(root_folder: str):
    """Solo archivos .mid/.midi en la carpeta raíz (no subdirectorios)."""
    out = []
    try:
        for fn in os.listdir(root_folder):
            if fn.lower().endswith((".mid", ".midi")):
                out.append(os.path.join(root_folder, fn))
    except Exception:
        pass
    return sorted(out, key=lambda p: os.path.basename(p).lower())

class TrackConfig:
    def __init__(self, track_idx: int):
        self.track_idx = track_idx
        self.synth = tk.StringVar(value="ks")
        self.preset = tk.StringVar(value="nylon")
        self.enabled = tk.BooleanVar(value=True)
        self.detected = ""  # nombre instrumento GM
        self.emoji = "🎵"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TP Audio GUI — MIDI desde raíz + presets dinámicos (readonly)")
        self.geometry("1080x700")

        # Estado global
        self.midi_path = tk.StringVar()
        self.out_path = tk.StringVar(value="out.wav")
        self.sample_dir = tk.StringVar(value=DEFAULT_SAMPLE_DIR)
        self.preset_instr = tk.StringVar(value=DEFAULT_PRESET_INSTR)
        self.preset_fx = tk.StringVar(value=DEFAULT_PRESET_FX)

        self.reverb_on = tk.BooleanVar(value=True)
        self.reverb_mix = tk.DoubleVar(value=0.15)

        self.notes = []
        self.by_track = {}
        self.tracks_cfg = []

        self.presets = None
        self.available_presets = {}  # dict: bank -> [preset1, preset2, ...]

        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # Archivos / Presets / Samples
        frm_files = ttk.LabelFrame(container, text="Archivos / Presets / Samples")
        frm_files.pack(fill="x", padx=4, pady=6)

        r = 0
        ttk.Label(frm_files, text="Archivo MIDI:").grid(row=r, column=0, sticky="e", padx=6, pady=4)

        # Combo de MIDI (readonly) que se refresca al abrir el desplegable
        self.cmb_midi = ttk.Combobox(frm_files, state="readonly", width=72, values=[])
        self.cmb_midi.grid(row=r, column=1, padx=6, pady=4, sticky="w")
        self.cmb_midi.bind("<<ComboboxSelected>>", self._on_midi_selected)
        # refrescar lista al ganar foco o al click
        self.cmb_midi.bind("<Button-1>", self._refresh_midi_list)
        self.cmb_midi.bind("<FocusIn>", self._refresh_midi_list)

        ttk.Button(frm_files, text="Cargar MIDI", command=self._load_midi).grid(row=r, column=2, padx=6, pady=4)
        r += 1

        ttk.Label(frm_files, text="Salida WAV:").grid(row=r, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(frm_files, textvariable=self.out_path, width=72).grid(row=r, column=1, padx=6, pady=4, sticky="w")
        ttk.Button(frm_files, text="Elegir...", command=self._browse_out).grid(row=r, column=2, padx=6, pady=4)
        r += 1

        ttk.Label(frm_files, text="Presets instrumentos (YAML):").grid(row=r, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(frm_files, textvariable=self.preset_instr, width=72).grid(row=r, column=1, padx=6, pady=4, sticky="w")
        ttk.Button(frm_files, text="Cargar presets", command=self._load_presets).grid(row=r, column=2, padx=6, pady=4)
        r += 1

        ttk.Label(frm_files, text="Carpeta Samples (para 'sample'):").grid(row=r, column=0, sticky="e", padx=6, pady=4)
        ttk.Entry(frm_files, textvariable=self.sample_dir, width=72).grid(row=r, column=1, padx=6, pady=4, sticky="w")
        ttk.Button(frm_files, text="Buscar...", command=self._browse_samples).grid(row=r, column=2, padx=6, pady=4)
        r += 1

        # FX
        frm_fx = ttk.LabelFrame(container, text="Efectos")
        frm_fx.pack(fill="x", padx=4, pady=6)
        ttk.Checkbutton(frm_fx, text="Reverb", variable=self.reverb_on).grid(row=0, column=0, padx=6, pady=4, sticky="w")
        ttk.Label(frm_fx, text="Mix:").grid(row=0, column=1, padx=6, pady=4, sticky="e")
        ttk.Scale(frm_fx, from_=0.0, to=0.6, orient="horizontal", variable=self.reverb_mix, length=220).grid(row=0, column=2, padx=6, pady=4, sticky="w")

        # Pistas
        self.frm_tracks = ttk.LabelFrame(container, text="Pistas (motor por pista + instrumento detectado)")
        self.frm_tracks.pack(fill="both", expand=True, padx=4, pady=6)

        self.tree = ttk.Treeview(self.frm_tracks, columns=("enabled", "synth", "preset", "instrument", "emoji"),
                                 show="headings", height=16)
        self.tree.heading("enabled", text="Usar")
        self.tree.heading("synth", text="Motor")
        self.tree.heading("preset", text="Preset")
        self.tree.heading("instrument", text="Instrumento")
        self.tree.heading("emoji", text="🎵")
        self.tree.column("enabled", width=60, anchor="center")
        self.tree.column("synth", width=120, anchor="center")
        self.tree.column("preset", width=240)
        self.tree.column("instrument", width=300)
        self.tree.column("emoji", width=60, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        frm_edit = ttk.Frame(self.frm_tracks)
        frm_edit.pack(fill="x", padx=6, pady=6)

        ttk.Label(frm_edit, text="Pista:").grid(row=0, column=0, padx=6, sticky="e")
        self.sel_track_lbl = ttk.Label(frm_edit, text="-")
        self.sel_track_lbl.grid(row=0, column=1, padx=6, sticky="w")

        ttk.Label(frm_edit, text="Motor:").grid(row=0, column=2, padx=6, sticky="e")
        self.cmb_synth = ttk.Combobox(frm_edit, values=["kick", "ks", "sample", "piano"], state="readonly", width=10)
        self.cmb_synth.grid(row=0, column=3, padx=6)
        self.cmb_synth.bind("<<ComboboxSelected>>", self._on_synth_change)

        ttk.Label(frm_edit, text="Preset (según banco, readonly):").grid(row=0, column=4, padx=6, sticky="e")
        self.cmb_preset = ttk.Combobox(frm_edit, values=[], state="readonly", width=32)
        self.cmb_preset.grid(row=0, column=5, padx=6)

        ttk.Button(frm_edit, text="Aplicar a pista", command=self._apply_to_selected).grid(row=0, column=6, padx=6)
        ttk.Button(frm_edit, text="Aplicar a todas", command=self._apply_to_all).grid(row=0, column=7, padx=6)

        # Acciones
        frm_actions = ttk.Frame(container)
        frm_actions.pack(fill="x", padx=4, pady=6)
        ttk.Button(frm_actions, text="Generar WAV", command=self._render).pack(side="right", padx=6)
        ttk.Button(frm_actions, text="Salir", command=self.destroy).pack(side="right", padx=6)

    # ---------- MIDI combo ----------
    def _refresh_midi_list(self, _evt=None):
        paths = list_mid_files_in_root(PROJECT_ROOT)
        display = [os.path.basename(p) for p in paths]
        self._midi_paths_cache = {os.path.basename(p): p for p in paths}
        self.cmb_midi["values"] = display
        if display and not self.cmb_midi.get():
            self.cmb_midi.set(display[0])
            self.midi_path.set(self._midi_paths_cache[display[0]])

    def _on_midi_selected(self, _evt=None):
        name = self.cmb_midi.get()
        full = self._midi_paths_cache.get(name)
        if full:
            self.midi_path.set(full)

    # ---------- File pickers ----------
    def _browse_out(self):
        path = filedialog.asksaveasfilename(initialdir=PROJECT_ROOT, defaultextension=".wav",
                                            filetypes=[("WAV", "*.wav")])
        if path:
            self.out_path.set(path)

    def _browse_samples(self):
        path = filedialog.askdirectory(initialdir=PROJECT_ROOT)
        if path:
            self.sample_dir.set(path)

    # ---------- Presets ----------
    # Agregá en la clase App:
    def _ensure_presets_loaded(self):
        if self.presets is None:
            try:
                self.presets = load_presets(self.preset_instr.get() or DEFAULT_PRESET_INSTR, DEFAULT_PRESET_FX)
            except Exception:
                self.presets = {}
        if not getattr(self, "available_presets", None):
            avail = {}
            for bank, items in (self.presets or {}).items():
                if isinstance(items, dict):
                    avail[bank] = sorted(list(items.keys()))
            self.available_presets = avail


    def _load_presets(self):
        try:
            self.presets = load_presets(self.preset_instr.get(), DEFAULT_PRESET_FX)
            # construir índice de presets por banco
            avail = {}
            for bank, items in self.presets.items():
                if isinstance(items, dict):
                    avail[bank] = sorted(list(items.keys()))
            self.available_presets = avail
            banks = ", ".join(sorted(self.presets.keys()))
            messagebox.showinfo("Presets", f"Presets cargados.\nBancos: {banks}")
        except Exception as e:
            messagebox.showwarning("Presets", f"No se pudieron cargar presets:\n{e}")

    # ---------- Carga MIDI ----------
    def _load_midi(self):
        path = self.midi_path.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showwarning("MIDI", "Elegí un archivo .mid/.midi válido desde el combo.")
            return
        self.notes = load_notes(path)
        if not self.notes:
            messagebox.showwarning("MIDI", "No se encontraron notas en el MIDI.")
            return

        # Agrupar por pista
        self.by_track = {}
        for (ti, t0, dur, pitch, vel) in self.notes:
            self.by_track.setdefault(ti, []).append((ti, t0, dur, pitch, vel))

        # Detectar instrumentos/emoji por pista
        detected = detect_midi_instruments(path) if HAS_MIDO else []
        det_map = {ti: (name, emoji) for (ti, name, emoji) in detected}

        # Poblar tabla/configs
        self.tracks_cfg = []
        self.tree.delete(*self.tree.get_children())

        for ti in sorted(self.by_track.keys()):
            cfg = TrackConfig(track_idx=ti)
            name, emoji = det_map.get(ti, ("Unknown", "🎵"))
            cfg.detected = name
            cfg.emoji = emoji

            # Motor sugerido por instrumento GM
            suggested = suggest_synth(name)
            cfg.synth.set(suggested)

            # Preset por defecto según banco y available_presets
            preset_default = self._default_preset_for_bank(suggested)
            cfg.preset.set(preset_default)

            self.tracks_cfg.append(cfg)
            self.tree.insert(
                "", "end", iid=str(ti),
                values=("✔", cfg.synth.get(), cfg.preset.get(), cfg.detected, cfg.emoji)
            )

        messagebox.showinfo("MIDI", f"Notas cargadas: {len(self.notes)}\nPistas: {len(self.tracks_cfg)}")

    def _default_preset_for_bank(self, bank: str) -> str:
        """Devuelve un preset válido para el banco (si hay presets cargados)."""
        if not self.available_presets:
            # Defaults razonables si no hay YAML cargado
            if bank == "kick":
                return "drums.kick_additive"
            if bank == "piano":
                return "piano"
            if bank == "sample":
                return ""
            return "nylon"
        # Tenemos YAML: mapear banco -> lista
        if bank == "kick":
            bank_key = "drums"
            presets = self.available_presets.get(bank_key, [])
            return f"{bank_key}.{presets[0]}" if presets else "drums.kick_additive"
        else:
            bank_key = bank
            presets = self.available_presets.get(bank_key, [])
            if presets:
                # devolver como "bank.preset" para desambiguar
                return f"{bank_key}.{presets[0]}"
            # fallback
            if bank == "piano":
                return "piano"
            if bank == "sample":
                return ""
            return "nylon"

    # ---------- Edición por pista ----------
    def _on_tree_select(self, _evt):
        sel = self.tree.selection()
        if not sel:
            return
        ti = int(sel[0])
        cfg = self._cfg_by_idx(ti)
        self.sel_track_lbl.config(text=f"{ti}")
        # set motor
        self.cmb_synth.set(cfg.synth.get())
        # cargar presets posibles para ese banco y fijar el actual
        self._reload_preset_combo_for_bank(cfg.synth.get())
        self.cmb_preset.set(cfg.preset.get())

    def _cfg_by_idx(self, ti):
        for c in self.tracks_cfg:
            if c.track_idx == ti:
                return c
        return None

    def _on_synth_change(self, _evt=None):
        """Al cambiar de motor en el panel, recargar lista de presets (readonly)."""
        bank = self.cmb_synth.get()
        self._reload_preset_combo_for_bank(bank)

    def _reload_preset_combo_for_bank(self, bank: str):
        # Asegura YAML cargado y diccionario {bank: [presets...]}
        self._ensure_presets_loaded()

        values = []
        if bank == "kick":
            values = [f"drums.{p}" for p in self.available_presets.get("drums", [])]
        elif bank == "sample":
            values = [""]
        else:
            # ks, piano, etc.  ← acá te van a aparecer 'nylon', 'steel', 'electric', 'bass', 'banjo', ...
            values = [f"{bank}.{p}" for p in self.available_presets.get(bank, [])]

        # Si no hay nada (por si faltó banco), fallback mínimo
        if not values and bank == "ks":
            values = [f"ks.{p}" for p in ("nylon", "steel", "electric", "bass", "banjo") if True]

        self.cmb_preset["values"] = values
        if values and not self.cmb_preset.get():
            self.cmb_preset.set(values[0])


    def _apply_to_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Pistas", "Seleccioná una pista en la tabla.")
            return
        ti = int(sel[0])
        cfg = self._cfg_by_idx(ti)
        # aplicar motor/preset desde combos (readonly)
        if self.cmb_synth.get():
            cfg.synth.set(self.cmb_synth.get())
        if self.cmb_preset.get() or self.cmb_synth.get() == "sample":
            cfg.preset.set(self.cmb_preset.get())
        # refrescar fila
        self.tree.set(str(ti), "synth", cfg.synth.get())
        self.tree.set(str(ti), "preset", cfg.preset.get())

    def _apply_to_all(self):
        syn = self.cmb_synth.get()
        pre = self.cmb_preset.get()
        for cfg in self.tracks_cfg:
            if syn:
                cfg.synth.set(syn)
                # recalc preset para ese banco si no hay YAML
                if not self.available_presets and not pre:
                    cfg.preset.set(self._default_preset_for_bank(syn))
            if pre or syn == "sample":
                cfg.preset.set(pre)
            self.tree.set(str(cfg.track_idx), "synth", cfg.synth.get())
            self.tree.set(str(cfg.track_idx), "preset", cfg.preset.get())

    # ---------- Render ----------
    def _render(self):
        if not self.notes:
            messagebox.showwarning("Render", "Cargá un MIDI primero.")
            return
        out = self.out_path.get().strip() or "out.wav"

        # cargar samples si alguna pista usa 'sample'
        use_sample = any(cfg.synth.get() == "sample" for cfg in self.tracks_cfg)
        samples = load_samples(self.sample_dir.get()) if use_sample else None

        # cargar presets si aún no están
        if self.presets is None:
            try:
                self.presets = load_presets(self.preset_instr.get(), DEFAULT_PRESET_FX)
            except Exception:
                self.presets = {}

        tracks_audio = []
        for cfg in self.tracks_cfg:
            if not cfg.enabled.get():
                continue
            ti = cfg.track_idx
            tnotes = [(ti, t0, dur, pitch, vel) for (ti2, t0, dur, pitch, vel) in self.notes if ti2 == ti]
            print(f"[TRK {ti}] → {cfg.synth.get()} ({cfg.preset.get() or 'default'})")

            rf = self._make_renderer(cfg, samples)
            y_trk = lay_notes_on_timeline(tnotes, rf)
            tracks_audio.append(y_trk)

        if not tracks_audio:
            messagebox.showwarning("Render", "No hay pistas habilitadas.")
            return

        y_mix = mix_tracks(tracks_audio, normalize=True, ceiling_dbfs=-1.0)
        if self.reverb_on.get():
            y_mix = simple_reverb(y_mix, SR, mix=float(self.reverb_mix.get()))
        y_mix = _normalize(y_mix)

        write_wav(out, y_mix, SR)
        messagebox.showinfo("Render", f"Archivo generado:\n{out}")

    # ---------- Renderer por pista ----------
    def _make_renderer(self, cfg: TrackConfig, samples):
        synth = cfg.synth.get()
        preset = (cfg.preset.get() or "").strip()

        def get_params(bank_name, preset_name):
            if not self.presets or bank_name not in self.presets:
                return {}
            bank = self.presets[bank_name]
            if preset_name in bank:
                data = dict(bank[preset_name])
                data.pop("transpose", None)
                return data.get("params", data)
            return {}

        if synth == "kick":
            if "." in preset:
                bank, name = preset.split(".", 1)
                kick_p = get_params(bank, name)
            else:
                kick_p = get_params("drums", preset or "kick_additive")
            if not kick_p:
                kick_p = {
                    "dur_s": 0.35,
                    "f_start_hz": 150.0, "f_end_hz": 50.0, "tau_freq_ms": 22.0,
                    "amps": (1.0, 0.5, 0.25, 0.15, 0.10),
                    "ratios": (1.0, 1.6, 2.3, 3.5, 4.2),
                    "tau_amp_ms": (120, 90, 70, 55, 45),
                    "click_ms": 6.0, "click_mix": 0.12, "hp_hz": 22.0, "drive": 0.9,
                }
            print(f"[INFO] KICK usando {preset or 'drums.kick_additive'} params={kick_p}")

            def rf(pitch, dur, vel, sr, _p=kick_p):
                p = dict(_p)
                p["dur_s"] = dur
                y = render_kick_additive(**p)
                return (vel / 127.0) * y
            return rf

        if synth == "ks":
            if "." in preset:
                bank, name = preset.split(".", 1)
                ks_params = get_params(bank, name)
                name_for_preset = name
            else:
                ks_params = get_params("ks", preset or "nylon")
                name_for_preset = preset or "nylon"
            def rf(pitch, dur, vel, sr, _p=ks_params, _n=name_for_preset):
                return render_note_ks(pitch, dur, vel, sr, preset_name=_n, **_p)
            return rf

        if synth == "sample":
            def rf(pitch, dur, vel, sr, _s=samples):
                return render_note_sample(_s, pitch, dur, vel, sr)
            return rf

        if synth == "piano":
            def rf(pitch, dur, vel, sr):
                return render_note_piano_additive(pitch, dur, vel, sr)
            return rf

        raise SystemExit(f"Sintetizador no reconocido: {synth}")

if __name__ == "__main__":
    # Ejecución recomendada:
    # cd "C:\Users\Admin\OneDrive\Documents\GitHub\Sintetizador-de-Instrumentos-Musicales"
    # .venv\Scripts\activate
    # $env:PYTHONPATH="$PWD\src"
    # python -m tpaudio.gui
    App().mainloop()
