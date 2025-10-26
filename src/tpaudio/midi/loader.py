from mido import MidiFile

def load_notes(mid_path: str):
    mid = MidiFile(mid_path)
    notes = []
    for ti, track in enumerate(mid.tracks):
        t = 0.0
        on = {}
        tempo = 500000  # 120 bpm
        tpb = mid.ticks_per_beat
        for msg in track:
            t += msg.time * (tempo / 1e6) / tpb
            if msg.type == "set_tempo":
                tempo = msg.tempo
            elif msg.type == "note_on" and msg.velocity > 0:
                on[msg.note] = (t, msg.velocity)
            elif (msg.type == "note_off") or (msg.type == "note_on" and msg.velocity == 0):
                if msg.note in on:
                    t0, vel = on.pop(msg.note)
                    notes.append((ti, t0, t - t0, msg.note, vel))
    return notes
