# Content modes (variable conditions)

Pick one mode before writing the spec; it decides the scene blueprint, narration register, and which understanding aids (examples, analogies, figures) you add. A mode is a starting outline — merge, split or drop scenes when the source is thin or dense.

## `paper-journal-club` — 论文 → 组会汇报视频

Goal: a lab-meeting walkthrough of one paper. Register: formal but spoken ("这篇文章…", "作者认为…").

Outline (12–18 slides, 8–12 min):
1. cover: paper title (+ 中文意译), authors/venue/year
2. 研究问题与动机 — what problem, why it matters, one `.note` with the key claim
3. 相关工作/前人局限 — `grid2` cards or a small table
4. 方法总览 — a `.flow` of the pipeline; if the paper has a method figure, crop it into `figs/` and use `.fig`
5–7. 方法分模块 — one slide per component (`.split`: figure/diagram + `.card` notes)
8. 实验设置 — datasets/benchmarks/metrics table
9–10. 主要结果 — table of numbers (round aggressively; bold the wins), one number worth a big `.stat`-style card if striking
11. 消融/分析 — what the ablations actually reveal
12. 局限与讨论 — honest `.dodont` or two cards
13. 对我们的启发 — 2–3 takeaways for the group's own work
14. `.summary` recap + 开放问题

Narration rules: never read tables aloud — speak the trend ("提升了三个点，主要来自…"). Every figure gets one "怎么读这张图" sentence.

## `doc-tutorial` — 文档/README → 带示例和类比的讲解视频

Goal: make a doc genuinely understood, not just summarized. Register: friendly, second person.

Outline: cover → 这个东西解决什么问题(1–2) → 核心概念(类比先行) → 逐功能：**每个功能两页** — 先"是什么/为什么"，再"动手示例"(`pre` or `.flow` 或 `.terminal`-style pre showing a real command and its output) → 常见错误/最佳实践 → `.summary` recap。

Understanding aids (the point of this mode):
- **类比**：对每个抽象概念给一个生活类比，用 `<div class="analogy"><b>类比：</b>把 X 想成 Y——…</div>`。类比要贴合文档语义（状态、生命周期、边界），一个概念只给一个，别堆。
- **示例**：能动手的都给可复制运行的命令/代码和真实输出；示例参数要有意义（`/fix-issue 123`，不是 `foo`）。
- **反例**：易错处给 ❌/✅ 对照（`.dodont`）。

## `topic-course` — 主题 → 系列课程一讲

Goal: like `01-slash-commands` — an episode of a course series. Register: 讲给初学者，节奏更快。

Outline: cover → 全景/分类 → 按"用户意图"分组的命令/功能（每个意图 1–2 页）→ 原理/执行流程（`.flow`）→ 现成示例盘点 → 最佳实践 `.dodont` → 排错 → `.summary` 要点 + 预告下一课。

## Choosing voice / theme

- 组会: `zh-CN-YunjianNeural` (沉稳) or Yunyang; cool accent theme, e.g. `{"--acc": "#7aa2f7"}`.
- 教程/课程: default Yunyang + default warm theme.
- Don't change THEME mid-deck; one theme per video.
