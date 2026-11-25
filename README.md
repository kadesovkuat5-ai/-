# ReelMate: AI video editing assistant for Instagram Reels

This project has two tools:

1. **ReelKit** (`reelkit/`): Claude analyzes and edits your raw footage, then builds a **CapCut kit**:
   separate clips, separate audio, sound effects, synced SRT subtitles, an MP4 **preview** and a detailed
   editing timeline, so you can keep editing in CapCut on iPhone.
   → Step-by-step guide (Kazakh): [docs/WORKFLOW.md](docs/WORKFLOW.md)
   → Can a real CapCut project be generated? [docs/CAPCUT_DRAFT_RESEARCH.md](docs/CAPCUT_DRAFT_RESEARCH.md)
2. **ReelMate web app** (`index.html`): a simple in-browser editor (described below).
3. **Qalta** (`qalta/`): an installable phone app (PWA) for small businesses (clinic, dentist, car service,
   shop…) with staff roles, a client base, income/expenses, tax and a monthly report. See [qalta/README.md](qalta/README.md).

> The preview MP4 is a finished, flat video. It is **not** an editable project.

## ReelKit quick start

```bash
pip install -r reelkit/requirements.txt        # Whisper speech-to-text (needs ffmpeg too)
python3 reelkit/reelkit.py analyze input/ --language kk
python3 reelkit/reelkit.py plan --target 30 --hook "Hook text" --music input/music.mp3
#   (Claude reviews and improves work/edit.json here)
python3 reelkit/reelkit.py build --name my_reel   # → output/my_reel_capcut_kit.zip
```

Sound effects in `reelkit/sfx/` come from Pixabay (free licence, see `reelkit/sfx/CREDITS.md`).

---

## ReelMate web app

A simple, dark, mobile-friendly web app that helps you turn any video into an Instagram Reel.
It runs **entirely in your browser**. Your video is never uploaded anywhere.

## What it does

| Step | What you do | What happens behind the scenes |
|------|-------------|--------------------------------|
| 1. Upload | Pick a video from your phone or computer | The browser makes a temporary private link to the file |
| 2. Preview | Play, pause and scrub | Each frame is drawn onto a 9:16 canvas, so you see the final result |
| 3. Suggestions | Tap **Analyze my video** | ~8–40 frames are sampled to check length, framing, lighting, contrast, pacing and how strong the opening is |
| 4. Subtitles | Paste what is said, tap **Generate** | The text is split into short captions and timed across the clip. You can edit each one |
| 5. 9:16 format | Choose *Fill & crop*, *Fit + blur* or *Fit + black*, and trim | The video is scaled and positioned inside a 1080×1920 frame |
| 6. Export | Tap **Export Reel** | The trimmed clip plays while each frame and the audio are recorded into a new video file |

## How to run it (beginner guide)

### Option A: on your computer (easiest)
1. Download this repository (green **Code** button → **Download ZIP**) and unzip it.
2. Double-click `index.html`. It opens in your browser.
3. Use **Chrome** or **Safari** for the best results (they can export MP4).

### Option B: on your phone with GitHub Pages (free)
1. On GitHub, open this repository → **Settings** → **Pages**.
2. Under *Build and deployment*, set **Source** to *Deploy from a branch*, choose your branch and `/ (root)`, then **Save**.
3. After about a minute GitHub shows a link like `https://<your-username>.github.io/<repo>/`. Open it on your phone.

## The files

- `index.html`: the page structure, one card per step
- `style.css`: the dark design. Colors are at the top in `:root`, so they're easy to change
- `app.js`: the logic, split into sections named `STEP 1` … `STEP 6`

## Good to know

- **Keep the screen open while exporting.** The export plays your video in real time, so a 30-second Reel takes about 30 seconds.
- **MP4 vs WebM:** Chrome and Safari create MP4 (H.264) files, which Instagram accepts. Some browsers can only create WebM, and the app tells you when that happens.
- **iPhone videos (HEVC/.mov):** if one won't play in your browser, open it in Safari, or set your camera to *Most Compatible* (Settings → Camera → Formats).
- **Subtitles are timed automatically, not transcribed.** You type the words and the app spreads them over the clip. Use the ▶ button next to a caption to check it, and adjust the times if needed.

## Ideas for next steps

1. **Automatic transcription:** send the audio to a speech-to-text AI so you don't have to type the subtitles.
2. **Smarter AI suggestions:** send a few frames to a vision AI model for feedback on the content, hook and caption ideas.
3. **Music & text overlays:** add background music, titles and stickers.
4. **Multiple clips:** join several videos into one Reel.
