---
name: motion-explainer
description: Turn a topic, doc or README into a narrated motion-graphics explainer video in a dark HUD style. Each scene builds up element by element, in sync with sentence-level edge-tts narration, with burned-in subtitles. Use when the user wants an animated or motion-graphics explainer video (动态讲解视频、动画科普视频、动效视频), not static slides.
---

# Motion explainer

Output is code-drawn motion graphics, not a slide deck. Every scene is a **beat timeline**: one narration sentence per beat, and each visual element enters (and is highlighted) on the beat whose sentence talks about it. The HTML player is a pure function of time (`seek(t)`); headless Chrome renders every frame of it, so the video is deterministic and the narration lines up with the animation.

Files: `scripts/render.py` (pipeline), `runtime/player.html` (layouts, animation, subtitles), `references/spec.md` (spec format: **read it before writing a spec**), `examples/01-slash-commands.py` (complete sample using every layout).

## Requirements

A Python env with `edge-tts>=7.3.1` and `playwright` (rendering uses the installed Google Chrome via `channel="chrome"`), plus `ffmpeg` ≥ 7.1. Older edge-tts versions get HTTP 403 from the speech service. Below, `PY` is that interpreter and `R` is `<skill dir>/scripts/render.py`.

## Steps

1. **Outline.** Read the source fully. Plan 10–16 scenes (≈ 6–9 min): cover, one scene per idea, recap last. Pick a layout per scene from `references/spec.md` by content shape: a number goes in `stat`, a sequence in `flow`, a file in `code`, usage in `terminal`. Done when every scene has a layout and a one-line purpose.
2. **Write the spec** `<out>/spec.py`. Write beats first, then attach every element to the beat that mentions it (`at=k`). Done when each element's `at` matches a sentence that names it and every scene is within the fit limits.
3. **Voice and lay out:** `PY R spec.py <out> tts timeline sheet`. The `tts` step caches audio by text hash, so edited sentences are re-voiced and unchanged ones reused. Network errors retry on their own; rerun if TTS still fails.
4. **Visual QA.** Read `<out>/qa/contact.png` (the final state of each scene), then the per-beat frames `qa/sNNbKK.png` of the dense scenes. Fix overflow, clipping, collisions with the subtitle band, and elements that appear on the wrong beat; rerun step 3 until the frames are clean.
5. **Render:** `PY R spec.py <out> frames mux`; `ME_WORKERS` sets the number of parallel Chrome workers (default 4). With 4 workers a 6.5-minute video took about 2.5 minutes to render; run it in the background for long videos.
6. **Verify.** `ffprobe` `<out>/<slug>.mp4`: h264 1920×1080 30 fps plus aac, and the duration matches the total `timeline` printed. Extract 3 frames at known beat times, check the right element is highlighted, and check the subtitle matches that beat.

Deliverables in `<out>`: `<slug>.mp4` (subtitles burned in), `<slug>.srt`, `narration.md`, `player.html` + `narration.m4a`, `qa/`, `build/`. `player.html` has two manual modes: plain open scrubs (space plays, ←/→ jump 5 s), and `player.html?slides=1` is a hand-driven slide deck with one slide per narration beat plus each scene's final state (←/→ one beat, ↑/↓ one scene, click left/right half, `&i=N` opens at slide N). `player` rebuilds it from `build/timeline.json` without touching audio.

## Adapting the look

Colors, fonts and sizes are CSS variables and classes at the top of `runtime/player.html`. A new layout is one `else if (L === "...")` branch in `buildScene`, pushing animations onto `A`. Everything that moves must be computed from `t` inside `applyAnim`/`seek`; CSS transitions, `@keyframes`, timers and `Math.random` break frame-accurate rendering.
