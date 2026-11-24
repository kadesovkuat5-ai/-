"""Make one voice file per narration line with Piper (ISSAI Kazakh voice, CC-BY-4.0).

Usage: python3 tools/tts.py <voices_dir>
Writes assets/voice/<chapter>_<nn>.wav and tools/voice_timing.json.
Lines are cached: a file is only re-made when its text or voice changes.
"""
import hashlib, json, os, subprocess, sys, wave

sys.path.insert(0, os.path.dirname(__file__))
from story import CHAPTERS

VOICES = sys.argv[1]
MODEL = os.path.join(VOICES, "kk_KZ-issai-high.onnx")
SPEAKER = {"A": 0, "E": 4}          # A: ISSAI male (M2), E: ISSAI female (F1)
LENGTH = {"A": 1.12, "E": 1.0}      # >1 speaks slower
ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "assets", "voice")
os.makedirs(OUT, exist_ok=True)

timing = {}
for ch in CHAPTERS:
    for i, line in enumerate(ch["lines"]):
        name = f"{ch['id']}_{i:02d}"
        text = line.get("s", line["t"])
        key = hashlib.sha1(f"{text}|{line['who']}|{LENGTH[line['who']]}".encode()).hexdigest()[:12]
        wav = os.path.join(OUT, name + ".wav")
        stamp = wav + ".key"
        if not (os.path.exists(wav) and os.path.exists(stamp) and open(stamp).read() == key):
            raw = wav + ".raw.wav"
            subprocess.run(["python3", "-m", "piper", "-m", MODEL, "-s", str(SPEAKER[line["who"]]),
                            "--length-scale", str(LENGTH[line["who"]]), "--sentence-silence", "0.25",
                            "-f", raw], input=text.encode(), check=True, capture_output=True)
            # trim edge silence, gentle loudness match, 44.1 kHz mono
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
                            "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                            "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                            "loudnorm=I=-17:TP=-2:LRA=7", "-ar", "44100", "-ac", "1", wav], check=True)
            os.remove(raw)
            open(stamp, "w").write(key)
        with wave.open(wav) as w:
            timing[name] = round(w.getnframes() / w.getframerate(), 3)
        print(name, timing[name], flush=True)

json.dump(timing, open(os.path.join(os.path.dirname(__file__), "voice_timing.json"), "w"), indent=1)
print("TOTAL", round(sum(timing.values()), 1), "s")
