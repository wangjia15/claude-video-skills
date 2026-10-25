# STE writing rules for paper explainers

ASD-STE100 is a controlled language for technical writing. Its aim is that a reader who is not a native English speaker understands each sentence only one way. The checker in `scripts/ste_lint.py` enforces the rules that a program can test. The rest is your job.

Contents: core rules, how to rewrite academic sentences, defining terms, numbers and units, attributing claims, Chinese translation, phrases to reuse.

## Core rules (and why)

| Rule | Why it helps a paper explainer |
|---|---|
| A descriptive sentence has 25 words or fewer | Papers pack 3 ideas in one sentence. The limit forces you to separate them. |
| One topic for each paragraph, 6 sentences or fewer (use 2 to 4) | Each paragraph then maps to one idea in the diagram. |
| Active voice | The reader sees who does what: "The router selects the experts." |
| Simple tenses (present for facts, simple past for what the authors did) | Complex tenses hide the order of events. |
| One word, one meaning. Never rename a concept | If you write "expert", then "sub-network", then "specialist", the reader thinks there are three things. |
| Define a technical noun at its first use, in its own short sentence | The glossary repeats the definition, but the reader should not need to jump to it. |
| No vague or promotional words | "Very fast", "huge", "robust", "novel" claim something without a fact. Use the number from the paper or say nothing. |
| No contractions, no idioms, no metaphors | They break for non-native readers and for translation. |
| Use articles ("the", "a") and keep verbs visible | Do not drop articles as in a headline. |
| Use a list or a table for steps and for comparisons | The page has diagrams and tables for this. |

## Rewriting academic sentences

Cut at every "which", "that", "while", "and", and semicolon. Then check each piece.

Original (41 words):
"YOLO26 fundamentally redesigns the prediction head to produce direct, non-redundant bounding box predictions without the need for NMS, which reduces inference complexity and eliminates the dependency on hand-tuned thresholds."

STE rewrite (3 sentences):
"YOLO26 has a new prediction head. The head predicts direct boxes that are not redundant. The model does not need NMS or a hand-tuned threshold."

Check what you removed. "Reduces inference complexity" was a claim without a number, so it is gone unless you can say how much.

| Academic pattern | STE pattern |
|---|---|
| "is utilized to", "leverages" | "uses" |
| "is capable of achieving" | "can reach" |
| "a plethora of", "a myriad of" | "many" (or the exact number) |
| "in order to" | "to" |
| noun pile: "label assignment loss weighting strategy" | break it up: "The strategy changes the weight of the loss." |
| passive: "Boxes are filtered by NMS." | "NMS filters the boxes." |
| progressive: "The model is learning" | "The model learns." |
| "can be seen that" | delete, and state the fact |

## Defining a term

Use this pattern for the first sentence about a new term, then add one sentence on what it does:

"A **<term>** is a <class> that <function>." followed by "<Where the paper uses it>."

- "A **bounding box** is a rectangle around an object."
- "**NMS** removes duplicate boxes. It keeps the box with the highest confidence score for each object."

If the term has an abbreviation, write the full name once: "Non-maximum suppression (NMS) removes duplicate boxes." Then use only the abbreviation.

Mark a term in bold (`**term**`) only at its first definition in the prose. The linter warns when a bold term has no glossary row. Add `aliases` to the glossary row when the prose uses another form (for example `object detector` for the row `object detection`).

## Numbers and units

- Write the number exactly as the paper prints it ("40.9", not "about 41").
- Write the unit in a plain way: "1.7 ms", "55.7 M parameters" (in a sentence: "55.7 million parameters").
- Name the setting beside the number: "On a T4 GPU with TensorRT, YOLO26n needs 1.7 ms."
- A comparison needs both numbers: "YOLO26n needs 1.7 ms and YOLO26x needs 11.8 ms."
- If you calculate a number, say it is a difference or a ratio, and list it in `meta.derived_numbers`.
- Percent signs: the checker looks for the digits in the source. Write "above 53%" if the paper writes it so.

## Attributing claims

Sort every statement into one of three kinds and write it in the matching pattern.

| Kind | Pattern | Example |
|---|---|---|
| A table in the paper shows it | plain fact + table name in the chart source | "YOLO26x reaches an mAP of 57.5." |
| The text claims it, no table shows it | "The paper says that..." | "The paper says that MuSGD gives faster convergence." |
| Missing evidence (you checked) | "The paper does not show..." / "has no ..." | "The paper has no ablation table for STAL." |

Never write your own opinion of the method as a fact. Never write "better" or "faster" without the number and the baseline.

## Chinese translation

- Match sentence by sentence (the build fails when the counts differ). One English sentence maps to one Chinese sentence.
- Translate for meaning. Chinese may use a comma where English uses "and" or "while", but keep one idea in each sentence.
- Keep standard English terms that Chinese readers use as they are: token, NMS, mAP, IoU, FP16, INT8, COCO, ONNX. Give a Chinese name in the glossary term cell.
- Mark the same term in bold in the Chinese sentence (`**NMS**`).
- Use the Chinese full-width punctuation (，。：；) and put a space between Chinese text and an English word or number ("YOLO26 的 mAP 是 40.9").
- Chinese captions and labels for diagrams must be short: about 11 characters in a node when two nodes share a row.

## Phrases you can reuse

- "The paper says that ..." / "The paper lists ..." / "The paper gives ..."
- "Table 2 shows ..." / "Table 2 lists only ..."
- "The paper does not describe ..." / "The paper has no ..."
- "A higher value is better." / "A lower value is better."
- "Do not compare these scores with each other."
- "Version 1 says ... Version 5 says ..."
- "This diagram is our simplification."

## Plain-language explanations of figures

A figure card explains a figure to a newcomer. Keep STE in the English and use the three-part pattern:

| Block | What it does | Pattern |
|---|---|---|
| read | tells the reader how to read the figure | "Each dot is one model size." "A dot on the left is faster." |
| meaning | says what the figure tells us, with numbers | "From n to x, the mAP rises by 16.6 points." |
| caution | says what the figure does not show | "The original figure also shows other models." |

Put the analogy in the Chinese `analogy.zh` field only. STE does not allow metaphors in the English. A good analogy matches the structure of the figure (axes, direction, trade-off) and adds no claim that the paper does not make. Do not use an analogy to say that a method is good.

## Limits of the linter

The linter does not know the official STE dictionary of approved words. It finds long sentences, vague words, contractions, and some passive, progressive, and complex-tense forms. It cannot find a word used with two meanings, a missing definition, or an unclear noun pile. Read your English once, slowly, as a non-native reader would.
