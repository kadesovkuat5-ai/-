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

## ghost-editor (`.claude/skills/ghost-editor`, from github.com/kurbaitaev/ghost-editor @ d71bdb6)
- The skill expects to live at `~/.claude/skills/ghost-editor`. In a fresh cloud session, first run:
  `mkdir -p ~/.claude/skills && ln -sfn "$PWD/.claude/skills/ghost-editor" ~/.claude/skills/ghost-editor`
- Then `pip install opencv-python-headless google-genai openai-whisper`,
  `python3 ~/.claude/skills/ghost-editor/scripts/library_restore.py` (SFX + music, git-ignored) and check with `scripts/doctor.sh`.
- Built for macOS; on Linux the macOS-only caption text check is unavailable. Gemini key is optional (B-roll checks).
