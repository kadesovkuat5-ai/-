#!/usr/bin/env python3
"""
ReelKit: turn raw footage into a CapCut-ready editing kit for Instagram Reels.

    python3 reelkit/reelkit.py analyze input/ --language kk   # 1. look at the footage
    python3 reelkit/reelkit.py plan --target 30               # 2. make an edit plan (work/edit.json)
    python3 reelkit/reelkit.py build --name my_reel           # 3. build the kit (output/my_reel_capcut_kit.zip)
    python3 reelkit/reelkit.py all input/ --language kk       #    or all three in one go

The kit contains SEPARATE files you keep editing in CapCut (clips, voice, music, sound
effects, subtitles) plus a PREVIEW MP4. The preview is a flat video, not an editable
project: CapCut on iPhone cannot reopen it as layers.

Needs: Python 3.9+, ffmpeg/ffprobe. Optional: `pip install faster-whisper` for subtitles.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SFX_DIR = HERE / "sfx"
WORK = ROOT / "work"
OUTPUT = ROOT / "output"
W, H, FPS = 1080, 1920, 30
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".3gp"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}
HDR_TRC = {"arib-std-b67", "smpte2084"}

os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # plain HTTPS model download (works behind strict proxies)


# ----------------------------------------------------------------------------
# small helpers
# ----------------------------------------------------------------------------
def log(msg: str) -> None:
    print(msg, flush=True)


def run(cmd: list, capture: bool = False, cwd: Path | None = None) -> str:
    """Run ffmpeg/ffprobe. Returns stderr+stdout text when capture=True."""
    res = subprocess.run([str(c) for c in cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd)
    if res.returncode != 0:
        sys.stderr.write(res.stderr[-3000:])
        raise SystemExit(f"\nCommand failed: {' '.join(str(c) for c in cmd[:6])} ...")
    return (res.stdout or "") + (res.stderr or "") if capture else ""


def run_in(folder: Path, cmd: list) -> None:
    """Run inside a folder (the subtitle filter reads 'subs.ass' by a simple relative name)."""
    run(cmd, cwd=folder)


def tc(sec: float) -> str:
    """Timeline clock for humans: 0:07.40"""
    sec = max(0.0, sec)
    return f"{int(sec // 60)}:{sec % 60:05.2f}"


def srt_time(sec: float) -> str:
    ms = int(round(max(0.0, sec) * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ass_time(sec: float) -> str:
    cs = int(round(max(0.0, sec) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def frames(sec: float) -> float:
    """Snap a duration/time to the 30 fps frame grid so every file lines up exactly."""
    return round(sec * FPS) / FPS


def slug(text: str, n: int = 24) -> str:
    s = re.sub(r"[^\w]+", "_", Path(text).stem, flags=re.UNICODE).strip("_")
    return (s or "clip")[:n]


def load_json(path: Path):
    if not path.exists():
        raise SystemExit(f"Missing {path.relative_to(ROOT)}. Run the previous step first.")
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def rel(p) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


# ----------------------------------------------------------------------------
# 1. ANALYZE
# ----------------------------------------------------------------------------
def probe(path: Path) -> dict:
    data = json.loads(run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format",
                           "-show_streams", path], capture=True))
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    if not v:
        raise SystemExit(f"{path.name}: no video stream found")
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(float(sd["rotation"]))
    rot = rot or int(v.get("tags", {}).get("rotate", 0))
    w, h = int(v["width"]), int(v["height"])
    if abs(rot) % 180 == 90:
        w, h = h, w
    num, _, den = v.get("avg_frame_rate", "30/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    return {
        "duration": float(data["format"].get("duration") or v.get("duration") or 0),
        "width": w, "height": h, "fps": round(fps, 3),
        "codec": v.get("codec_name"), "has_audio": a is not None,
        "hdr": v.get("color_transfer") in HDR_TRC, "color_transfer": v.get("color_transfer"),
    }


def detect_silences(path: Path) -> list:
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0", "-af",
               "silencedetect=noise=-35dB:d=0.35", "-f", "null", "-"], capture=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return [[round(s, 2), round(e, 2)] for s, e in zip(starts, ends + [None] * len(starts)) if e]


def detect_scenes(path: Path) -> list:
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-an", "-vf",
               "scale=320:-2,select='gt(scene,0.32)',showinfo", "-f", "null", "-"], capture=True)
    return [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", out)]


def measure_brightness(path: Path) -> float | None:
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-an", "-vf",
               "fps=1,scale=160:-2,format=yuv420p,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
               "-f", "null", "-"], capture=True)
    vals = [float(x) for x in re.findall(r"YAVG=([\d.]+)", out)]
    return round(sum(vals) / len(vals), 1) if vals else None


def measure_loudness(path: Path) -> float | None:
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-map", "0:a:0", "-af",
               "loudnorm=print_format=json", "-f", "null", "-"], capture=True)
    m = re.search(r'"input_i"\s*:\s*"(-?[\d.]+|-inf)"', out)
    return float(m.group(1)) if m and m.group(1) != "-inf" else None


_whisper = None


def transcribe(path: Path, language: str | None, model_name: str) -> dict:
    global _whisper
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log("   ! faster-whisper not installed: skipping subtitles (pip install faster-whisper)")
        return {"language": None, "words": []}
    if _whisper is None:
        log(f"   loading Whisper '{model_name}' model (first time downloads ~0.5 GB)…")
        _whisper = WhisperModel(model_name, device="cpu", compute_type="int8")
    import numpy as np  # decode with ffmpeg ourselves: avoids PyAV version problems
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path), "-map", "0:a:0",
                          "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], stdout=subprocess.PIPE, check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    segments, info = _whisper.transcribe(audio, language=language, word_timestamps=True,
                                         vad_filter=True, beam_size=5)
    words = []
    for seg in segments:
        for w in seg.words or []:
            text = w.word.strip()
            if text:
                words.append({"start": round(w.start, 2), "end": round(w.end, 2), "text": text})
    return {"language": info.language, "words": words}


def cmd_analyze(args) -> None:
    files = []
    for p in args.inputs:
        p = Path(p)
        files += sorted(f for f in p.iterdir() if f.suffix.lower() in VIDEO_EXT) if p.is_dir() else [p]
    if not files:
        raise SystemExit("No video files found. Put your raw footage in the input/ folder.")
    sources = []
    for i, f in enumerate(files, 1):
        log(f"[{i}/{len(files)}] Analyzing {f.name}")
        info = probe(f)
        src = {"id": f"S{i}", "file": rel(f), "name": f.name, **info}
        src["scenes"] = detect_scenes(f)
        src["brightness"] = measure_brightness(f)
        if info["has_audio"]:
            src["silences"] = detect_silences(f)
            src["loudness_lufs"] = measure_loudness(f)
            src["transcript"] = {"language": None, "words": []} if args.no_transcribe else \
                transcribe(f, args.language, args.model)
        else:
            src.update(silences=[], loudness_lufs=None, transcript={"language": None, "words": []})
        n_words = len(src["transcript"]["words"])
        log(f"   {info['width']}x{info['height']} {info['duration']:.1f}s, {len(src['scenes'])} scene cuts, "
            f"{n_words} words{' (HDR)' if info['hdr'] else ''}")
        sources.append(src)
    save_json(WORK / "analysis.json", {"sources": sources})
    log(f"\n✓ Saved {rel(WORK / 'analysis.json')}")


# ----------------------------------------------------------------------------
# 2. PLAN – automatic first cut (Claude or you can then edit work/edit.json)
# ----------------------------------------------------------------------------
def speech_segments(words: list, dur: float) -> list:
    """Keep the parts where someone talks; drop pauses longer than ~0.45 s."""
    segs = []
    for w in words:
        s, e = max(0.0, w["start"] - 0.12), min(dur, w["end"] + 0.18)
        if segs and s - segs[-1][1] < 0.3:
            segs[-1][1] = max(segs[-1][1], e)
        else:
            segs.append([s, e])
    return [s for s in segs if s[1] - s[0] >= 0.5]


def visual_segments(src: dict, max_len: float = 3.0) -> list:
    """No speech: take the middle of each shot (between scene cuts), up to max_len seconds."""
    cuts = [0.0] + [t for t in src["scenes"] if 0.5 < t < src["duration"] - 0.5] + [src["duration"]]
    segs = []
    for a, b in zip(cuts, cuts[1:]):
        length = b - a
        if length < 0.8:
            continue
        take = min(max_len, length)
        mid = (a + b) / 2
        segs.append([max(a, mid - take / 2), min(b, mid + take / 2)])
    return segs


def cmd_plan(args) -> None:
    analysis = load_json(WORK / "analysis.json")
    clips, notes = [], []
    for src in analysis["sources"]:
        words = src["transcript"]["words"]
        if len(words) >= 3:
            segs = speech_segments(words, src["duration"])
            notes.append(f"{src['name']}: kept {len(segs)} speech parts, removed pauses")
        else:
            segs = visual_segments(src)
            notes.append(f"{src['name']}: no speech, picked {len(segs)} shots")
        portrait = src["width"] / src["height"] < 0.8
        for k, (a, b) in enumerate(segs):
            clips.append({
                "source": src["id"], "in": round(a, 2), "out": round(b, 2),
                "framing": "fill" if portrait else "blur",   # fill = crop to 9:16, blur = fit on blurred copy
                "crop_x": 0.5,                                # 0 = keep left side, 1 = keep right side
                "zoom": 1.0,
                "transition_in": "cut",                       # cut | fade
                "note": "",
            })

    # Too long? Shorten no-speech shots first, then drop from the end.
    def total():
        return sum(c["out"] - c["in"] for c in clips)
    if total() > args.target:
        speech_ids = {s["id"] for s in analysis["sources"] if len(s["transcript"]["words"]) >= 3}
        for c in clips:
            if c["source"] not in speech_ids and c["out"] - c["in"] > 1.8:
                mid = (c["in"] + c["out"]) / 2
                c["in"], c["out"] = round(mid - 0.9, 2), round(mid + 0.9, 2)
        while total() > args.target and len(clips) > 1 and clips[-1]["source"] not in speech_ids:
            clips.pop()
        if total() > args.target:
            notes.append(f"Still {total():.1f}s (target {args.target}s): speech was not cut. "
                         "Remove clips in work/edit.json if you want it shorter.")

    # Jump cuts: alternate a small zoom when two clips in a row come from the same source.
    for prev, cur in zip(clips, clips[1:]):
        if cur["source"] == prev["source"]:
            cur["zoom"] = 1.0 if prev["zoom"] > 1.0 else 1.12
            cur["note"] = "jump cut: zoom hides the jump"
        else:
            cur["transition_in"] = "cut"
            cur["note"] = "new shot: whoosh sound on the cut"
    if clips:
        clips[0]["note"] = "HOOK: first 2 seconds must grab attention"

    sfx, t = [], 0.0
    for prev, cur in zip([None] + clips, clips):
        if prev and cur["source"] != prev["source"]:
            sfx.append({"at": round(max(0.0, t - 0.2), 2), "name": "whoosh", "volume": 0.35,
                        "why": "accent the change of shot"})
        t += cur["out"] - cur["in"]
    if args.hook:
        sfx.insert(0, {"at": 0.05, "name": "pop", "volume": 0.4, "why": "hook text appears"})

    plan = {
        "_help": "Edit this file to change the cut. Times are seconds in the SOURCE file (in/out). "
                 "framing: fill|blur. transition_in: cut|fade. Then run: python3 reelkit/reelkit.py build",
        "title": args.title or "My Reel",
        "hook_text": args.hook or "",
        "hook_seconds": 2.5,
        "clips": clips,
        "music": {"file": args.music or "", "volume": 0.18, "start_in_track": 0.0,
                  "fade_in": 0.5, "fade_out": 1.5, "duck_under_voice": True,
                  "suggestion": args.music_mood or "upbeat, modern, 100-120 BPM, no vocals"},
        "sfx": sfx,
        "captions": {"enabled": True, "words_per_caption": 3, "fixes": {}, "position": "lower"},
        "notes": notes,
    }
    save_json(WORK / "edit.json", plan)
    log("\n".join(notes))
    log(f"\n✓ Plan: {len(clips)} clips, {total():.1f}s → {rel(WORK / 'edit.json')}")


# ----------------------------------------------------------------------------
# 3. BUILD
# ----------------------------------------------------------------------------
def build_timeline(plan: dict, sources: dict) -> list:
    """Snap every clip to the frame grid and compute where it lands on the final timeline."""
    out, t = [], 0.0
    for i, c in enumerate(plan["clips"], 1):
        src = sources[c["source"]]
        a = max(0.0, frames(c["in"]))
        b = min(frames(src["duration"]), frames(c["out"]))
        if b - a < 1 / FPS:
            raise SystemExit(f"Clip {i}: out ({c['out']}) must be after in ({c['in']})")
        out.append({**c, "n": i, "in": a, "out": b, "dur": round(b - a, 4),
                    "t0": round(t, 4), "t1": round(t + b - a, 4), "src": src})
        t += b - a
    return out


def caption_chunks(timeline: list, cfg: dict) -> list:
    """Words that fall inside the kept clips → short Reels-style captions on the final timeline."""
    fixes = cfg.get("fixes", {})
    words = []
    for c in timeline:
        for w in c["src"]["transcript"]["words"]:
            mid = (w["start"] + w["end"]) / 2
            if c["in"] <= mid < c["out"]:
                s = c["t0"] + max(w["start"], c["in"]) - c["in"]
                e = c["t0"] + min(w["end"], c["out"]) - c["in"]
                text = w["text"]
                for wrong, right in fixes.items():
                    text = text.replace(wrong, right)
                words.append({"start": s, "end": e, "text": text})
    per = max(1, int(cfg.get("words_per_caption", 3)))
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= per or w["start"] - cur[-1]["end"] > 0.4 or w["end"] - cur[0]["start"] > 1.8):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?…,;:]$", w["text"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    caps = [{"start": ch[0]["start"], "end": max(ch[-1]["end"], ch[0]["start"] + 0.45),
             "text": " ".join(x["text"] for x in ch).strip()} for ch in chunks]
    for a, b in zip(caps, caps[1:]):          # no overlaps, no tiny flicker gaps
        if b["start"] - a["end"] < 0.25:
            a["end"] = b["start"]
        a["end"] = min(a["end"], b["start"])
    return [c for c in caps if c["end"] - c["start"] > 0.05]


def ass_escape(text: str) -> str:
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def write_ass(path: Path, caps: list, hook: str, hook_secs: float, position: str) -> None:
    margin = {"lower": 560, "middle": 900, "upper": 1300}.get(position, 560)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
        "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Cap,DejaVu Sans,76,&H00FFFFFF,&H000000FF,&H00000000,&H78000000,-1,0,0,0,100,100,0,0,1,7,3,2,90,90,{margin},1",
        "Style: Hook,DejaVu Sans,84,&H00000000,&H000000FF,&H0000D6FF,&H0000D6FF,-1,0,0,0,100,100,0,0,3,22,0,8,80,80,330,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    if hook:
        lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(hook_secs)},Hook,,0,0,0,,{ass_escape(hook)}")
    for c in caps:
        lines.append(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Cap,,0,0,0,,{ass_escape(c['text'])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def frame_filter(c: dict) -> str:
    """ffmpeg filter that turns one source clip into a 1080x1920 Reel frame."""
    src, z = c["src"], max(1.0, float(c.get("zoom", 1.0)))
    tone = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p," if src.get("hdr") else "")
    zw, zh = int(W * z) // 2 * 2, int(H * z) // 2 * 2
    if c.get("framing", "fill") == "fill":
        cx = min(1.0, max(0.0, float(c.get("crop_x", 0.5))))
        v = (f"[0:v]{tone}scale={zw}:{zh}:force_original_aspect_ratio=increase,"
             f"crop={W}:{H}:(iw-{W})*{cx}:(ih-{H})/2")
    else:  # blur: whole picture on a blurred, zoomed copy of itself
        v = (f"[0:v]{tone}split[bg][fg];"
             f"[bg]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,boxblur=18:2,"
             f"scale={W}:{H},eq=brightness=-0.08[b];"
             f"[fg]scale={zw}:{zh}:force_original_aspect_ratio=decrease[f];"
             f"[b][f]overlay=(W-w)/2:(H-h)/2")
    fades = ""
    if c.get("transition_in") == "fade":
        fades += ",fade=t=in:st=0:d=0.25"
    if c.get("_fade_out"):
        fades += f",fade=t=out:st={max(0, c['dur'] - 0.35):.3f}:d=0.35"
    return f"{v},fps={FPS},tpad=stop_mode=clone:stop_duration=1,setsar=1,format=yuv420p{fades}[v]"


def render_clip_file(c: dict, dst: Path) -> None:
    """Separate clip for CapCut: original framing, original sound, high quality, just trimmed."""
    src = c["src"]
    if src.get("hdr"):  # keep iPhone HDR as 10-bit HEVC so colours stay right in CapCut
        trc = src["color_transfer"]
        vcodec = ["-c:v", "libx265", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p10le",
                  "-tag:v", "hvc1", "-color_primaries", "bt2020", "-color_trc", trc, "-colorspace", "bt2020nc",
                  "-x265-params", f"colorprim=bt2020:transfer={trc}:colormatrix=bt2020nc:log-level=error"]
    else:
        vcodec = ["-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p"]
    audio = ["-map", "0:a:0", "-c:a", "aac", "-b:a", "256k", "-ar", "48000"] if src["has_audio"] else []
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{c['in']:.3f}", "-i", ROOT / src["file"],
         "-t", f"{c['dur']:.3f}", "-map", "0:v:0", *vcodec, *audio, "-movflags", "+faststart", dst])


def render_preview_segment(c: dict, vid: Path, wav: Path) -> None:
    src = c["src"]
    afade = ",afade=t=in:d=0.02" + (f",afade=t=out:st={max(0, c['dur'] - 0.03):.3f}:d=0.03")
    if c.get("_fade_out"):
        afade += f",afade=t=out:st={max(0, c['dur'] - 0.35):.3f}:d=0.35"
    a_in = "0:a:0" if src["has_audio"] else "1:a"
    fc = (frame_filter(c) + f";[{a_in}]aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo,"
          f"apad,atrim=0:{c['dur']:.4f}{afade}[a]")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-ss", f"{c['in']:.3f}", "-t", f"{c['dur']:.3f}", "-i", ROOT / src["file"],
         "-f", "lavfi", "-t", f"{c['dur']:.3f}", "-i", "anullsrc=r=48000:cl=stereo",
         "-filter_complex", fc,
         "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
         "-frames:v", str(round(c["dur"] * FPS)), vid,
         "-map", "[a]", "-c:a", "pcm_s16le", wav])


def concat(files: list, dst: Path, extra: list) -> None:
    lst = dst.with_suffix(".txt")
    lst.write_text("".join(f"file '{f.resolve()}'\n" for f in files), encoding="utf-8")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", lst, *extra, dst])


def sfx_file(name: str) -> Path:
    manifest = json.loads((SFX_DIR / "manifest.json").read_text(encoding="utf-8"))
    if name in manifest:
        return SFX_DIR / manifest[name]["file"]
    p = Path(name)
    if not p.is_absolute():
        p = ROOT / p
    if p.exists():
        return p
    raise SystemExit(f"Unknown sound effect '{name}'. Use one of: {', '.join(manifest)} or a file path.")


def cmd_build(args) -> None:
    plan = load_json(WORK / "edit.json")
    sources = {s["id"]: s for s in load_json(WORK / "analysis.json")["sources"]}
    timeline = build_timeline(plan, sources)
    if not timeline:
        raise SystemExit("The plan has no clips.")
    timeline[-1]["_fade_out"] = True
    total = timeline[-1]["t1"]
    name = slug(args.name or plan.get("title", "reel"), 40)
    kit = OUTPUT / f"{name}_capcut_kit"
    if kit.exists():
        shutil.rmtree(kit)
    d_clips, d_audio, d_sfx = kit / "1_clips", kit / "2_audio", kit / "2_audio" / "sfx"
    d_subs, d_prev, d_tl = kit / "3_subtitles", kit / "4_preview", kit / "5_timeline"
    for d in (d_clips, d_sfx, d_subs, d_prev, d_tl):
        d.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="reelkit_"))

    # --- 1) separate clips + preview pieces
    seg_v, seg_a = [], []
    for c in timeline:
        c["clip_file"] = f"{c['n']:02d}_{slug(c['src']['name'], 16)}_{c['in']:06.2f}-{c['out']:06.2f}.mp4".replace(":", "")
        log(f"Clip {c['n']:02d}/{len(timeline)}  {tc(c['t0'])}–{tc(c['t1'])}  from {c['src']['name']}")
        render_clip_file(c, d_clips / c["clip_file"])
        v, a = tmp / f"seg{c['n']:03d}.mp4", tmp / f"seg{c['n']:03d}.wav"
        render_preview_segment(c, v, a)
        seg_v.append(v)
        seg_a.append(a)
    video_only, voice_wav = tmp / "video.mp4", tmp / "voice.wav"
    concat(seg_v, video_only, ["-c", "copy"])
    concat(seg_a, voice_wav, ["-c", "copy"])

    # --- 2) audio stems: voice, music, sound effects, full mix
    log("Audio: voice, music, sound effects, mix")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", voice_wav, "-c:a", "aac", "-b:a", "256k",
         d_audio / "voice_original_sound.m4a"])
    inputs, chains, mix = ["-i", voice_wav], [], ["[voice]"]
    chains.append("[0:a]asplit=2[voice][sc]")
    music = plan.get("music", {})
    music_path = None
    if music.get("file"):
        music_path = Path(music["file"]) if Path(music["file"]).is_absolute() else ROOT / music["file"]
        if not music_path.exists():
            raise SystemExit(f"Music file not found: {music['file']}")
        fi, fo, vol = float(music.get("fade_in", 0.5)), float(music.get("fade_out", 1.5)), float(music.get("volume", 0.18))
        shape = (f"aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo,atrim=0:{total:.3f},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:d={fi},afade=t=out:st={max(0, total - fo):.3f}:d={fo}")
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-stream_loop", "-1",
             "-ss", f"{float(music.get('start_in_track', 0)):.3f}", "-i", music_path, "-af", shape,
             "-t", f"{total:.3f}", "-c:a", "aac", "-b:a", "256k", d_audio / "music_trimmed.m4a"])
        inputs += ["-i", d_audio / "music_trimmed.m4a"]
        chains.append(f"[1:a]aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo,volume={vol}[m0]")
        if music.get("duck_under_voice", True):   # music gets quieter while someone talks
            chains.append("[m0][sc]sidechaincompress=threshold=0.03:ratio=8:attack=15:release=350[music]")
        else:
            chains += ["[m0]anull[music]", "[sc]anullsink"]
        mix.append("[music]")
    else:
        chains.append("[sc]anullsink")

    sfx_rows = []
    for k, s in enumerate(sorted(plan.get("sfx", []), key=lambda x: x["at"]), 1):
        f = sfx_file(s["name"])
        out_name = f"{k:02d}_{slug(s['name'], 14)}_at_{tc(s['at']).replace(':', 'm').replace('.', 's', 1)}{f.suffix}"
        shutil.copy(f, d_sfx / out_name)
        idx = len(inputs) // 2
        inputs += ["-i", f]
        ms = int(round(float(s["at"]) * 1000))
        chains.append(f"[{idx}:a]aresample=48000,aformat=sample_fmts=s16:channel_layouts=stereo,"
                      f"volume={float(s.get('volume', 0.35))},adelay={ms}:all=1[s{k}]")
        mix.append(f"[s{k}]")
        sfx_rows.append({**s, "file": f"2_audio/sfx/{out_name}"})
    chains.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first,"
                  f"alimiter=limit=0.95,atrim=0:{total:.4f}[out]")
    mix_wav = tmp / "mix.wav"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs, "-filter_complex", ";".join(chains),
         "-map", "[out]", "-c:a", "pcm_s16le", mix_wav])
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", mix_wav, "-c:a", "aac", "-b:a", "256k",
         d_audio / "full_mix_voice_music_sfx.m4a"])

    # --- 3) subtitles
    cap_cfg = plan.get("captions", {})
    caps = caption_chunks(timeline, cap_cfg) if cap_cfg.get("enabled", True) else []
    srt = "\n".join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n"
                    for i, c in enumerate(caps, 1))
    (d_subs / "subtitles.srt").write_text(srt, encoding="utf-8")
    (d_subs / "transcript.txt").write_text(" ".join(c["text"] for c in caps) + "\n", encoding="utf-8")
    hook = plan.get("hook_text", "")
    hook_secs = min(float(plan.get("hook_seconds", 2.5)), total)
    write_ass(tmp / "subs.ass", caps, hook, hook_secs, cap_cfg.get("position", "lower"))
    if caps or hook:
        log("Subtitles: green-screen overlay for CapCut")
        run_in(tmp, ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                     f"color=c=0x00FF00:s={W}x{H}:r={FPS}:d={total:.3f}", "-vf", "ass=subs.ass",
                     "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                     (d_subs / "captions_greenscreen_overlay.mp4").resolve()])

    # --- 4) preview MP4 (flat video – NOT an editable project)
    log("Preview: rendering the finished MP4")
    preview = d_prev / f"{name}_PREVIEW_9x16.mp4"
    vf = ["-vf", "ass=subs.ass"] if (caps or hook) else []
    run_in(tmp, ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", video_only, "-i", mix_wav,
                 *vf, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                 "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                 "-shortest", preview.resolve()])
    no_text = d_prev / f"{name}_PREVIEW_no_text_9x16.mp4"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", video_only, "-i", mix_wav,
         "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", no_text])

    # --- 5) timeline + guide
    write_timeline(d_tl, kit, plan, timeline, caps, sfx_rows, music_path, total, name)
    if args.with_originals:
        d_orig = kit / "0_originals"
        d_orig.mkdir()
        for s in {c["src"]["file"] for c in timeline}:
            shutil.copy(ROOT / s, d_orig / Path(s).name)

    zip_path = OUTPUT / f"{name}_capcut_kit.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as z:  # videos are already compressed
        for f in sorted(kit.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(OUTPUT))
    shutil.rmtree(tmp, ignore_errors=True)
    size = zip_path.stat().st_size / 1e6
    log(f"\n✓ Kit ready: {rel(kit)}/\n✓ Zip: {rel(zip_path)} ({size:.1f} MB), {len(timeline)} clips, {tc(total)} long")


# ----------------------------------------------------------------------------
# timeline documents
# ----------------------------------------------------------------------------
FRAMING_KK = {"fill": "Толтыру (кесу) / Fill", "blur": "Бұлдыр фон / Blur background"}
TRANS_KK = {"cut": "Кесу / Cut", "fade": "Қараңғылану / Fade (0.25s)"}


def write_timeline(d_tl, kit, plan, timeline, caps, sfx_rows, music_path, total, name) -> None:
    music = plan.get("music", {})
    data = {
        "title": plan.get("title"), "format": "9:16 1080x1920 30fps", "duration": round(total, 3),
        "hook_text": plan.get("hook_text", ""), "hook_seconds": plan.get("hook_seconds", 2.5),
        "clips": [{
            "n": c["n"], "file": f"1_clips/{c['clip_file']}", "timeline_start": c["t0"], "timeline_end": c["t1"],
            "duration": c["dur"], "source": c["src"]["name"], "source_in": c["in"], "source_out": c["out"],
            "framing": c.get("framing"), "crop_x": c.get("crop_x"), "zoom": c.get("zoom"),
            "transition_in": c.get("transition_in"), "fade_out": bool(c.get("_fade_out")), "note": c.get("note", ""),
        } for c in timeline],
        "audio": {
            "voice": "2_audio/voice_original_sound.m4a",
            "music": ({"file": "2_audio/music_trimmed.m4a", "source": rel(music_path), "start": 0.0, "end": total,
                       "volume": music.get("volume"), "fade_in": music.get("fade_in"), "fade_out": music.get("fade_out"),
                       "ducked_under_voice": music.get("duck_under_voice")} if music_path else
                      {"file": None, "suggestion": music.get("suggestion")}),
            "sfx": sfx_rows, "full_mix": "2_audio/full_mix_voice_music_sfx.m4a",
        },
        "captions": [{"n": i, "start": round(c["start"], 3), "end": round(c["end"], 3), "text": c["text"]}
                     for i, c in enumerate(caps, 1)],
    }
    save_json(d_tl / "timeline.json", data)
    with open(d_tl / "timeline.csv", "w", newline="", encoding="utf-8-sig") as f:
        wr = csv.writer(f)
        wr.writerow(["track", "n", "timeline_start", "timeline_end", "duration", "file", "source", "source_in",
                     "source_out", "framing", "zoom", "transition_in", "volume", "text_or_note"])
        for c in data["clips"]:
            wr.writerow(["video", c["n"], tc(c["timeline_start"]), tc(c["timeline_end"]), f"{c['duration']:.2f}",
                         c["file"], c["source"], f"{c['source_in']:.2f}", f"{c['source_out']:.2f}", c["framing"],
                         c["zoom"], c["transition_in"], "", c["note"]])
        m = data["audio"]["music"]
        if m.get("file"):
            wr.writerow(["music", 1, tc(0), tc(total), f"{total:.2f}", m["file"], m["source"], "", "", "", "", "",
                         m["volume"], "ducked under voice" if m["ducked_under_voice"] else ""])
        for k, s in enumerate(sfx_rows, 1):
            wr.writerow(["sfx", k, tc(s["at"]), "", "", s["file"], s["name"], "", "", "", "", "",
                         s.get("volume", 0.35), s.get("why", "")])
        for c in data["captions"]:
            wr.writerow(["caption", c["n"], tc(c["start"]), tc(c["end"]), f"{c['end'] - c['start']:.2f}",
                         "3_subtitles/subtitles.srt", "", "", "", "", "", "", "", c["text"]])

    # ---------- human timeline (Kazakh, with English menu names) ----------
    L = [f"# Монтаж кестесі / Editing timeline: {plan.get('title', name)}", "",
         f"- Пішім / Format: **9:16 (1080×1920), {FPS} fps**",
         f"- Ұзақтығы / Duration: **{tc(total)}** ({total:.2f} s)",
         f"- Клиптер / Clips: **{len(timeline)}**, дыбыс эффектілері / SFX: **{len(sfx_rows)}**, "
         f"субтитрлер / captions: **{len(caps)}**", ""]
    if plan.get("hook_text"):
        L += [f"**Hook мәтіні / Hook text** (0:00.00–{tc(float(plan.get('hook_seconds', 2.5)))}, жоғарыда, сары): "
              f"«{plan['hook_text']}»", ""]
    L += ["## 🎬 Видео / Video track", "",
          "| # | Кестеде / Timeline | Ұзақ. | Файл | Түпнұсқа / Source (in → out) | Кадр / Framing | Zoom | Ауысу / Transition | Ескерту |",
          "|---|---|---|---|---|---|---|---|---|"]
    for c in data["clips"]:
        L.append(f"| {c['n']} | {tc(c['timeline_start'])} → {tc(c['timeline_end'])} | {c['duration']:.2f}s | "
                 f"`{c['file'].split('/')[-1]}` | {c['source']} ({tc(c['source_in'])} → {tc(c['source_out'])}) | "
                 f"{FRAMING_KK.get(c['framing'], c['framing'])} | {int(round(float(c['zoom'] or 1) * 100))}% | "
                 f"{TRANS_KK.get(c['transition_in'], c['transition_in'])}{' + соңында fade out' if c['fade_out'] else ''} | "
                 f"{c['note']} |")
    L += ["", "## 🎵 Музыка / Music", ""]
    m = data["audio"]["music"]
    if m.get("file"):
        L += [f"- Файл: `{m['file']}` (бастапқы: {m['source']})",
              f"- 0:00.00 → {tc(total)}, дауысы / volume **{int(float(m['volume']) * 100)}%**, "
              f"fade in {m['fade_in']}s, fade out {m['fade_out']}s",
              "- Сөйлеген кезде музыка автоматты түрде басылады (ducking)." if m["ducked_under_voice"] else ""]
    else:
        L += ["- Музыка файлы берілмеген. CapCut ішіндегі музыкадан таңдаңыз (Instagram-да рұқсат етілген).",
              f"- Ұсыныс / Suggestion: **{m.get('suggestion')}**",
              "- Дауысы шамамен 15–20% болсын, сөз анық естілуі керек."]
    L += ["", "## 🔊 Дыбыс эффектілері / Sound effects", ""]
    if sfx_rows:
        L += ["| # | Уақыт / At | Файл | Дауысы / Volume | Неге / Why |", "|---|---|---|---|---|"]
        L += [f"| {k} | {tc(s['at'])} | `{s['file'].split('/')[-1]}` | {int(float(s.get('volume', .35)) * 100)}% | "
              f"{s.get('why', '')} |" for k, s in enumerate(sfx_rows, 1)]
    else:
        L.append("- Жоқ / None")
    L += ["", "## 💬 Субтитрлер / Captions", ""]
    if caps:
        L += ["| # | Басталуы | Аяқталуы | Мәтін / Text |", "|---|---|---|---|"]
        L += [f"| {c['n']} | {tc(c['start'])} | {tc(c['end'])} | {c['text']} |" for c in data["captions"]]
    else:
        L.append("- Сөз табылмады / No speech found.")
    (d_tl / "timeline.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---------- START HERE guide ----------
    first, last = data["clips"][0]["file"].split("/")[-1], data["clips"][-1]["file"].split("/")[-1]
    G = [f"# Осыдан бастаңыз / START HERE: {plan.get('title', name)}", "",
         "> ⚠️ **`4_preview` ішіндегі MP4 тек ДАЙЫН КӨРІНІС (preview).** Ол өңделетін жоба ЕМЕС: CapCut оны "
         "бір тұтас видео ретінде ғана ашады. Әрі қарай өңдеу үшін төмендегі **бөлек файлдарды** қолданыңыз.", "",
         "## Ішінде не бар", "",
         "| Папка | Не | CapCut-та қалай қолданамыз |", "|---|---|---|",
         f"| `1_clips/` | {len(timeline)} бөлек клип, ретімен нөмірленген, түпнұсқа сапа мен дыбыспен | Негізгі видео жолы |",
         "| `2_audio/voice_original_sound.m4a` | Тек сөйлеу (дайын кесте бойынша) | Қажет болса бөлек дыбыс жолы |",
         "| `2_audio/music_trimmed.m4a` | Музыка (кесілген, fade-пен) | Музыка жолы |",
         "| `2_audio/sfx/` | Дыбыс эффектілері, файл атында уақыты жазылған (`_at_0m07s40` = 0:07.40) | Әрқайсысын сол уақытқа қою |",
         "| `2_audio/full_mix_voice_music_sfx.m4a` | Бәрі араласқан дыбыс | Тез жол: бір ғана дыбыс жолы |",
         "| `3_subtitles/subtitles.srt` | Синхрондалған субтитрлер | CapCut компьютерде/вебте импорттайды |",
         "| `3_subtitles/captions_greenscreen_overlay.mp4` | Жасыл фондағы субтитрлер | iPhone: Overlay + Chroma key |",
         "| `3_subtitles/transcript.txt` | Барлық мәтін | Көшіріп алу үшін |",
         "| `4_preview/` | Дайын видео (мәтінмен және мәтінсіз) | Тек көру үшін / салыстыру үшін |",
         "| `5_timeline/` | Толық монтаж кестесі (`timeline.md`, `.csv`, `.json`) | Қадамдарды тексеру |", "",
         "## iPhone-да CapCut-та жинау (қадам бойынша)", "",
         "CapCut мәзір атаулары нұсқаға қарай сәл өзгеше болуы мүмкін.", "",
         "1. **Файлдарды телефонға алу.** ZIP файлды **Files** (Файлдар) қосымшасына сақтаңыз → басыңыз, ол ашылады.",
         f"2. **Клиптерді Photos-қа сақтау.** `1_clips` папкасын ашыңыз → **Select** → бәрін таңдаңыз → "
         f"**Share** → **Save Videos**.",
         f"3. **Жаңа жоба.** CapCut → **New project** → клиптерді **ретімен** таңдаңыз: `{first}` … `{last}` → **Add**.",
         "4. **9:16.** Төменгі мәзірден **Ratio** (Формат) → **9:16**.",
         "5. **Кадр мен zoom.** `timeline.md` бойынша: «Толтыру» клиптерін екі саусақпен үлкейтіп экранды толтырыңыз; "
         "«Бұлдыр фон» клиптері үшін **Canvas** → **Blur**. Zoom 112% деген клипті сәл үлкейтіңіз.",
         "6. **Ауысулар.** Клиптер арасындағы кішкентай ақ шаршыны басып, кестедегі ауысуды таңдаңыз "
         "(Cut = ештеңе қоспау).",
         "7. **Музыка.** **Audio** → **Sounds** → **Your sounds** / **From device** → `music_trimmed.m4a`. "
         "Немесе CapCut-тың өз музыкасын таңдаңыз. Дауысы ~18%.",
         "8. **Дыбыс эффектілері.** Сол жолмен `2_audio/sfx/` файлдарын қосып, әрқайсысын атында жазылған уақытқа қойыңыз.",
         "9. **Субтитрлер (3 тәсіл):**",
         "   - **A (ең оңай, өңделеді):** **Text** → **Auto captions** → тілді таңдаңыз. Мәтінді `transcript.txt` "
         "бойынша түзетіңіз.",
         "   - **B (дәл біздің стиль):** **Overlay** → **Add overlay** → `captions_greenscreen_overlay.mp4` → "
         "толық экранға созыңыз → **Chroma key** → жасыл түсті таңдаңыз → Intensity ~ 30–50.",
         "   - **C (компьютер арқылы):** CapCut Desktop/Web → **Captions** → **Import** → `subtitles.srt`. "
         "Жобаны бұлтқа (Cloud) жүктеп, iPhone-да ашыңыз.",
         "10. **Hook мәтіні.** " + (f"**Text** → «{plan['hook_text']}» → басынан {plan.get('hook_seconds', 2.5)} секунд, жоғарыда."
                                    if plan.get("hook_text") else "Басына қысқа, қызықты мәтін қосуды ұмытпаңыз."),
         "11. **Тексеру.** Нәтижені `4_preview` ішіндегі видеомен салыстырыңыз.",
         "12. **Экспорт.** Жоғарыдағы **Export** → 1080p, 30 fps → Instagram-ға жүктеу.", "",
         "Инстаграмның батырмалары астыңғы ~20% және оң жақ жиекті жабады: мәтін мен бетті ол жерге қоймаңыз.", ""]
    (kit / "START_HERE.md").write_text("\n".join(G), encoding="utf-8")


# ----------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description="ReelKit: raw footage → CapCut-ready kit for Instagram Reels")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_analyze(p):
        p.add_argument("inputs", nargs="+", help="video files or folders (e.g. input/)")
        p.add_argument("--language", help="speech language code: kk, ru, en… (auto-detect if omitted)")
        p.add_argument("--model", default="small", help="Whisper model: tiny, base, small, medium (default small)")
        p.add_argument("--no-transcribe", action="store_true", help="skip speech recognition")

    def add_plan(p):
        p.add_argument("--target", type=float, default=30, help="target length in seconds (default 30)")
        p.add_argument("--music", help="music file to use (mp3/m4a/wav)")
        p.add_argument("--music-mood", help="music suggestion text when no file is given")
        p.add_argument("--hook", help="big text on screen for the first seconds")
        p.add_argument("--title", help="project title")

    def add_build(p):
        p.add_argument("--name", help="output name (default: title)")
        p.add_argument("--with-originals", action="store_true", help="also copy full original files into the kit")

    add_analyze(sub.add_parser("analyze", help="1. analyze raw footage"))
    add_plan(sub.add_parser("plan", help="2. create an automatic edit plan"))
    add_build(sub.add_parser("build", help="3. build the CapCut kit"))
    p_all = sub.add_parser("all", help="analyze + plan + build")
    add_analyze(p_all)
    add_plan(p_all)
    add_build(p_all)

    args = ap.parse_args()
    if args.cmd in ("analyze", "all"):
        cmd_analyze(args)
    if args.cmd in ("plan", "all"):
        cmd_plan(args)
    if args.cmd in ("build", "all"):
        cmd_build(args)


if __name__ == "__main__":
    main()
