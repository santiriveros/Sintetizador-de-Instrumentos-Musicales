# src/tpaudio/gui.py
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import numpy as np

# --- NUEVO: imports para espectrograma ---
import soundfile as sf
import matplotlib.pyplot as plt

# --- Rutas relativas ---
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]  # carpeta Sintetizador-de-Instrumentos-Musicales
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

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
    from tpaudio.synth.adsr import render_kick_additive

    # === efectos integrados (tus clases) ===
    from tpaudio.effects.flanger import Flanger
    from tpaudio.effects.reverb import Reverb
except Exception as e:
    raise RuntimeError(f"No se pudieron importar módulos del paquete tpaudio:\n{e}")

# --- MIDO para detección GM ---
try:
    import mido
    HAS_MIDO = True
except Exception:
    HAS_MIDO = False

# --- Paths relativos de presets y samples ---
DEFAULT_SAMPLE_DIR = PROJECT_ROOT / "samples_piano_1"
DEFAULT_PRESET_INSTR = PROJECT_ROOT / "presets" / "instruments.yml"
DEFAULT_PRESET_FX = PROJECT_ROOT / "presets" / "effects.yml"

def _normalize(y: np.ndarray) -> np.ndarray:
    return (y / (np.max(np.abs(y)) + 1e-9)).astype(np.float32)

# ===== GM program names =====
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

# ===== Emojis por familia =====
INSTRUMENT_EMOJIS = {
    "piano": "🎹", "organ": "🎹", "keyboard": "🎹",
    "guitar": "🎸", "bass": "🎸",
    "violin": "🎻", "cello": "🎻", "strings": "🎻", "harp": "🎻",
    "flute": "🎶", "piccolo": "🎶", "oboe": "🎶", "clarinet": "🎷", "sax": "🎷",
    "trumpet": "🎺", "trombone": "🎺", "horn": "🎺", "tuba": "🎺",
    "drum": "🥁", "percussion": "🥁", "timpani": "🥁",
    "synth": "🎛️", "lead": "🎛️", "pad": "🎛️",
    "voice": "🎤", "vocal": "🎤",
}
def guess_emoji(instr_name: str) -> str:
    n = (instr_name or "").lower()
    for key, emoji in INSTRUMENT_EMOJIS.items():
        if key in n:
            return emoji
    return "🎵"

def suggest_synth(instr_name: str) -> str:
    n = (instr_name or "").lower()
    if "drum" in n or "percussion" in n or "timpani" in n or "cymbal" in n:
        return "kick_adsr"
    if "piano" in n or "keyboard" in n or "organ" in n or "harpsichord" in n:
        return "piano_sample"
    if "guitar" in n or "bass" in n or "string" in n or "violin" in n or "cello" in n or "harp" in n:
        return "ks"
    if "sax" in n or "trumpet" in n or "trombone" in n or "horn" in n or "tuba" in n or "clarinet" in n or "flute" in n:
        return "ks"
    if "synth" in n or "lead" in n or "pad" in n:
        return "ks"
    return "ks"

def detect_midi_instruments(mid_path: str):
    results = []
    if not HAS_MIDO:
        return results
    try:
        mid = mido.MidiFile(mid_path)
        for i, track in enumerate(mid.tracks):
            name = None
            for msg in track:
                if msg.type == "program_change":
                    prog = int(getattr(msg, "program", 0))
                    name = GM_PROGRAM_NAMES[prog] if 0 <= prog < len(GM_PROGRAM_NAMES) else f"Program {prog}"
                    break
            if not name:
                for msg in track:
                    if hasattr(msg, "channel") and int(msg.channel) == 9:
                        name = "Drum Kit (Channel 10)"
                        break
            if not name:
                name = "Unknown / No Program Change"
            results.append((i, name, guess_emoji(name)))
    except Exception as e:
        print("[WARN] Error leyendo instrumentos del MIDI:", e)
    return results

# ===== Helpers =====
def list_mid_files_in_root(root_folder: Path):
    try:
        lst = list(root_folder.glob("*.mid")) + list(root_folder.glob("*.midi"))
        return sorted(lst, key=lambda p: p.name.lower())
    except Exception:
        return []

# ===== GUI =====
class TrackConfig:
    def __init__(self, track_idx: int):
        self.track_idx = track_idx
        self.synth = tk.StringVar(value="ks")
        self.preset = tk.StringVar(value="")
        self.enabled = tk.BooleanVar(value=True)
        self.detected = ""
        self.emoji = "🎵"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TP Audio GUI — Motores: KS / Kick ADSR / Piano Sample + FX")
        self.geometry("1120x780")

        self.midi_path = tk.StringVar()
        self.out_path = tk.StringVar(value="out.wav")

        # ===== Efectos (estado) =====
        # Reverb
        self.reverb_on   = tk.BooleanVar(value=True)
        self.rv_room     = tk.DoubleVar(value=0.5)
        self.rv_decay    = tk.DoubleVar(value=1.8)
        self.rv_predelay = tk.DoubleVar(value=20.0)
        self.rv_bright   = tk.DoubleVar(value=0.6)
        self.rv_mix      = tk.DoubleVar(value=0.25)
        # Flanger
        self.flanger_on  = tk.BooleanVar(value=False)
        self.fl_rate     = tk.DoubleVar(value=0.25)
        self.fl_depth_ms = tk.DoubleVar(value=3.0)
        self.fl_base_ms  = tk.DoubleVar(value=2.0)
        self.fl_feedback = tk.DoubleVar(value=0.2)
        self.fl_mix      = tk.DoubleVar(value=0.5)

        self.tracks_cfg = []
        self.notes = []
        self.by_track = {}
        self.presets = None
        self.available_presets = {}
        self._selected_track_idx = None

        self._midi_paths_cache = {}  # {basename: fullpath}

        # NUEVO: ruta del último WAV efectivamente renderizado
        self._last_rendered_wav: str | None = None

        self._build_ui()

    def _build_ui(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # === Archivos ===
        frm_files = ttk.LabelFrame(container, text="Archivos")
        frm_files.pack(fill="x", pady=6)

        ttk.Label(frm_files, text="Archivo MIDI:").grid(row=0, column=0, padx=6, sticky="e")
        self.cmb_midi = ttk.Combobox(frm_files, state="readonly", width=64, values=[])
        self.cmb_midi.grid(row=0, column=1, padx=6, sticky="w")
        self.cmb_midi.bind("<Button-1>", self._refresh_midi_list)
        self.cmb_midi.bind("<FocusIn>", self._refresh_midi_list)
        self.cmb_midi.bind("<<ComboboxSelected>>", self._on_midi_selected)

        ttk.Button(frm_files, text="Cargar", command=self._load_midi_from_combo).grid(row=0, column=2, padx=6)
        ttk.Button(frm_files, text="Buscar...", command=self._load_midi_from_explorer).grid(row=0, column=3, padx=6)

        ttk.Label(frm_files, text="Salida WAV:").grid(row=1, column=0, padx=6, sticky="e")
        ttk.Entry(frm_files, textvariable=self.out_path, width=64).grid(row=1, column=1, padx=6, sticky="w")
        ttk.Button(frm_files, text="Elegir", command=self._browse_out).grid(row=1, column=2, padx=6)

        # === Efectos (sliders prolijos) ===
        frm_fx = ttk.LabelFrame(container, text="Efectos (sobre la mezcla de todas las pistas habilitadas)")
        frm_fx.pack(fill="x", pady=8)

        # Subframes lado a lado
        fx_left  = ttk.LabelFrame(frm_fx, text="🌊 Reverb")
        fx_right = ttk.LabelFrame(frm_fx, text="🎸 Flanger")
        fx_left.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")
        fx_right.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")
        frm_fx.columnconfigure(0, weight=1)
        frm_fx.columnconfigure(1, weight=1)

        # Reverb controls
        ttk.Checkbutton(fx_left, text="Activar", variable=self.reverb_on).grid(row=0, column=0, sticky="w", padx=6, pady=(6,2))
        self._add_labeled_scale(fx_left, "Tamaño de sala", 0.0, 1.0, self.rv_room, resolution=0.01, row=1)
        self._add_labeled_scale(fx_left, "Duración T60 (s)", 0.3, 5.0, self.rv_decay, resolution=0.1, row=2)
        self._add_labeled_scale(fx_left, "Pre-delay (ms)", 0.0, 80.0, self.rv_predelay, resolution=1.0, row=3)
        self._add_labeled_scale(fx_left, "Brillo", 0.0, 1.0, self.rv_bright, resolution=0.01, row=4)
        self._add_labeled_scale(fx_left, "Mix (dry/wet)", 0.0, 1.0, self.rv_mix, resolution=0.01, row=5)

        # Flanger controls
        ttk.Checkbutton(fx_right, text="Activar", variable=self.flanger_on).grid(row=0, column=0, sticky="w", padx=6, pady=(6,2))
        self._add_labeled_scale(fx_right, "Velocidad LFO (Hz)", 0.05, 2.0, self.fl_rate, resolution=0.01, row=1)
        self._add_labeled_scale(fx_right, "Profundidad (ms)", 0.0, 12.0, self.fl_depth_ms, resolution=0.1, row=2)
        self._add_labeled_scale(fx_right, "Retardo base (ms)", 0.5, 6.0, self.fl_base_ms, resolution=0.1, row=3)
        self._add_labeled_scale(fx_right, "Feedback", -0.95, 0.95, self.fl_feedback, resolution=0.01, row=4)
        self._add_labeled_scale(fx_right, "Mix (dry/wet)", 0.0, 1.0, self.fl_mix, resolution=0.01, row=5)

        # === Pistas ===
        frm_tracks = ttk.LabelFrame(container, text="Pistas")
        frm_tracks.pack(fill="both", expand=True, pady=6)
        self.tree = ttk.Treeview(
            frm_tracks,
            columns=("enabled", "synth", "preset", "instrument", "emoji"),
            show="headings",
            height=16
        )
        for c, t, w in [
            ("enabled", "Usar", 60),
            ("synth", "Motor", 120),
            ("preset", "Preset", 240),
            ("instrument", "Instrumento", 300),
            ("emoji", "🎵", 60),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Button-1>", self._on_tree_click_toggle_enabled)

        frm_edit = ttk.Frame(frm_tracks)
        frm_edit.pack(fill="x", pady=6)
        ttk.Label(frm_edit, text="Motor:").grid(row=0, column=0, padx=6)
        self.cmb_synth = ttk.Combobox(frm_edit, values=["kick_adsr", "ks", "piano_sample"], state="readonly", width=14)
        self.cmb_synth.grid(row=0, column=1, padx=6)
        self.cmb_synth.bind("<<ComboboxSelected>>", self._on_synth_change)

        ttk.Label(frm_edit, text="Preset:").grid(row=0, column=2)
        self.cmb_preset = ttk.Combobox(frm_edit, values=[], state="readonly", width=32)
        self.cmb_preset.grid(row=0, column=3, padx=6)
        ttk.Button(frm_edit, text="Aplicar pista", command=self._apply_to_selected).grid(row=0, column=4, padx=6)

        # === Acciones ===
        bar = ttk.Frame(container)
        bar.pack(fill="x", pady=8)

# Botón de espectrograma: arranca deshabilitado
        self.btn_spec = ttk.Button(bar, text="Ver espectrograma", command=self._show_last_spectrogram)
        self.btn_spec.pack(side="left", padx=6)
        self.btn_spec.state(["disabled"])  # ← importante: deshabilitado correctamente al inicio

        ttk.Button(bar, text="Renderizar WAV", command=self._render).pack(side="right", padx=10)
        ttk.Button(bar, text="Salir", command=self.destroy).pack(side="right", padx=6)


    # --- helper de slider con etiqueta y valor ---
    def _add_labeled_scale(self, parent, label, minv, maxv, var, resolution=0.01, row=0):
        frm = ttk.Frame(parent)
        frm.grid(row=row, column=0, sticky="ew", padx=6, pady=2)
        frm.columnconfigure(1, weight=1)
        ttk.Label(frm, text=label).grid(row=0, column=0, sticky="w", padx=(0,8))
        val_lbl = ttk.Label(frm, width=8, anchor="e")
        val_lbl.grid(row=0, column=2, sticky="e")
        def _upd(v=None):
            val_lbl.config(text=f"{var.get():.2f}")
        scale = ttk.Scale(frm, from_=minv, to=maxv, variable=var, command=lambda _: _upd())
        scale.grid(row=0, column=1, sticky="ew")
        _upd()

    # ---- Helpers GUI ----
    def _refresh_midi_list(self, _evt=None):
        paths = list_mid_files_in_root(PROJECT_ROOT)
        self._midi_paths_cache = {p.name: str(p) for p in paths}
        names = list(self._midi_paths_cache.keys())
        self.cmb_midi["values"] = names
        if names and not self.cmb_midi.get():
            self.cmb_midi.set(names[0])
            self.midi_path.set(self._midi_paths_cache[names[0]])

    def _on_midi_selected(self, _evt=None):
        name = self.cmb_midi.get()
        path = self._midi_paths_cache.get(name)
        if path:
            self.midi_path.set(path)

    def _on_tree_click_toggle_enabled(self, event):
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if col != '#1' or not row:
            return
        try:
            ti = int(row)
        except ValueError:
            return
        current = self.tree.set(row, "enabled")
        new = "✖" if current == "✔" else "✔"
        self.tree.set(row, "enabled", new)
        cfg = self._cfg_by_idx(ti)
        if cfg:
            cfg.enabled.set(new == "✔")
        return "break"

    def _browse_out(self):
        p = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV", "*.wav")], initialdir=str(PROJECT_ROOT))
        if p:
            self.out_path.set(p)

    # ---- Presets ----
    def _ensure_presets_loaded(self):
        if not self.presets:
            try:
                self.presets = load_presets(str(DEFAULT_PRESET_INSTR), str(DEFAULT_PRESET_FX))
            except Exception:
                self.presets = {}
        avail = {}
        for bank, items in (self.presets or {}).items():
            if isinstance(items, dict):
                avail[bank] = sorted(list(items.keys()))
        self.available_presets = avail

    def _reload_preset_combo_for_bank(self, bank: str):
        self._ensure_presets_loaded()
        values = []
        if bank == "kick_adsr":
            values = [f"drums.{p}" for p in self.available_presets.get("drums", [])]
        elif bank == "piano_sample":
            values = []  # solo vacío
        elif bank == "ks":
            values = [f"ks.{p}" for p in self.available_presets.get("ks", [])]
            if not values:
                values = [f"ks.{p}" for p in ("nylon", "steel", "electric", "bass", "banjo")]
        self.cmb_preset["values"] = [""] + values  # siempre incluir vacío

    # ---- MIDI loading (combo / explorador) ----
    def _load_midi_from_combo(self):
        path = self.midi_path.get().strip()
        if not path:
            name = self.cmb_midi.get().strip()
            path = self._midi_paths_cache.get(name, "")
        if not path:
            messagebox.showwarning("MIDI", "Elegí un archivo del combo o usa 'Buscar...'.")
            return
        self._load_midi_common(path)

    def _load_midi_from_explorer(self):
        path = filedialog.askopenfilename(filetypes=[("MIDI", "*.mid *.midi")], initialdir=str(PROJECT_ROOT))
        if not path:
            return
        self.midi_path.set(path)
        p = Path(path)
        if p.parent.resolve() == PROJECT_ROOT.resolve():
            if p.name not in self._midi_paths_cache:
                self._midi_paths_cache[p.name] = str(p)
                self.cmb_midi["values"] = list(self._midi_paths_cache.keys())
            self.cmb_midi.set(p.name)
        else:
            self.cmb_midi.set(p.name)
        self._load_midi_common(path)

    def _load_midi_common(self, path: str):
        notes = load_notes(path)
        if not notes:
            messagebox.showwarning("MIDI", "No se encontraron notas en el MIDI.")
            return
        self.midi_path.set(path)
        self.notes = notes

        # Agrupar por pista
        self.by_track = {}
        for (ti, t0, dur, pitch, vel) in self.notes:
            self.by_track.setdefault(ti, []).append((ti, t0, dur, pitch, vel))

        # Detectar instrumentos GM por pista
        det_map = {}
        if HAS_MIDO:
            detected = detect_midi_instruments(path)
            det_map = {ti: (name, emoji) for (ti, name, emoji) in detected}

        # Poblar tabla
        self.tracks_cfg.clear()
        self.tree.delete(*self.tree.get_children())
        for ti in sorted(self.by_track.keys()):
            cfg = TrackConfig(ti)
            name, emoji = det_map.get(ti, ("Unknown / No Program Change", "🎵"))
            cfg.detected = name
            cfg.emoji = emoji
            cfg.synth.set(suggest_synth(name))
            cfg.preset.set("")  # iniciar en blanco
            self.tracks_cfg.append(cfg)
            self.tree.insert("", "end", iid=str(ti),
                             values=("✔", cfg.synth.get(), cfg.preset.get(), cfg.detected, cfg.emoji))

        messagebox.showinfo("MIDI", f"Notas: {len(self.notes)} | Pistas: {len(self.tracks_cfg)}")

    # ---- Edición ----
    def _on_tree_select(self, _evt):
        sel = self.tree.selection()
        if not sel:
            return
        self._selected_track_idx = int(sel[0])
        cfg = self._cfg_by_idx(self._selected_track_idx)
        self.cmb_synth.set(cfg.synth.get())
        self._reload_preset_combo_for_bank(cfg.synth.get())
        self.cmb_preset.set(cfg.preset.get())

    def _cfg_by_idx(self, ti: int):
        for c in self.tracks_cfg:
            if c.track_idx == ti:
                return c
        return None

    def _on_synth_change(self, _evt=None):
        bank = self.cmb_synth.get()
        self._reload_preset_combo_for_bank(bank)
        self.cmb_preset.set("")  # limpiar visual
        if self._selected_track_idx is not None:
            cfg = self._cfg_by_idx(self._selected_track_idx)
            if cfg:
                cfg.synth.set(bank)
                cfg.preset.set("")  # limpiar en modelo
                self.tree.set(str(cfg.track_idx), "synth", bank)
                self.tree.set(str(cfg.track_idx), "preset", "")

    def _apply_to_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        ti = int(sel[0])
        cfg = self._cfg_by_idx(ti)
        cfg.synth.set(self.cmb_synth.get())
        cfg.preset.set(self.cmb_preset.get())  # puede ser ""
        self.tree.set(str(ti), "synth", cfg.synth.get())
        self.tree.set(str(ti), "preset", cfg.preset.get())

    # ---- Visualización: espectrograma del último WAV renderizado ----
      # ---- Visualización: espectrograma del último WAV renderizado ----
    def _show_spectrogram(self, wav_path: str):
        """Carga el WAV final y muestra su espectrograma en una ventana de Matplotlib."""
        try:
            y, fs = sf.read(wav_path, dtype="float32")
            if y.ndim > 1:
                y = y.mean(axis=1)  # convertir a mono
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el WAV:\n{e}")
            return

        # evitar log(0): agregar piso de ruido muy bajo
        y = y + 1e-12

        plt.close('all')  # cerrar figuras previas
        fig, ax = plt.subplots(figsize=(10, 5))
        Pxx, freqs, bins, im = ax.specgram(
                y,
                NFFT=1024,
                Fs=fs,
                noverlap=512,
                cmap="inferno",
                vmin=-120,  # piso de dB
                vmax=-20    # techo (ajustalo según brillo deseado)
            )
        ax.set_title(f"Espectrograma: {Path(wav_path).name}")
        ax.set_xlabel("Tiempo [s]")
        ax.set_ylabel("Frecuencia [Hz]")
        fig.colorbar(im, ax=ax, label="Amplitud (dB)")
        plt.tight_layout()
        plt.show()

    def _show_last_spectrogram(self):
        """Abre el espectrograma del último WAV realmente generado. Solo habilitado tras el 1er render."""
        if not self._last_rendered_wav:
            # No debería ocurrir porque el botón está deshabilitado hasta el primer render.
            messagebox.showwarning("Espectrograma", "Aún no generaste ningún WAV.")
            return
        p = Path(self._last_rendered_wav)
        if not p.exists():
            messagebox.showwarning("Espectrograma", f"No encuentro el archivo:\n{self._last_rendered_wav}\nVolvé a renderizar.")
            return
        self._show_spectrogram(self._last_rendered_wav)

    # ---- Renderers ----
    def _make_renderer(self, cfg: TrackConfig, samples):
        synth = cfg.synth.get()
        preset = (cfg.preset.get() or "").strip()

        def get_params(bank, name):
            if not self.presets or bank not in self.presets:
                return {}
            bank_data = self.presets[bank]
            if name in bank_data:
                d = dict(bank_data[name])
                d.pop("transpose", None)
                return d.get("params", d)
            return {}

        if synth == "kick_adsr":
            bank, name = ("drums", "kick_additive")
            if preset:
                if "." in preset:
                    bank, name = preset.split(".", 1)
                else:
                    bank, name = "drums", preset
            p = get_params(bank, name) or {
                "dur_s": 0.35,
                "f_start_hz": 150.0, "f_end_hz": 50.0, "tau_freq_ms": 22.0,
                "amps": (1.0, 0.5, 0.25, 0.15, 0.10),
                "ratios": (1.0, 1.6, 2.3, 3.5, 4.2),
                "tau_amp_ms": (120, 90, 70, 55, 45),
                "click_ms": 6.0, "click_mix": 0.12, "hp_hz": 22.0, "drive": 0.9,
            }
            def rf(pitch, dur, vel, sr, _p=p):
                local = dict(_p); local["dur_s"] = dur
                y = render_kick_additive(**local)
                return (vel / 127.0) * y
            return rf

        if synth == "ks":
            name = "nylon"
            if preset:
                name = preset.split(".", 1)[1] if "." in preset else preset
            p = get_params("ks", name) or {}
            def rf(pitch, dur, vel, sr, _p=p, _n=name):
                return render_note_ks(pitch, dur, vel, sr, preset_name=_n, **_p)
            return rf

        if synth == "piano_sample":
            def rf(pitch, dur, vel, sr, _s=samples):
                return render_note_sample(_s, pitch, dur, vel, sr)
            return rf

        raise SystemExit(f"Motor no reconocido: {synth}")

    # ---- Render principal (mezcla + FX) ----
    def _render(self):
        if not self.notes:
            messagebox.showwarning("Render", "Cargá un MIDI primero.")
            return
        out = self.out_path.get().strip() or "out.wav"

        # Cargar presets/samples cuando haga falta
        if not self.presets:
            try:
                self.presets = load_presets(str(DEFAULT_PRESET_INSTR), str(DEFAULT_PRESET_FX))
            except Exception:
                self.presets = {}
        needs_samples = any(cfg.synth.get() == "piano_sample" for cfg in self.tracks_cfg)
        samples = load_samples(str(DEFAULT_SAMPLE_DIR)) if needs_samples else None

        # Render por pista
        tracks_audio = []
        for cfg in self.tracks_cfg:
            if not cfg.enabled.get():
                continue
            tnotes = [n for n in self.notes if n[0] == cfg.track_idx]
            rf = self._make_renderer(cfg, samples)
            y = lay_notes_on_timeline(tnotes, rf)
            tracks_audio.append(y)

        if not tracks_audio:
            messagebox.showwarning("Render", "No hay pistas habilitadas.")
            return

        # Mezcla
        y_mix = mix_tracks(tracks_audio, normalize=True, ceiling_dbfs=-1.0)

        # === Aplicación de FX sobre la mezcla ===
        # 1) Flanger (antes que la reverb por efecto creativo tipo "chorus metálico")
        if self.flanger_on.get():
            fl = Flanger(
                rate_hz=float(self.fl_rate.get()),
                depth_ms=float(self.fl_depth_ms.get()),
                base_ms=float(self.fl_base_ms.get()),
                feedback=float(self.fl_feedback.get()),
                mix=float(self.fl_mix.get()),
            )
            y_mix = fl.process(y_mix.astype(np.float64), SR).astype(np.float32)

        # 2) Reverb (cola final)
        if self.reverb_on.get():
            rv = Reverb(
                room_size=float(self.rv_room.get()),
                decay_s=float(self.rv_decay.get()),
                pre_delay_ms=float(self.rv_predelay.get()),
                brightness=float(self.rv_bright.get()),
                mix=float(self.rv_mix.get()),
            )
            y_mix = rv.process(y_mix.astype(np.float64), SR).astype(np.float32)

        # Normaliza y escribe WAV
        y_out = _normalize(y_mix)
        write_wav(out, y_out, SR)

        # Guardar ruta del último WAV y habilitar botón espectrograma
        self._last_rendered_wav = out
        self.btn_spec.state(["!disabled"])

        # Mensaje adaptativo según uso de FX
        fx_active = self.flanger_on.get() or self.reverb_on.get()
        fx_text = "con FX" if fx_active else "sin FX"
        messagebox.showinfo("Render", f"Archivo generado {fx_text}:\n{out}")

if __name__ == "__main__":
    App().mainloop()
