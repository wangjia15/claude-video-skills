# Spec reference

A spec is a Python module with `META` and `SCENES`. `examples/01-slash-commands.py` uses every layout; copy it as the starting point.

## META

| key | meaning |
|---|---|
| `title` | video title (MP4 metadata, narration.md heading) |
| `slug` | output file stem: `<slug>.mp4`, `<slug>.srt` |
| `brand`, `episode` | top-right corner: `brand · EPISODE` |
| `voice`, `rate` | edge-tts voice (default `zh-CN-YunyangNeural`) and rate (default `+5%`) |

## Scene keys (all layouts)

| key | meaning |
|---|---|
| `layout` | `cover` `list` `cards` `table` `code` `terminal` `flow` `stat` `compare` |
| `section`, `section_title` | top-left badge and label (hidden on `cover`) |
| `kicker` | small uppercase mono line above the title, decoded with a scramble effect |
| `title` | headline, wiped in left to right; supports highlight markup |
| `say` | list of **beats**: one narration sentence each, voiced separately |
| `note` | optional bottom callout `dict(text, at, color)` |
| `hold` | extra seconds of silence at the end of the scene |

### Beats drive everything

- Beat `k` starts when sentence `k` starts speaking. Beat 0 normally introduces the headline; give each element `at=k` so it appears while sentence `k` describes it, and stays highlighted (`is-focus`) until beat `k+1`.
- Elements default to `at = index + 1`. Several elements may share a beat.
- A beat is a string (spoken and shown as the subtitle) or `dict(say=..., sub=...)` when TTS needs a spoken form that differs from the displayed text: `say="斜杠 clear 清空对话"`, `sub="/clear 清空对话"`. Write `say` for the ear (spell out `.`, `/`, `$`, `--`); write `sub` for the eye.
- Keep one idea per beat: 15–45 Chinese characters. The subtitle is cut at punctuation into short phrases timed by character count.

## Markup

- Text fields: `{c:..}` cyan, `{o:..}` orange, `{r:..}` red, `{g:..}` green, `{y:..}` yellow, `{m:..}` muted, `` `code` `` monospace. No nesting.
- `code` layout lines: `{k:..}` key/keyword, `{s:..}` string, `{v:..}` variable, `{c:..}` comment, `{y:..}` literal.
- Colors for elements: `color="c"|"o"|"r"|"g"|"y"`.

## Layouts

| layout | fields | best for |
|---|---|---|
| `cover` | `kicker`, `title`, `en` (scrambled English line), `glyph` (large outlined character), `sub`, `sub_at`, `items[code,label,color,at]` chips | first scene |
| `list` | `items[value,unit,kicker,title,sub,color,at]`; rows show as faint ghosts until their beat | 3–5 parallel points, questions, recap |
| `cards` | `items[icon,label,sub,code,color,at]`, `cols` | 2–4 named things side by side |
| `table` | `header[]`, `rows[cells[],at]` | up to 6 command → purpose rows |
| `code` | `file`, `code[text,at]` (typed line by line), `focus_lines[at,lines[],at_end]`, `notes[title,text,color,at]` | config files, SKILL.md, source; ≤ 10 lines |
| `terminal` | `lines[cmd|out, at]`: `cmd` lines type out, `out` lines appear | command usage examples |
| `flow` | `nodes[icon,label,sub,color,at]`, `per_row`; nodes light up in order with growing connectors | pipelines, lifecycles; > 5 nodes wrap to 2 rows |
| `stat` | `value`, `unit`, `prefix`, `decimals`, `label`, `caption`, `color`, `at`, `items[title,text,color,at]` | one big counted-up number |
| `compare` | `columns[title,color,at,items[text,at]]` | before/after, do/don't |

## Fit limits (1920×1080, subtitles reserve the bottom 170 px)

`list` ≤ 4 rows · `cards` ≤ 4 · `table` ≤ 6 rows · `code` ≤ 10 lines of ≤ 60 chars · `terminal` ≤ 7 lines · `flow` ≤ 8 nodes · `compare` ≤ 5 items per column. Over the limit, split into two scenes. Two more known collisions: `cards` with `cols=2` and 4 items forms a 2×2 grid that overflows the scene body (keep the default single row, or use ≤ 3 items per column); and a scene-level `note` collides with a `list` of 4 rows, so drop the note or fold its text into the last beat.
