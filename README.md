# Claude video skills

Six Claude Code skills that turn a source (paper, documentation, or a topic) into a narrated Chinese explainer video, end to end: content design → slides/scenes → edge-tts narration → MP4 with subtitles. They render with headless Chrome and ffmpeg (the two K-Plex skills write Obsidian notes instead); no After Effects, no Remotion.

| Skill | Style | Best for |
|---|---|---|
| [`slides-video/`](slides-video/) | Static styled slides (1920×1080 HTML → PNG), one slide spoken per beat | 组会汇报（论文→lab-meeting video）、带示例和类比的文档教程、系列课程一讲 |
| [`motion-explainer/`](motion-explainer/) | Code-drawn motion graphics; every visual element enters on the narration beat that names it | Animated explainers in a dark HUD style ("辞月赴尘"-like), concept demos, pipelines |
| [`research-to-video/`](research-to-video/) | Four-stage pipeline (research → HTML PPT → narration → MP4) with a user checkpoint after each stage | Topic-driven talk videos; depends on the `ppt-generator` and `speech-to-audio` skills |
| [`paper-ste-visual/`](paper-ste-visual/) | One paper → bilingual (ASD-STE100 Simplified English + Chinese) interactive HTML explainer with animated diagrams and concept tables | Paper explainers in plain, controlled English |
| [`kplex-paper-deep-read/`](kplex-paper-deep-read/) | One PDF → a K-Plex deep-reading note with every figure/table/formula, plus one paper card per cited reference (Semantic Scholar/arXiv/OpenAlex lookup), linked via `References` | Building a citation graph in Obsidian/K-Plex |
| [`kplex-vault-organize/`](kplex-vault-organize/) | Link a folder of Markdown paper notes by citations + semantic similarity (local vector index), with translated-title aliases | Organizing an existing Obsidian paper vault for K-Plex |

## How a skill is used

Install by cloning into `~/.claude/skills/` (or symlink each skill folder), then just ask, e.g. "把这篇论文做成组会视频" or "用动态图形讲解 X"。The skill's SKILL.md drives the whole process; each run writes its own output folder (`<slug>.mp4`, `.srt`, `narration.md`, an interactive `player.html`, QA contact sheets, and the editable `spec.py`/`slides.py` source).

Content choices are explicit, per-video conditions, not hard-coded: voice, rate, color theme, and — for `slides-video` — a content mode (`paper-journal-club`, `doc-tutorial` with worked examples and analogies, `topic-course`) that decides the outline and narration register.

## Requirements

- Python env with `edge-tts >= 7.3.1` (older versions get HTTP 403 from the speech service) and `playwright` (motion-explainer only; rendering uses the installed Google Chrome via `channel="chrome"`)
- `ffmpeg` ≥ 7.1 (`slides-video` works with 7.x; `motion-explainer` uses `-/filter_complex`)
- macOS or Linux (Chrome path is auto-detected by Playwright; narration is Simplified Chinese by default, any edge-tts voice works)

## Repo layout

Each folder is one self-contained skill (SKILL.md + scripts + references + a complete example). Both pipelines cache narration keyed by the narration text, so editing one line re-voices only that line.

See each skill's SKILL.md for the step-by-step contract and its `references/` for the spec format.
