# src/tpaudio/gui.py
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import numpy as np
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
    from tpaudio.core.mixer import mix_tracks
    from tpaudio.midi.loader import load_notes

    from tpaudio.synth.karplus import render_note_ks
    from tpaudio.synth.sample_piano import load_samples, render_note_sample
    from tpaudio.synth.adsr import render_kick_additive

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


# ===== GM y emojis =====
# Lista reducida + uso de módulo para no explotar si el prog excede
GM_PROGRAM_NAMES = [
    "Acoustic Grand Piano","Bright Acoustic Piano","Electric Grand Piano","Honky-tonk Piano",
    "Electric Piano 1","Electric Piano 2","Harpsichord","Clavinet",
    "Acoustic Guitar (nylon)","Acoustic Guitar (steel)","Electric Guitar (jazz)","Electric Guitar (clean)",
    "Violin","Viola","Cello","Contrabass",
    "String Ensemble 1","String Ensemble 2","SynthStrings 1","SynthStrings 2",
    "Trumpet","Trombone","Tuba","French Horn",
    "Soprano Sax","Alto Sax","Tenor Sax","Baritone Sax",
    "Flute","Oboe","Clarinet","Bassoon",
    "Synth Bass 1","Synth Bass 2","Lead 1 (square)","Lead 2 (sawtooth)"
]
INSTRUMENT_EMOJIS = {
    "piano": "🎹", "organ": "🎹", "keyboard": "🎹",
    "guitar": "🎸", "bass": "🎸",
    "violin": "🎻", "cello": "🎻", "strings": "🎻", "harp": "🎻",
    "flute": "🎶", "piccolo": "🎶", "oboe": "🎶", "clarinet": "🎷", "sax": "🎷",
    "trumpet": "🎺", "trombone": "🎺", "horn": "🎺", "tuba": "🎺",
    "drum": "🥁", "percussion": "🥁", "timpani": "🥁",
    "synth": "🎛️", "lead": "🎛️", "pad": "🎛️",
    "voice": "🎤",
}


def guess_emoji(name: str) -> str:
    n = (name or "").lower()
    for k, e in INSTRUMENT_EMOJIS.items():
        if k in n:
            return e
    return "🎵"


def suggest_synth(name: str) -> str:
    n = (name or "").lower()
    if "drum" in n or "perc" in n or "timpani" in n or "cymbal" in n:
        return "kick_adsr"
    if "piano" in n or "organ" in n or "keyboard" in n or "harpsichord" in n:
        return "piano_sample"
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
                    name = GM_PROGRAM_NAMES[prog % len(GM_PROGRAM_NAMES)]
                    break
            if not name:
                # detectar drums si aparece canal 10
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
        self.volume = tk.DoubleVar(value=1.0)  # 🔊 volumen 0–1 por pista
        self.detected = ""
        self.emoji = "🎵"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TP Audio GUI — KS / Kick ADSR / Piano Sample + FX + Volumen por pista")
        self.geometry("1140x800")

        self.midi_path = tk.StringVar()
        self.out_path = tk.StringVar(value="out.wav")

        # === Estado de efectos globales ===
        self.reverb_on = tk.BooleanVar(value=True)
        self.rv_room = tk.DoubleVar(value=0.5)
        self.rv_decay = tk.DoubleVar(value=1.8)
        self.rv_predelay = tk.DoubleVar(value=20.0)
        self.rv_bright = tk.DoubleVar(value=0.6)
        self.rv_mix = tk.DoubleVar(value=0.25)

        self.flanger_on = tk.BooleanVar(value=False)
        self.fl_rate = tk.DoubleVar(value=0.25)
        self.fl_depth_ms = tk.DoubleVar(value=3.0)
        self.fl_base_ms = tk.DoubleVar(value=2.0)
        self.fl_feedback = tk.DoubleVar(value=0.2)
        self.fl_mix = tk.DoubleVar(value=0.5)

        self.tracks_cfg = []
        self.notes = []
        self.by_track = {}
        self.presets = None
        self.available_presets = {}
        self._selected_track_idx = None
        self._note_cache = {}
        self._midi_paths_cache = {}
        self._last_rendered_wav = None

        self._build_ui()

    # === UI ===
    def _build_ui(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # === Archivos ===
        frm_files = ttk.LabelFrame(container, text="Archivos")
        frm_files.pack(fill="x", pady=6)

        ttk.Label(frm_files, text="Archivo MIDI:").grid(row=0, column=0, padx=6, sticky="e")
        self.cmb_midi = ttk.Combobox(frm_files, state="readonly", width=64)
        self.cmb_midi.grid(row=0, column=1, padx=6, sticky="w")
        self.cmb_midi.bind("<Button-1>", self._refresh_midi_list)
        self.cmb_midi.bind("<<ComboboxSelected>>", self._on_midi_selected)
        ttk.Button(frm_files, text="Cargar", command=self._load_midi_from_combo).grid(row=0, column=2, padx=6)
        ttk.Button(frm_files, text="Buscar...", command=self._load_midi_from_explorer).grid(row=0, column=3, padx=6)

        ttk.Label(frm_files, text="Salida WAV:").grid(row=1, column=0, padx=6, sticky="e")
        ttk.Entry(frm_files, textvariable=self.out_path, width=64).grid(row=1, column=1, padx=6, sticky="w")
        ttk.Button(frm_files, text="Elegir", command=self._browse_out).grid(row=1, column=2, padx=6)

        # === FX (solo switches acá para no recargar UI) ===
        frm_fx = ttk.LabelFrame(container, text="Efectos globales (se aplican sobre la mezcla)")
        frm_fx.pack(fill="x", pady=8)
        ttk.Checkbutton(frm_fx, text="Reverb", variable=self.reverb_on).grid(row=0, column=0, padx=6)
        ttk.Checkbutton(frm_fx, text="Flanger", variable=self.flanger_on).grid(row=0, column=1, padx=6)

        # === Pistas ===
        frm_tracks = ttk.LabelFrame(container, text="Pistas (con volumen por pista)")
        frm_tracks.pack(fill="both", expand=True, pady=6)
        self.tree = ttk.Treeview(
            frm_tracks,
            columns=("enabled", "synth", "vol", "preset", "instrument", "emoji"),
            show="headings", height=16
        )
        for c, t, w, anchor in [
            ("enabled", "Usar", 60, "center"),
            ("synth", "Motor", 120, "center"),
            ("vol", "Vol", 70, "center"),
            ("preset", "Preset", 200, "center"),
            ("instrument", "Instrumento", 300, "center"),
            ("emoji", "🎵", 60, "center"),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor=anchor)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Edición
        frm_edit = ttk.Frame(frm_tracks)
        frm_edit.pack(fill="x", pady=6)
        ttk.Label(frm_edit, text="Motor:").grid(row=0, column=0, padx=6)
        self.cmb_synth = ttk.Combobox(frm_edit, values=["kick_adsr", "ks", "piano_sample"],
                                      state="readonly", width=14)
        self.cmb_synth.grid(row=0, column=1, padx=6)
        self.cmb_synth.bind("<<ComboboxSelected>>", self._on_synth_change)
        ttk.Label(frm_edit, text="Preset:").grid(row=0, column=2)
        self.cmb_preset = ttk.Combobox(frm_edit, values=[], state="readonly", width=32)
        self.cmb_preset.grid(row=0, column=3, padx=6)
        ttk.Button(frm_edit, text="Aplicar pista", command=self._apply_to_selected).grid(row=0, column=4, padx=6)

        # 🔊 Slider de volumen
        ttk.Label(frm_edit, text="Volumen:").grid(row=1, column=0, padx=6, sticky="e")
        self.edit_vol = tk.DoubleVar(value=1.0)
        frm_vol = ttk.Frame(frm_edit)
        frm_vol.grid(row=1, column=1, columnspan=3, sticky="ew", padx=6)
        frm_vol.columnconfigure(0, weight=1)
        self.sld_vol = ttk.Scale(frm_vol, from_=0.0, to=1.0, orient="horizontal",
                                 variable=self.edit_vol,
                                 command=lambda _: self._on_volume_change_live())
        self.sld_vol.grid(row=0, column=0, sticky="ew")
        self.lbl_vol_val = ttk.Label(frm_vol, text="1.00", width=6, anchor="e")
        self.lbl_vol_val.grid(row=0, column=1, padx=(6, 0))

        # === Acciones ===
        bar = ttk.Frame(container)
        bar.pack(fill="x", pady=8)
        self.btn_spec = ttk.Button(bar, text="Ver espectrograma", command=self._show_last_spectrogram)
        self.btn_spec.pack(side="left", padx=6)
        self.btn_spec.state(["disabled"])
        ttk.Button(bar, text="Renderizar WAV", command=self._render).pack(side="right", padx=10)
        ttk.Button(bar, text="Salir", command=self.destroy).pack(side="right", padx=6)

    # === Funciones auxiliares ===
    def _refresh_midi_list(self, _=None):
        paths = list_mid_files_in_root(PROJECT_ROOT)
        self._midi_paths_cache = {p.name: str(p) for p in paths}
        names = list(self._midi_paths_cache.keys())
        self.cmb_midi["values"] = names
        if names:
            self.cmb_midi.set(names[0])
            self.midi_path.set(self._midi_paths_cache[names[0]])

    def _on_midi_selected(self, _=None):
        name = self.cmb_midi.get()
        path = self._midi_paths_cache.get(name)
        if path:
            self.midi_path.set(path)

    def _browse_out(self):
        p = filedialog.asksaveasfilename(defaultextension=".wav",
                                         filetypes=[("WAV", "*.wav")],
                                         initialdir=str(PROJECT_ROOT))
        if p:
            self.out_path.set(p)

    def _load_midi_from_combo(self):
        path = self.midi_path.get().strip()
        if not path:
            messagebox.showwarning("MIDI", "Elegí un archivo.")
            return
        self._load_midi_common(path)

    def _load_midi_from_explorer(self):
        path = filedialog.askopenfilename(filetypes=[("MIDI", "*.mid *.midi")],
                                          initialdir=str(PROJECT_ROOT))
        if path:
            self._load_midi_common(path)

    def _load_midi_common(self, path: str):
        notes = load_notes(path)
        if not notes:
            messagebox.showwarning("MIDI", "No se encontraron notas.")
            return
        self.notes = notes
        self.by_track.clear()
        for (ti, t0, dur, pitch, vel) in self.notes:
            self.by_track.setdefault(ti, []).append((ti, t0, dur, pitch, vel))
        det_map = {ti: (name, emoji) for (ti, name, emoji) in detect_midi_instruments(path)}
        self.tree.delete(*self.tree.get_children())
        self.tracks_cfg.clear()
        for ti in sorted(self.by_track.keys()):
            cfg = TrackConfig(ti)
            name, emoji = det_map.get(ti, ("Unknown / No Program Change", "🎵"))
            cfg.detected = name
            cfg.emoji = emoji
            cfg.synth.set(suggest_synth(name))
            self.tracks_cfg.append(cfg)
            self.tree.insert("", "end", iid=str(ti),
                             values=("✔", cfg.synth.get(), f"{cfg.volume.get():.2f}",
                                     cfg.preset.get(), cfg.detected, cfg.emoji))
        self._note_cache.clear()
        messagebox.showinfo("MIDI", f"Pistas: {len(self.tracks_cfg)}  |  Notas: {len(self.notes)}")

    # === Edición ===
    def _on_tree_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        ti = int(sel[0])
        self._selected_track_idx = ti
        cfg = self._cfg_by_idx(ti)
        self.cmb_synth.set(cfg.synth.get())
        self.cmb_preset.set(cfg.preset.get())
        self.edit_vol.set(cfg.volume.get())
        self.lbl_vol_val.config(text=f"{cfg.volume.get():.2f}")

    def _cfg_by_idx(self, ti):
        for c in self.tracks_cfg:
            if c.track_idx == ti:
                return c
        return None

    def _on_synth_change(self, _=None):
        if self._selected_track_idx is None:
            return
        cfg = self._cfg_by_idx(self._selected_track_idx)
        if cfg:
            cfg.synth.set(self.cmb_synth.get())
            cfg.preset.set("")
            self.tree.set(str(cfg.track_idx), "synth", cfg.synth.get())
            self.tree.set(str(cfg.track_idx), "preset", "")
        self._note_cache.clear()

    def _on_volume_change_live(self):
        """Actualizar volumen y reflejarlo en la tabla."""
        self.lbl_vol_val.config(text=f"{self.edit_vol.get():.2f}")
        if self._selected_track_idx is None:
            return
        cfg = self._cfg_by_idx(self._selected_track_idx)
        cfg.volume.set(self.edit_vol.get())
        self.tree.set(str(cfg.track_idx), "vol", f"{cfg.volume.get():.2f}")

    def _apply_to_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        ti = int(sel[0])
        cfg = self._cfg_by_idx(ti)
        cfg.synth.set(self.cmb_synth.get())
        cfg.preset.set(self.cmb_preset.get())
        cfg.volume.set(self.edit_vol.get())
        self.tree.set(str(ti), "synth", cfg.synth.get())
        self.tree.set(str(ti), "preset", cfg.preset.get())
        self.tree.set(str(ti), "vol", f"{cfg.volume.get():.2f}")
        self._note_cache.clear()

    # === Espectrograma ===
    def _show_spectrogram(self, wav_path: str):
        try:
            y, fs = sf.read(wav_path, dtype="float32")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer el WAV:\n{e}")
            return
        plt.close("all")
        if y.ndim == 1:
            fig, ax = plt.subplots(figsize=(10, 5))
            sig = y + 1e-12
            _, _, _, im = ax.specgram(sig, NFFT=1024, Fs=fs, noverlap=512,
                                      cmap="inferno", vmin=-120, vmax=-20)
            ax.set_title(Path(wav_path).name)
            ax.set_xlabel("Tiempo [s]"); ax.set_ylabel("Frecuencia [Hz]")
            fig.colorbar(im, ax=ax, pad=0.02).set_label("Amplitud [dB]")
        else:
            fig, (axL, axR) = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
            sigL = y[:, 0] + 1e-12; sigR = y[:, 1] + 1e-12
            _, _, _, imL = axL.specgram(sigL, NFFT=1024, Fs=fs, noverlap=512, cmap="inferno", vmin=-120, vmax=-20)
            _, _, _, imR = axR.specgram(sigR, NFFT=1024, Fs=fs, noverlap=512, cmap="inferno", vmin=-120, vmax=-20)
            axL.set_title("Left"); axR.set_title("Right")
            for ax in (axL, axR): ax.set_xlabel("Tiempo [s]")
            axL.set_ylabel("Frecuencia [Hz]")
            fig.colorbar(imR, ax=[axL, axR], pad=0.02).set_label("Amplitud [dB]")
        plt.tight_layout(); plt.show()

    def _show_last_spectrogram(self):
        if not self._last_rendered_wav:
            messagebox.showwarning("Espectrograma", "No hay WAV generado aún.")
            return
        self._show_spectrogram(self._last_rendered_wav)

    # ====== OPTIMIZACIONES: caché de notas + timeline rápido ======
    def _cached_note(self, rf, pitch, dur, vel):
        """Devuelve el audio de una nota cacheada por (id(rf), pitch, dur_ms, vel_bin)."""
        dur_ms = int(round(dur * 1000))
        vel_bin = int(vel) // 2
        key = (id(rf), pitch, dur_ms, vel_bin)
        seg = self._note_cache.get(key)
        if seg is None:
            seg = rf(pitch, dur, vel, SR)
            if seg.dtype != np.float32:
                seg = seg.astype(np.float32, copy=False)
            self._note_cache[key] = seg
        return seg

    def _lay_notes_on_timeline_fast(self, notes, rf, sr=SR):
        """Versión rápida: usa cache por nota y suma por slicing. 'notes' es una lista de UNA pista."""
        if not notes:
            return np.zeros(1, dtype=np.float32)
        t_end = max(t0 + dur for (_ti, t0, dur, _p, _v) in notes)
        n = int(np.ceil(t_end * sr)) + 1
        y = np.zeros(n, dtype=np.float32)
        for (_ti, t0, dur, pitch, vel) in notes:
            seg = self._cached_note(rf, pitch, dur, vel)
            i0 = int(round(t0 * sr))
            i1 = min(i0 + len(seg), n)
            if i0 < n:
                y[i0:i1] += seg[:i1 - i0]
        return y

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

        # Render por pista (rápido)
        tracks_audio = []
        for cfg in self.tracks_cfg:
            if not cfg.enabled.get():
                continue
            tnotes = self.by_track.get(cfg.track_idx, [])  # O(1)
            rf = self._make_renderer(cfg, samples)
            y = self._lay_notes_on_timeline_fast(tnotes, rf)
            # aplicar volumen por pista
            vol = float(cfg.volume.get())
            if vol != 1.0:
                y = (y * vol).astype(np.float32, copy=False)
            tracks_audio.append(y)

        if not tracks_audio:
            messagebox.showwarning("Render", "No hay pistas habilitadas.")
            return

        # Mezcla sin normalizar (normalizamos una sola vez al final)
        y_mix = mix_tracks(tracks_audio, normalize=False)

        # === FX sólo si están activos (evita casts/cópias si OFF) ===
        if self.flanger_on.get():
            fl = Flanger(
                rate_hz=float(self.fl_rate.get()),
                depth_ms=float(self.fl_depth_ms.get()),
                base_ms=float(self.fl_base_ms.get()),
                feedback=float(self.fl_feedback.get()),
                mix=float(self.fl_mix.get()),
            )
            y_mix = fl.process(y_mix.astype(np.float64), SR).astype(np.float32)

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

        # Guardar ruta del último WAV y habilitar espectrograma
        self._last_rendered_wav = out
        self.btn_spec.state(["!disabled"])

        # Mensaje adaptativo según FX
        fx_active = self.flanger_on.get() or self.reverb_on.get()
        fx_text = "con FX" if fx_active else "sin FX"
        messagebox.showinfo("Render", f"Archivo generado {fx_text}:\n{out}")


if __name__ == "__main__":
    App().mainloop()
