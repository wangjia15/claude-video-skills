# Spec reference (slides.py)

A spec is a Python module. Required: `TITLE`, `SLUG`, `FOOTER`, `SLIDES`. Optional: `VOICE` (default `zh-CN-YunyangNeural`), `RATE` (default `+5%`), `THEME` (dict of CSS variable overrides, e.g. `{"--acc": "#7aa2f7", "--bg": "#0e1116"}`).

Each `SLIDES` entry is a dict: `tag` (small chapter label), `title` (HTML allowed), `body` (HTML, 1920×1080 minus ~110 px header/foot), `notes` (spoken narration for this slide), optional `cls` (`"cover"` for the first slide, `"summary"` for the last).

## Body building blocks (CSS classes already in build.py)

| class | use |
|---|---|
| `.lead`, `.grid2/.grid3/.grid4`, `.card` (+ `.card .ic/.h3/.p`), `.split` | layouts; ≤ 4 cards per grid |
| `table` (`.small`, `.dodont` with ✅/❌ columns) | ≤ 8 rows; first column `nowrap` |
| `pre` (+ `span.c` comment, `span.k` key, `span.v` value) | ≤ 14 lines; `pre.mini` for one-liners |
| `.note` / `.note.warn` / `.note.small` | callouts and warnings |
| `.flow` `.fnode` `.farrow` | left-to-right pipelines |
| `.migrate` `.mbox` `.arrow` | before/after comparisons |
| `.takeaways` (numbered list), `.next`, `.pill`, `kbd` | recap slides |
| `<figure class="fig"><img src="figs/x.png"><figcaption>图 1 · …</figcaption></figure>` | paper figures: put crops in `<out>/figs/` before `html png` |
| `<div class="analogy"><b>类比：</b>…</div>` | analogy callout |

## Narration (`notes`)

Spoken by edge-tts: natural spoken Chinese, 120–250 chars per slide, no markdown/symbols. Spell out what TTS mangles ("CLAUDE 点 md", "斜杠 rewind", "杠杠 output-format"). The SRT is generated from the same text, so keep it listenable.

## Fit limits

A slide that needs scrolling is a bug: tables ≤ 8 rows, code ≤ 14 lines, and after building always check `build/png/slideNN.png` (contact sheet + dense slides) before `tts video`.
