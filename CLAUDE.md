# Project notes for Claude

## The user
- Beginner. Prefers **Kazakh** (Russian also fine), does not read English well. Explain simply, step by step.
- Edits Instagram Reels and finishes them manually in **CapCut on iPhone**.

## Main workflow: ReelKit (`reelkit/reelkit.py`, guide in `docs/WORKFLOW.md`)
When the user sends raw footage:
1. Put the files in `input/`, then run `python3 reelkit/reelkit.py analyze input/ --language <kk|ru|…>`.
2. `python3 reelkit/reelkit.py plan --target <sec> [--hook "..."] [--music file]`.
3. **Review and improve `work/edit.json` yourself.** This is the "AI editing" step:
   - Read the transcript in `work/analysis.json`.
   - Put the strongest moment first as the hook, and cut weak or repeated parts.
   - Place b-roll sensibly (not all at the end).
   - Add `captions.fixes` for Whisper mistakes, and set SFX and transitions.
4. `python3 reelkit/reelkit.py build --name <name>`, then check the preview frames, and send the user
   `output/<name>_capcut_kit.zip` plus the preview MP4.

## Rules
- **Never call an MP4 an editable project.** The preview is a flat video. Editable material = the separate
  files in the kit (clips, audio stems, SRT, timeline).
- CapCut on iPhone cannot import SRT or project files. See `docs/CAPCUT_DRAFT_RESEARCH.md`.
- Only use sound effects from `reelkit/sfx/` (Pixabay licence) or files the user provides.
- The Whisper model downloads from huggingface.co. `HF_HUB_DISABLE_XET=1` is set inside the script.
- `input/`, `work/` and `output/` are git-ignored. Do not commit footage.

## Second project: 3D stadium site (`stadium/index.html`)
- A 3D model of the Petr Atoyan stadium in Oral (FC Akzhayik). The user calls it "Ақжайық стадионы".
- Published artifact (keep this URL; republish the same file to update it): https://claude.ai/artifact/Ub17nSmbhQAcc51taNrRoC
- Features: pick a seat (stand/sector/row/seat) and view from it; squad with best seat and best angle per player;
  weather and time of day (sun position for Oral); team and player editor; rotate pad.
- Built from Yandex satellite imagery and photos (org id 192281300613, point 51.351037 E, 51.212237 N).
  The pitch axis points to about 330°.
- Still approximate: row and seat counts, sector names, and the look of the west stand. Ask the user for a real ticket or photos.
- Test locally with Playwright by routing the jsdelivr three.min.js request to `npm pack three@0.147.0`, because jsdelivr is blocked here.
