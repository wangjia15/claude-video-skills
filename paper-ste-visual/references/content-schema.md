# Content file schema

`build.py` reads one JSON file. Every human-readable text has the form `{"en": "...", "zh": "..."}` unless the table says otherwise. Use `**term**` to mark a term in bold inside any sentence.

Contents: top level, sections, diagram, chart, figure cards, tables, footer notes, validation messages.

## Top level

```json
{
  "meta": { ... },
  "sections": [ ... ],
  "figures": { ... },
  "tables": [ ... ],
  "rules_table": true,
  "footer_notes": [ {"en": "...", "zh": "..."} ]
}
```

### meta

| Field | Required | Meaning |
|---|---|---|
| `title` | yes | `{en, zh}` page title |
| `subtitle` | no | `{en, zh}` one line under the title |
| `source` | no | `{title, authors, id, date, url}` shown under the title as "Source: ..." Include the version in `id` (for example `arXiv:2509.25164v5`) |
| `limit` | no | maximum words in an English sentence (default 25) |
| `derived_numbers` | no | list of numbers (as strings) that you calculated and that are not in the source text |
| `concepts_title` | no | `{en, zh}` heading for the tables section (default "Related concepts") |

## sections

Each item:

```json
{
  "id": "nms-dfl",
  "title": {"en": "...", "zh": "..."},
  "paras": [ {"en": ["Sentence.", "Sentence."], "zh": ["句子。", "句子。"]} ],
  "diagram": { ... },
  "chart": { ... }
}
```

- `paras[].en` and `paras[].zh` must have the same length. English: 6 sentences or fewer, each 25 words or fewer.
- `diagram` and `chart` are optional. A section with a diagram shows the diagram in a second column (sticky on wide screens). A chart appears under the prose.

## diagram

```json
{
  "title": {"en": "...", "zh": "..."},
  "desc":  {"en": "...", "zh": "..."},
  "rows": [["in"], ["a", "b"], ["out"]],
  "nodes": {
    "in": {"label": {"en": "Image", "zh": "图像"}, "sub": {"en": "...", "zh": "..."}, "style": "plain", "desc": {"en": "...", "zh": "..."}}
  },
  "edges": [ ["in", "a"], {"from": "out", "to": "in", "loop": true, "label": {"en": "Repeat", "zh": "重复"}} ],
  "scenarios": [
    {"id": "s1", "label": {"en": "Training", "zh": "训练"},
     "steps": [ {"nodes": ["in"], "edges": [["in", "a"]], "caption": {"en": "...", "zh": "..."}} ]}
  ],
  "caption": {"en": "...", "zh": "..."}
}
```

- `title` and `desc` are the accessible name and description of the SVG (screen readers).
- `rows`: top to bottom. All nodes in one row share one height and split the width. Use 1 to 2 nodes in a row for readable labels (3 at most, with short labels).
- `nodes.style`: `plain` (white), `teal` (core part), `amber` (new or highlighted part), `dash` (optional or older part).
- `nodes.sub` makes the box taller and adds a second line.
- `nodes.desc` is used as the step caption when you give no `scenarios`.
- `edges`:
  - an edge to a node in a lower row is drawn as a straight arrow
  - an edge to a node in the same row is drawn as a side arrow (the row gets a wider gap)
  - an edge to a node in a higher row, or with `"loop": true`, is drawn on the right side as a return path; a `label` is written along it
  - an edge that skips a row is drawn straight through the gap between nodes of the skipped row: place two nodes side by side in that row so the gap is free (see the "nms-dfl" diagram in the example)
- `scenarios` (optional): each scenario is a list of `steps`. A step lists the `nodes` to highlight, the `edges` where a dot travels (up to 3), and a `caption`. Each edge in a step must exist in `edges`. With 2 or more scenarios the page shows a switch; nodes and edges that the chosen scenario never uses are dimmed. Without `scenarios`, the page walks through the nodes in row order.
- Each scenario step lasts 1.7 seconds. The animation starts when the diagram is on screen, stops when it leaves, and has "Play/Pause" and "Next step" buttons. With reduced-motion settings it does not start by itself.

## chart

```json
{
  "title": {"en": "...", "zh": "..."},
  "source": "Table 2, detection part, arXiv v5 (COCO validation, 640 px)",
  "metrics": [
    {"id": "map", "label": {"en": "mAP", "zh": "mAP"}, "unit": "", "better": "high", "decimals": 1}
  ],
  "items": [ {"label": "YOLO26n", "values": {"map": 40.9}} ],
  "note": {"en": "...", "zh": "..."}
}
```

- `source` is required. Name the table and the version.
- `better`: `high` or `low`. It sets the hint text and the highlighted bar (the best value).
- `values` keys must be metric ids. A missing key means the row is skipped for that metric.
- Copy values exactly as printed in the paper. `--source` checks each value against the source text.

## figures (core figure cards)

```json
"figures": {
  "title": {"en": "...", "zh": "..."},          // optional, default "Core figures and tables explained"
  "intro": {"en": "...", "zh": "..."},          // optional
  "cards": [ { ... }, { ... }, { ... } ]        // 3 to 5 cards
}
```

One card:

```json
{
  "id": "fig1",
  "label": {"en": "Figure 1", "zh": "图 1"},
  "title": {"en": "Accuracy against speed", "zh": "精度与速度的关系"},
  "original": {"en": ["What the paper shows."], "zh": ["论文里这张图是什么。"]},
  "plain": {
    "read":    {"en": ["How to read it."],  "zh": ["怎么看。"]},
    "meaning": {"en": ["What it tells us."], "zh": ["它说明了什么。"]},
    "caution": {"en": ["What to be careful about."], "zh": ["需要留意什么。"]}
  },
  "analogy": {"zh": "一个生活化的比方（只有中文）"},
  "redraw_note": {"en": "What is reproduced and what is not.", "zh": "..."},
  "layout": "side",
  "redraw": { "type": "scatter", ... }
}
```

- `original`, `plain.read`, `plain.meaning`, `plain.caution` are lists of English sentences (counted, 25 words or fewer) with a Chinese list of the same length.
- `layout`: `side` (redraw beside the text) or `wide` (redraw above the text). `datatable`, `timeline`, and `panels` are always wide.
- `analogy.zh` is shown only in Chinese and bilingual mode.

### redraw types

`scatter` (a trade-off plot):

```json
{"type": "scatter", "source": "Table 2, arXiv v5",
 "x": {"label": {"en": "Latency", "zh": "延迟"}, "unit": "ms", "better": "low", "decimals": 1},
 "y": {"label": {"en": "mAP", "zh": "mAP"}, "better": "high", "decimals": 1},
 "better": "top-left",
 "points": [{"label": "n", "x": 1.7, "y": 40.9}]}
```
Points appear one by one when the card scrolls into view (Replay button; no autoplay with reduced motion). A point can be selected to read its values. `better` (`top-left`, `top-right`, `bottom-left`, `bottom-right`) marks the good corner. Optional `xmin`, `ymin`, `caption`.

`diagram`: `{"type": "diagram", "diagram": { ...same as a section diagram... }}`.

`chart`: `{"type": "chart", "chart": { ...same as a section chart... }}`.

`datatable` (a results table, best value in each column highlighted):

```json
{"type": "datatable", "source": "Table 2, detection part, arXiv v5",
 "first": {"en": "Model", "zh": "模型"},
 "columns": [{"id": "map", "label": {"en": "mAP", "zh": "mAP"}, "unit": "", "better": "high", "decimals": 1}],
 "rows": [{"label": "YOLO26n", "values": {"map": 40.9}}]}
```

`timeline` (a lineage or version table):

```json
{"type": "timeline", "source": "Table 1, arXiv v5 (9 of 14 rows)",
 "items": [{"year": "2024", "name": "YOLOv10", "mark": "ref",
            "text": {"en": ["One sentence."], "zh": ["一句话。"]}}]}
```
`mark`: `new` (amber dot, the paper's subject), `ref` (teal dot, a related earlier item), or omit.

`panels` (a multi-part figure, with an evidence badge for each part):

```json
{"type": "panels", "items": [
  {"tag": "(a)", "title": {"en": "Remove DFL", "zh": "去掉 DFL"},
   "claim": {"en": ["What the paper says."], "zh": ["论文的说法。"]},
   "plain": {"en": ["In plain words."], "zh": ["通俗地说。"]},
   "evidence": {"level": "claim", "note": {"en": "Why this level.", "zh": "为什么是这个级别。"}}}]}
```
`evidence.level`: `claim` (only the text says it), `partial` (a table shows part of it), `table` (a table shows it).

`source` is required for `scatter`, `datatable`, and `timeline`. With `--source`, every scatter point and every datatable value must appear in the source text.

## tables

Glossary table:

```json
{"kind": "glossary", "title": {"en": "Key terms", "zh": "关键术语"},
 "rows": [ {"term": {"en": "NMS", "zh": "非极大值抑制"}, "aliases": ["non-maximum suppression"],
            "def": ["Non-maximum suppression (NMS) removes duplicate boxes."],
            "note": "中文解释（字符串）"} ]}
```

Compare table:

```json
{"kind": "compare", "title": {"en": "...", "zh": "..."},
 "cols": [{"en": "Earlier models", "zh": "早期模型"}, {"en": "New model", "zh": "新模型"}],
 "rows": [ {"item": {"en": "Post-processing", "zh": "后处理"},
            "cells": [["Sentence for column 1."], ["Sentence for column 2."]],
            "note": "中文说明（字符串）"} ]}
```

- `def` and each `cells` entry are lists of English sentences (counted and badged like prose).
- `note` is a Chinese string.
- `cells` must have one entry for each column.
- The STE rules table (7 rules with avoid and use examples) is added at the end unless `"rules_table": false`.

## Display modes

The page has three modes: English only, Chinese only, and English plus Chinese (default). The word-count badges and the English columns hide in Chinese-only mode.

## Validation messages

| Message | Meaning |
|---|---|
| `has N English and M Chinese sentences` | the two lists in one paragraph differ in length |
| `uses unknown node` / `unknown edge` | a scenario step names a node or edge that does not exist |
| `is not placed in rows` | a node is defined but not in any row |
| `chart.source is required` | name the table and the version |
| `value X is not in the source text` | the number is not in `source_excerpt.txt`; check the paper |
| `number X is not in the source text` | same, for a decimal, a percent, or a number of 100 or more in a sentence; if you calculated it, add it to `meta.derived_numbers` |
| `bold term 'X' has no glossary row` | add a glossary row or an alias |
| `figures.cards has N cards` | use 3 to 5 cards |
| `figures.cards[i] is missing 'plain.caution'` | every card needs `original`, `plain.read`, `plain.meaning`, `plain.caution` |
| `evidence.level must be claim, partial, or table` | fix the badge level of a panel |
| `point X y=... is not in the source text` | a scatter or datatable value is not in the excerpt |
