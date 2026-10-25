---
name: kplex-paper-deep-read
description: Turn one PDF paper into a self-contained K-Plex paper folder — a Chinese deep-reading Markdown note that includes every figure, table and formula (formulas in LaTeX, complex concepts and formulas explained), plus one paper card per cited reference (metadata, abstract, translated abstract, a figure when arXiv has one) linked through the `References` property so K-Plex shows the citation structure. Use when the user wants to 精读/deep-read a PDF paper, convert a paper PDF into notes for K-Plex, build the reference/citation graph of a paper, or create reference paper cards ("精读论文", "把pdf转成k-plex", "分析引用创建论文卡片", "生成论文md包含所有图表和公式").
---

# K-Plex paper deep read

One PDF becomes one folder (everything stays inside it):

```
<vault>/Papers/DeepRead/<Author Year - Title>/
  <Stem>.md              deep-reading note — the K-Plex centre node
  <Stem>.pdf             copy of the PDF
  images/                fig-N.png, table-N.png cropped from the PDF
  References/<Card>.md   cited papers (parents of the note in K-Plex)
  References/images/     cited papers' figures (arXiv HTML)
  .work/                 manifest.json, text.md, outline.md, pages/, equations/, refs.json (hidden from Obsidian)
```

Script: `~/.claude/skills/kplex-paper-deep-read/scripts/kplex_paper.py`, run with `uv run --script` (PyMuPDF installs automatically). Below `P` means:

```bash
uv run --script ~/.claude/skills/kplex-paper-deep-read/scripts/kplex_paper.py
```

## Workflow

1. **Locate** the PDF and the vault root (the folder with `.obsidian`). Default output root is `Papers/DeepRead`; use `--root` if the user names another folder. Ask only when the vault is unclear.

2. **Extract**: `P extract <pdf> --vault <vault> [--root …] [--arxiv ID]`
   Looks up metadata (Semantic Scholar → arXiv), copies the PDF, renders every page to `.work/pages/p-NN.png` (144 dpi: **PDF points = pixels / 2**), crops each captioned figure/table to `images/`, crops numbered equations to `.work/equations/` (for reading only), writes the reading-order text with headings to `.work/text.md`, the section/figure/equation outline to `.work/outline.md`, and a note skeleton with frontmatter. Pass `--arxiv`/`--doi` when the PDF lacks them and the summary says `metadata_found: false`.

3. **Start references in the background** (network, a few minutes): `P refs <dir>` with `run_in_background`.
   Gets the reference list from Semantic Scholar, pairs it with the PDF's numbered entries (so `[12]` maps to a card), looks up unmatched entries, fills abstracts (arXiv/OpenAlex), translates titles/abstracts (`--lang zh-CN`, `--lang none` to skip), downloads the first arXiv HTML figure per card (`--card-figures N`, 0 = none), and writes `.work/refs.json` (`n`, `title`, `first_author`, `year`, `link`). A paper that already exists in the vault (matched by arXiv id / DOI / title) is linked instead of duplicated; `--no-reuse` forces cards. Set `S2_API_KEY` if Semantic Scholar rate-limits.

4. **Verify crops.** View every `images/*.png` (Read tool). A crop that cuts off content, includes body text, or shows the wrong figure: open the page render, measure the box in pixels, divide by 2, and recrop:
   `P crop <dir> --page N --rect x0,y0,x1,y1 --name fig-3` (also adds figures the detector missed; pass `--caption`). Do not skip this — the detector is heuristic.

5. **Deep read and write the note.** Read `.work/text.md` completely and look at the page renders for formulas, figures and tables (PDF text garbles maths — transcribe formulas from the images; `.work/equations/eq-N.png` are close-ups). Replace the placeholder in `<Stem>.md`, keeping the frontmatter, following [references/note-guide.md](references/note-guide.md). Non-negotiable:
   - every figure and table in `manifest.json` is embedded with its caption line directly below it;
   - every numbered equation appears as display LaTeX with `\tag{N}`; include the important unnumbered display formulas too;
   - complex concepts and every formula are explained (symbols, intuition, role in the method);
   - sections mirror the paper's headings so K-Plex's section outline matches the paper;
   - write in the user's language (default Chinese), keeping key original sentences as highlights.
   Once `refs` has finished, link citation markers to cards using `refs.json`.

6. **Check**: `P check <dir> --fix` — adds all reference links to the `References` property and reports missing figures/equations, broken embeds, unbalanced `$$`. Fix every issue and rerun until it exits cleanly.

7. **Report** to the user: the folder, counts (sections, figures, tables, equations, reference cards created/reused, unresolved references), and anything that needed judgement (recropped images, references that could not be resolved).

## How it appears in K-Plex

- `References` is K-Plex's paper-reading parent field: cited papers appear above the note. If paper reading is off, add `References` to **Settings → K-Plex → Ontology → Parent fields**.
- `Note type: Paper` gives cards and the note the paper style; the first `aliases` item (translated title) is the display name.
- Expanding the note to sections shows each section's `==highlights==` with their footnote comments and its figures under the section cards; `abstract_zh` feeds the hover abstract card.

## Rules

- Never overwrite an existing deep-reading note's body without asking; `extract --force` only regenerates `.work/` and images. Rerunning `refs` keeps existing cards unless `--refresh`.
- Only titles and abstracts are sent to the translation service; nothing else leaves the machine except metadata lookups.
- Do not invent content: when a formula or figure is unreadable, say so in the note instead of guessing.
