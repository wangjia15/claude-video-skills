---
name: paper-ste-visual
description: Analyze a research paper and explain it in ASD-STE100 Simplified Technical English with a Chinese translation, as one interactive HTML page with animated diagrams, number charts taken from the paper's tables, and concept tables. Make sure to use this skill whenever the user gives a paper (arXiv link, PDF, title, DOI) or a technical report and asks to analyze it, read it, explain it simply, explain the paper's key figures or tables in plain words (图表解读), summarize it visually, make a 论文解读 / 论文分析 / 可视化 page, write it in STE or ASD-STE100 or simplified English, or wants animated diagrams, concept tables, or a bilingual EN/中文 explainer of a paper, even if they do not say "HTML" or "STE" explicitly.
---

# Paper to STE visual explainer

Turn one paper into a single self-contained HTML page:

- the paper's ideas written in short ASD-STE100-style English sentences, each with a Chinese translation
- animated diagrams (a dot travels along the data flow; scenarios such as "training" and "inference" can be switched)
- charts that use only numbers copied from the paper's tables, each with its table name
- 3 to 5 "figure cards": the paper's core figures and tables, redrawn by you, each with a plain-language explanation (what the original shows, how to read it, what it tells us, what to be careful about, and an everyday analogy in Chinese)
- concept tables (key terms, old-versus-new comparison, and the STE rules used on the page)
- a section that tells the reader what to check before trusting the paper's numbers

The page is built from a JSON content file by `scripts/build.py`. You write the content; the script lints it and renders it. Do not hand-write the HTML. The template already handles language switching, animation, charts, tables, dark mode, and phone layouts.

A finished example is in `assets/examples/yolo26/` (`content.json`, `source_excerpt.txt`). Read `content.json` once before you write your own: it shows every feature in use.

## Workflow

### 1. Get the paper and fix the version

- Use the user's file, link, or title. For an arXiv ID, fetch the latest version of the PDF (for example `https://arxiv.org/pdf/<id>`), and note the version number and date. Numbers and claims change between versions, so the page must say which version it reads.
- Read the whole paper, not only the abstract. The abstract, the body text, and the tables sometimes disagree. Those disagreements are valuable findings (see step 3).
- If the paper is an uploaded PDF, extract the text to a file (`pdftotext -layout paper.pdf paper.txt`). If you read it with a web fetch, you must copy the tables and every sentence that carries a number into `source_excerpt.txt` verbatim. This file is the audit trail for step 6.

### 2. Plan the page before writing

Write a short plan for yourself (not in the page):

- **Question the paper answers** and **who needs this** (default reader: a technical person who has not read the paper).
- **3 to 6 core ideas.** One section for each idea or one section for each stage of the method. Add one section for results and one section for limits (step 3).
- **For each idea:** the problem it solves, the mechanism in one sentence, what it replaces, and the evidence the paper gives (a table, a figure, or only a claim).
- **3 to 5 core figures or tables** that carry the paper's main claims (the headline performance plot, the architecture figure, the figure that sums up the contributions, the family or timeline table, the main results table). Prefer the ones a newcomer cannot read without help.
- **Which sections get a diagram** (a mechanism, a pipeline, a before-and-after, a training loop) and **which get a chart** (a results table with several rows).
- **Terms** the reader needs. Every term you mark in bold in the prose must get a glossary row.

Default languages: English (STE) and Chinese. If the user writes in Chinese, answer them in Chinese. The page always has both languages and a switch.

### 3. Read critically, and say so on the page

A paper explainer that only repeats the paper is weak. Always include a final section titled like "What to check before you trust the numbers". Fill it only with facts you verified in the paper text. Check these, and report what you find:

- **Who produced the numbers?** A table caption may say the numbers come from the model's developer, not from the authors' own runs.
- **Ablations.** Does the paper show the effect of each proposed change alone? If there is no ablation table, say so.
- **Claims without a table.** A headline figure (for example "43% faster") may appear in the text with no table that lets the reader check it.
- **Abstract versus body.** The abstract may promise benchmarks (for example on a device) that no table shows.
- **Internal contradictions.** A related-work table and the method text may disagree (for example about which earlier model was first).
- **Version changes.** If you can see another version, compare the headline numbers.
- **Metrics and data.** Scores from different tasks or datasets must not be compared. Say so beside any chart that mixes them.

State each finding as a plain fact about the paper ("Table 2 lists only YOLO26 models"), never as an accusation. Do not claim that a number is wrong unless you recomputed it. If you cannot verify something, leave it out.

`references/paper-reading-checklist.md` has the full list with examples.

### 4. Write the content file

Copy the structure of `assets/examples/yolo26/content.json`. The full field list is in `references/content-schema.md`. Read `references/ste-rules.md` before you write the first sentence.

Writing rules in short (the reason is in the reference file):

- Every English sentence has 25 words or fewer. Prefer 8 to 18.
- One topic for each paragraph, 2 to 4 sentences.
- Active voice, simple tenses, no contractions, no vague words ("very", "huge", "robust", "novel").
- One word for one meaning. Choose a name for each concept and never change it.
- Define a technical noun in a short sentence at its first use; mark it in bold (`**term**`) once.
- The Chinese list must have the same number of sentences as the English list. Translate the meaning; do not translate word by word. Keep standard terms in English (token, NMS, mAP) and give a Chinese name in the glossary.
- Attribute claims: write "The paper says that..." when the paper only claims something. Write the plain fact only when the paper's table shows it.

**Diagrams.** Lay out nodes in `rows` (one or more nodes per row, top to bottom), list `edges`, and describe `scenarios` as steps with captions. Use scenarios to show differences: "earlier model" versus "new model", "training" versus "inference". Nodes that a scenario does not use are dimmed automatically. Keep each diagram to 12 nodes or fewer, labels short (about 20 English characters or 11 Chinese characters when two nodes share a row). Put a figure caption that says what you simplified ("The order of the steps is our simplification").

**Charts.** One metric chip for each column of a paper table, one item for each row. Put the table name and the version in `source`. Copy values exactly as printed. If a number is calculated by you (a difference, a ratio), put it in `meta.derived_numbers` so the checker allows it, and say in the prose that it is a difference.

**Figure cards.** Choose 3 to 5 figures or tables (the lint requires 3 to 5). For each card write:

- `original`: 2 to 4 sentences on what the paper's figure or table shows. Use only the caption and the text. If you cannot see the image, do not describe its data points.
- a **redraw**, one of `scatter`, `diagram`, `chart`, `datatable`, `timeline`, `panels` (see `references/content-schema.md`). Redraw only what the tables or the text give. A figure that plots other models' points that appear nowhere in the text cannot be redrawn in full: plot the values that you have, and say in `redraw_note` what is missing. Never copy the original image, and never invent data points.
- `plain.read`: how to read it (axes, columns, colours, what "good" looks like).
- `plain.meaning`: what it tells us, with the numbers from the paper.
- `plain.caution`: what the figure does not show, who made the numbers, claims without a table. This is where your step 3 findings meet the figures.
- `analogy.zh`: one everyday analogy in Chinese (restaurant, phone spec sheet, car model history). It is Chinese only, because STE bans metaphors. Keep it honest: an analogy explains the shape of the idea; it adds no new claim.

Match the redraw to the figure: a trade-off plot becomes a `scatter`; an architecture figure becomes a `diagram` with scenarios; a multi-part "summary of contributions" figure becomes `panels` with an evidence badge on each part (`claim` = the text only says it, `partial`, `table` = a table shows it); a lineage table becomes a `timeline`; a results table becomes a `datatable` that highlights the best value in each column. Set `redraw.source` to the figure or table name and the version.

Do not repeat the same chart twice. If a section already has a chart of Table 2, the card for Table 2 may show the same numbers in the table form, but its explanation must add something (how to read it, what to watch).

**Tables.** A `glossary` table (10 to 20 terms, one STE definition of 1 to 2 sentences, one Chinese note) and one `compare` table (old versus new, 4 to 7 rows). The STE rules table is added automatically.

### 5. Build and fix until clean

```bash
python scripts/build.py content.json out.html --source source_excerpt.txt
```

The script validates the structure, lints the STE style, checks that every chart value and every decimal or percent number in the English text appears in the source file, then writes the page. Fix every `ERROR` and read every `WARN`:

- `words (limit 25)`: split the sentence.
- `vague word`: replace it with a fact or delete it.
- `not in the source text`: you mistyped a number or invented one. Look it up again in the paper. Never silence this check by editing the excerpt to match.
- `has N English and M Chinese sentences`: make the lists the same length.
- `figures.cards has N cards`: use 3 to 5. `is missing 'plain.caution'`: every card needs original, read, meaning, and caution.
- `point ... is not in the source text` or `value ... (row, column)`: a figure-card number is not in the excerpt; copy it again from the table.
- possible passive voice, `-ing` form, complex tense: rewrite unless the sentence is clearly fine.
- label too long: shorten the node label.

### 6. Smoke test (when node and jsdom are available)

```bash
NODE_PATH=<folder with node_modules> node scripts/smoke_test.js out.html
```

It loads the page, clicks the controls, and prints counts and script errors. Expect `errors: []` and `overLimit: 0`. If you cannot run it, say so in your final message.

### 7. Deliver

- If the Artifact tool is available, publish `out.html` as an artifact (and update the same artifact when the user asks for changes).
- Otherwise save the file in `/mnt/user-data/outputs/` and present it.
- Save `content.json` too when the user may want to edit the text.

Final message to the user (a few sentences, in their language): what the page contains (sections, diagrams, charts, tables), which version of the paper it reads, the two or three most important findings from step 3, and what the lint could not check. Name the limits honestly (see below).

## Limits of this skill

- The lint applies the main ASD-STE100 writing rules. It does not use the official STE dictionary, so the page is "STE-style", not "STE-certified". Say this if the user asks about compliance. The official specification is published by ASD (asd-ste100.org).
- The checker proves that a number appears somewhere in the source text. It does not prove that the number is in the right row. Read the chart rows once against the paper table.
- Diagrams and figure cards are your reading of the paper, not the authors' figures. Say so in the caption or in `redraw_note` when you simplify. The page footer says that the cards are redraws, not copies.
- You may not be able to see a figure's image (text extraction gives only the caption). Then the card explains the caption and the tables, and says what it could not reproduce.
- The page has two fixed languages (English and Chinese). For another second language, change the labels in `assets/template.html` and the `zh` fields in the content file.
- For papers without result tables, leave out charts. For very long surveys, cover the 3 to 6 most important ideas and say which parts you skipped.
