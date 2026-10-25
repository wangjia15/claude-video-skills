---
name: slides-video
description: Turn a source (paper, doc/README, or topic) into a narrated static-slide video — styled HTML slides → PNG → edge-tts narration → MP4 with subtitles. Supports content modes that change the outline: paper→组会汇报, doc→带示例和类比的教程, topic→课程一讲. Use when the user wants a PPT-style 讲解视频/组会视频/课程视频 with static slides (not motion graphics — that is the motion-explainer skill).
---

# Slides video (static)

The pipeline: one `slides.py` spec → styled HTML deck → headless-Chrome PNG per slide + PDF → edge-tts narration per slide → MP4 (SRT alongside, soft subtitle track embedded). One slide of narration = one SRT block, so audio drift is impossible by construction.

Files: `scripts/build.py` (the whole pipeline), `references/spec.md` (spec format, CSS building blocks), `references/modes.md` (**read before writing a spec** — it contains the per-mode outlines and the example/analogy rules), `examples/01-slash-commands.py` (complete sample).

## Requirements

A Python env with `edge-tts>=7.3.1` (older versions get HTTP 403), Google Chrome, and `ffmpeg`. Below `PY` is that interpreter and `B` is `<skill dir>/scripts/build.py`.

## Steps

1. **Pick the mode and outline.** Read the source fully, choose a mode from `references/modes.md`, and turn its outline into a concrete slide list: one line per slide (tag, title, which source content). Done when every slide has a one-line purpose and the deck is 12–18 slides (paper) / 14–24 (doc or topic).
2. **Write the spec** `<out>/spec.py` following `references/spec.md`. Write `notes` (spoken narration) per slide — one idea per slide, narration expands what is on screen instead of reading it. For `doc-tutorial`, add the analogy and worked-example slides the mode calls for. For `paper-journal-club`, crop the paper's key figures into `<out>/figs/` first (pdftoppm/screenshot crops), then reference them via `<figure class="fig">`.
3. **Build slides:** `PY B spec.py <out> html png`. Check `build/png` count == slide count.
4. **Visual QA.** Tile the PNGs into a contact sheet (`ffmpeg -i <out>/build/png/slide%02d.png -vf "scale=640:360,tile=4x5:padding=6" -frames:v 1 sheet.png`) and Read it; Read the 2–3 densest slides at full size. Fix overflow/clipping/cramped slides and rerun until clean.
5. **Voice and video:** `PY B spec.py <out> tts video`. TTS retries on its own and caches per-slide audio keyed by the narration text, so edited slides are re-voiced and unchanged ones reused; if it still fails with connection errors, wait 30–60 s and rerun.
6. **Verify.** `ffprobe` `<out>/<slug>.mp4`: h264 1920×1080 + aac + mov_text, duration plausible vs slide count (~15–35 s/slide); SRT non-empty; extract the first and last frame and confirm they are the cover and recap slides.

Deliverables in `<out>`: `<slug>.mp4`, `<slug>.srt`, `slides.html` (open in a browser: ←/→/space/click to flip slides manually), `slides.pdf`, `narration.md`, `build/` (png, audio, seg, `scripts/spec.py` copy), plus `figs/` if used.

## Adapting the look

Colors are CSS variables in build.py's `CSS` (`--bg --panel --ink --mute --acc --acc2 --line`); override per video with `THEME = {"--acc": "#7aa2f7", ...}` in the spec. New recurring slide patterns belong as CSS classes in build.py — do not inline one-off styles across specs.
