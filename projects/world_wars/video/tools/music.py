"""Synthesize the film's quiet, sombre background score (original, no licence needed).

Slow minor-key pad chords with a low drone and a soft high bell every few bars.
Usage: python3 tools/music.py <seconds>  ->  assets/music/score.mp3
"""
import os, subprocess, sys
import numpy as np

SR = 44100
dur = float(sys.argv[1]) if len(sys.argv) > 1 else 1200
n = int(SR * dur)
t = np.arange(n) / SR
rng = np.random.default_rng(7)

def hz(m):  # midi -> Hz
    return 440.0 * 2 ** ((m - 69) / 12)

# D minor: Dm  Bb  F  C  | Dm  Gm  Bb  A
prog = [[50, 57, 62, 65], [46, 53, 58, 62], [41, 53, 57, 60], [48, 55, 60, 64],
        [50, 57, 62, 65], [43, 55, 58, 62], [46, 53, 58, 65], [45, 52, 57, 61]]
CH = 9.0  # seconds per chord
out = np.zeros(n)

for k in range(int(dur / CH) + 2):
    chord = prog[k % len(prog)]
    s0 = int(k * CH * SR)
    L = int((CH + 4.0) * SR)            # overlap into next chord
    s1 = min(n, s0 + L)
    if s0 >= n:
        break
    tt = np.arange(s1 - s0) / SR
    env = np.minimum(1, tt / 3.0) * np.minimum(1, np.maximum(0, (CH + 4.0 - tt) / 4.0))
    seg = np.zeros(s1 - s0)
    for i, m in enumerate(chord):
        f = hz(m + 12 * (i > 0))
        det = 1 + 0.0025 * np.sin(2 * np.pi * 0.11 * tt + i)
        # soft string-like tone: fundamental + a few weak harmonics, slightly detuned pair
        for h, a in [(1, 1.0), (2, 0.28), (3, 0.12), (4, 0.05)]:
            seg += a * (np.sin(2 * np.pi * f * h * det * tt) + 0.6 * np.sin(2 * np.pi * f * h * 1.003 * tt + 1.3))
    out[s0:s1] += 0.05 * env * seg
    # a bell on every second chord
    if k % 2 == 0:
        bf = hz(chord[-1] + 24)
        bt = tt[: int(5 * SR)]
        bell = np.exp(-bt * 1.4) * (np.sin(2 * np.pi * bf * bt) + 0.3 * np.sin(2 * np.pi * bf * 2.76 * bt))
        out[s0 + int(1.5 * SR): s0 + int(1.5 * SR) + len(bell)] += 0.035 * bell[: max(0, min(len(bell), n - s0 - int(1.5 * SR)))]

# low drone on D with slow breathing
out += 0.06 * (0.7 + 0.3 * np.sin(2 * np.pi * t / 23)) * (np.sin(2 * np.pi * hz(38) * t) + 0.4 * np.sin(2 * np.pi * hz(45) * t))
# faint wind noise, low-passed by a moving average
noise = rng.standard_normal(n)
k = 400
noise = np.convolve(noise, np.ones(k) / k, mode="same")
out += 0.25 * noise * (0.6 + 0.4 * np.sin(2 * np.pi * t / 37))

# fade in/out, normalise
fade = int(4 * SR)
out[:fade] *= np.linspace(0, 1, fade)
out[-fade:] *= np.linspace(1, 0, fade)
out = out / np.max(np.abs(out)) * 0.8
pcm = (out * 32767).astype("<i2").tobytes()
os.makedirs("assets/music", exist_ok=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-",
                "-af", "aecho=0.8:0.7:120|260:0.25|0.15,loudnorm=I=-20:TP=-2", "-b:a", "160k",
                "assets/music/score.mp3"], input=pcm, check=True)
print("ok", dur)
