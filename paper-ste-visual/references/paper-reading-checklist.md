# Paper reading checklist

Use this list in step 3 of the workflow. Every item that you confirm becomes one or two sentences in the "What to check before you trust the numbers" section. Report only what you checked in the paper text. If an item does not apply, skip it.

Contents: what to extract, what to check, how to word a finding, worked examples from the YOLO26 test.

## What to extract (for the plan)

1. Paper type: new method, benchmark, survey, system description, or analysis of someone else's model. This decides the tone ("The authors propose..." versus "The authors describe...").
2. The problem and the limit of the earlier work, in the authors' words.
3. Each proposed change: name, mechanism in one sentence, what it replaces.
4. What differs between training and inference.
5. Every results table: caption, dataset, metric, hardware, row labels.
6. The baselines used in tables and in figures.
7. Claims in the abstract and the conclusion, listed as separate lines.

## What to check

| Check | How | Where to report |
|---|---|---|
| Source of the numbers | Read each table caption and the figure "source" notes. Are the numbers from the developers, from other papers, or from the authors' runs? | Limits section, 1 sentence |
| Ablation | Search the tables for rows that add or remove one change. | Limits section |
| Claims without evidence | For each number in the abstract and the text (percent faster, fewer epochs), find the table row that supports it. | Limits section |
| Abstract versus body | Compare each promise in the abstract (devices, datasets, tasks) with the tables. | Limits section |
| Internal contradictions | Compare the related-work table with the method text (who was first, who has which part). | Limits section, and a caption note on the related diagram |
| Versions | If several versions exist (arXiv v1 to vN), compare the headline numbers. Record the version you read. | Limits section and the source line |
| Metrics and data | Do two tables use different datasets or metrics? | Note beside the chart |
| Statistics | Are there error bars (for example "+- 0.7")? How many runs? Say what is missing. | Limits section |
| Missing baselines | Does a table list only the proposed model? | Limits section |

## Reading the figures (for the figure cards)

For each core figure or table, write down before you draw:

1. What the caption says, word by word, and what the text says about it.
2. Axes, units, and the direction of "better" (higher or lower).
3. What the data are: the values in a table of the paper, values only in the image, or values in another paper.
4. Who made the numbers (caption or source note).
5. What the figure leaves out (other models, error bars, other datasets).
6. The one sentence that a newcomer must take from the figure.

Then redraw with the values that you can read from the text or the tables. Say in `redraw_note` what you left out. If the figure is a multi-part summary of claims, give each part an evidence badge: `claim`, `partial`, or `table`.

## How to word a finding

- Start with the paper's own words: "Table 2 lists only YOLO26 models."
- Then the consequence for the reader, in a separate short sentence: "So a reader cannot check the 43% figure from the tables."
- Never write "the authors hide" or "the paper is wrong". Write "does not show", "does not describe", "do not agree".
- Use "in version 5" or "in the text that we read" when your finding depends on the version or on the text extraction.
- If you only searched a part of the text, do not write that something is absent from the whole paper.

## Worked examples (YOLO26 paper, arXiv v5)

| Finding | Evidence | Wording used on the page |
|---|---|---|
| Developer numbers | Table 2 caption: "Ultralytics YOLO26 performance metrics" | "The caption of Table 2 calls the numbers Ultralytics YOLO26 performance metrics. The paper does not describe the measurement setup in detail." |
| No ablation | Tables 1 to 5 are a model summary and per-task results | "The paper has no ablation table for DFL removal, ProgLoss, STAL, or MuSGD." |
| Claim without a table | "up to 43% for the nano model" in section 2.2; Table 2 has only YOLO26 rows | "Table 2 lists only YOLO26 models. So a reader cannot check the 43% figure from the tables." |
| Contradiction | Table 1 row YOLOv10: "end-to-end NMS-free"; section 2.2: "first YOLO release to adopt this paradigm" | "The reader must decide how the two statements fit together." |
| Abstract versus body | Abstract mentions Jetson Nano and Orin benchmarks; result tables show CPU and T4 | "The result tables in version 5 show a CPU and a T4 GPU only." |
| Version change | v1 text: "above 51% and 53%"; v5 text: "above 53% and 55%" | "The numbers in the text can change between versions." |

## Do not

- Do not average, rank, or compare numbers across tables unless the paper does.
- Do not fill a gap with your own knowledge of the field. If the paper says nothing, write "The paper does not say".
- Do not copy a figure from the paper. Redraw the idea as a node diagram and say it is simplified.
- Do not present a diagram's step order as the paper's order unless the paper gives that order.
