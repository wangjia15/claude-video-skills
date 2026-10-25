# Writing the deep-reading note

The note is the K-Plex centre node. Its headings become section cards; `==highlight==[^n]` passages and their footnotes appear as quotes with comments under each section; images with a caption line below them appear as figures. Write for a reader who wants to understand the paper without opening the PDF.

## Frontmatter

Keep what `extract` wrote (`title`, `aliases`, `authors`, `year`, `venue`, `arxiv`/`doi`, `url`, `pdf`, `Note type`, `References`). Add:

```yaml
aliases:
  - "中文标题"            # first item = K-Plex display name; keep the English title as the second item
abstract_zh: "中文摘要…"   # hover abstract card
tldr: "一句话总结"
keywords: [..]
```

`References` is filled by `check --fix`; do not hand-edit its links.

## Body layout

```markdown
# <Title>

> [!summary] 一句话总结
> 解决什么问题、核心想法、主要结果（带数字）。

> [!abstract] 阅读地图
> - 问题 / 动机：…
> - 方法：…（模块名）
> - 结果：…
> - 局限：…

## Abstract
<original abstract>

## 摘要
<translation>

## I. Introduction          ← mirror the paper's numbering and titles exactly
### A. …

## 核心概念                 ← glossary of every non-trivial term used above
## 公式速查                 ← optional: all equations in one table (number, meaning)
## 参考文献                 ← numbered list linking to the cards
```

Appendix sections are included when the PDF has them (after the conclusion, before 核心概念).

## Inside each section

**Prose.** Explain the section's argument in the user's language, in order, as a careful reader would: what is claimed, why, how, and what evidence supports it. Do not just translate; add the missing background a newcomer needs. Keep numbers exact.

**Highlights.** Quote the 2–5 most important original sentences per section, each on its own line:

```markdown
==we propose AR-MOT, a novel autoregressive paradigm that formulates MOT as a sequence generation task==[^3]
```

with the footnote at the end of the note explaining it (meaning, why it matters, caveats). Footnote bodies may span several indented lines. Never put a highlight inside a callout or table.

**Concepts.** Explain each complex concept where it first appears:

```markdown
> [!info] 概念 · Region-Aware Alignment (RAA)
> 定义 / 直觉（类比）/ 在本文中的作用 / 与相近概念的区别
```

**Figures and tables.** Every item in `manifest.json → figures`, placed where the paper discusses it:

```markdown
![[images/fig-2.png]]

Figure 2: <caption from manifest>

> [!note] 图解
> 逐区域说明图中内容（按 (a)(b)… 或从左到右）、数据流/坐标轴含义、结论，以及它支撑了正文哪个论点。
```

The caption line must be within two lines below the embed (K-Plex reads it as the figure caption). For tables, additionally transcribe the key rows as a Markdown table when readable, and state what the numbers show (best result, deltas, ablation conclusion). Optionally add a source link using `pdfpp` from the manifest: `[[<pdfpp>|原文 p.N]]`.

**Formulas.** Transcribe from the page image into LaTeX (Obsidian MathJax):

```markdown
$$
\text{maximize}\ \sum_{j=1}^{N_i} \log P\big(s_{ID_i^j} \mid s_{past_i^j}\big) \tag{4}
$$

> [!tip] 公式 (4) 解读
> - 符号：$N_i$ 第 $i$ 帧目标数；$s_{ID_i^j}$ …（逐个说明）
> - 直觉：…
> - 作用：…；与公式 (5) 的关系：…
```

Every numbered equation needs `\tag{N}` with the paper's number (check verifies this). Inline maths uses `$…$`. Multi-line derivations use `\begin{aligned}…\end{aligned}` inside one `$$` block. If a formula is unreadable, embed nothing invented; write that it could not be read and point to the page.

**Citations.** Replace citation markers with links from `.work/refs.json`: `[12]` → `[[<link>|[12]]]`; author-year citations link the matching entry by first author and year. Unresolved references stay plain text.

## 参考文献 section

```markdown
## 参考文献
- [1] [[<link>|<title>]] (<year>)
- [2] <raw reference text>   ← unresolved
```

## Quality bar

- All figures, tables and numbered equations present; nothing summarised away.
- Each formula and complex concept explained, not only restated.
- Claims attributed correctly: separate what the authors claim from what experiments show; note limitations.
- Consistent terminology: first use gives the English term in parentheses, e.g. 多目标跟踪（MOT）.
