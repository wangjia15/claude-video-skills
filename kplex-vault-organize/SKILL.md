---
name: kplex-vault-organize
description: Organize a folder of Markdown paper/article notes into a K-Plex relationship graph by writing frontmatter links — citation links (References) found in each note's reference list and semantic "similar" links from its title, abstract and introduction — plus a translated-title alias, using a local vector index that later runs reuse. Use when the user wants to init/organize/link/cluster the notes in an Obsidian vault or folder for K-Plex, relate papers by relevance, build a paper graph, add topics, or update links after adding new articles ("整理frontmatter", "按相关性关联", "初始化/更新 K-Plex 关系", "新加文章后更新").
---

# K-Plex vault organize

Turns a folder of paper notes into K-Plex relationships:

| Field (default) | K-Plex role | Source |
| --- | --- | --- |
| `References` | parent (cited papers appear above) | the note's own reference list, matched to other notes by arXiv id / DOI / title |
| `similar` | left friend | nearest neighbours of title + abstract + introduction in the vector index |
| `topic` | property (style/lens) | optional clustering, named by you |
| `aliases` (first item) | display name | the English title translated (default Chinese); model names before a colon stay untranslated |
| `abstract_zh` | hover card text | the note's labelled English abstract, translated; only written when empty or previously written by this tool |

The script only replaces links it added itself (tracked in `.kplex/managed.json`); links the user wrote are kept. It writes nothing without `--apply`, backs up every changed file, and `restore` undoes the last apply.

Script: `~/.claude/skills/kplex-vault-organize/scripts/kplex_organize.py` (run with `uv run --script`; dependencies install automatically into an isolated environment). Below, `K` stands for:

```bash
uv run --script ~/.claude/skills/kplex-vault-organize/scripts/kplex_organize.py
```

## init — first organization of a vault

1. Pick the vault root (the folder containing `.obsidian`) and, if the notes live in a subfolder, `--dir <subfolder>`. Ask only if it is genuinely unclear.
2. Dry run: `K init <vault> [--dir notes]`
   - Creates `<vault>/.kplex/` (config, SQLite vector index, report). Obsidian ignores dot-folders.
   - First run downloads the embedding model (~130 MB, `BAAI/bge-small-en-v1.5`). If Hugging Face is unreachable, retry with `HF_ENDPOINT=https://hf-mirror.com`, or use `--backend tfidf` (no download, weaker similarity).
3. Read the JSON summary and skim `<vault>/.kplex/report.md`. Show the user: files that would change, citation/similar link counts, and 3–5 representative examples. Point out anything suspicious (a note that is "similar" to everything, obviously wrong citations).
4. Apply only after the user agrees: `K init <vault> [--dir notes] --apply` (the index is reused; nothing is re-embedded).
5. Tell the user the backup path printed on stderr and that `K restore <vault>` undoes it.

## Translated titles as aliases

`init` and `update` translate each note's paper title (Google Translate, falling back to Bing) and insert it as the **first** `aliases` item, so K-Plex can show it as the node name. Translations are cached in the index; each title is translated once. PDF-header "titles" (for example `arXiv:… [cs.CV]`, `Published as a conference paper…`) and titles already in Chinese are skipped. Only the title text is sent to the translation service; turn it off with `"translate_titles": false`.

To switch between the translated name and the original title in K-Plex, tell the user to set **Settings → K-Plex → Visual styling → Name fields when display names are off** to `title` (leave **Name fields** as `aliases`). The toolbar **Display aliases** button (Aa icon) then toggles 中文别名 ↔ English title.

## Translated abstracts

`init` and `update` also translate each note's labelled abstract (an `Abstract` section or `> Abstract:` line) into `abstract_zh`. K-Plex shows it in the hover abstract card (**Settings → K-Plex → Paper reading → Show abstract on hover**, property order `abstract_zh, abstract, summary`). A value the user or K-Plex wrote is never overwritten. About one minute per ~100 abstracts on first run; cached afterwards. Turn off with `"translate_abstracts": false`.

## update — after adding or editing articles

```bash
K update <vault>            # dry run: only new/changed notes are re-parsed and re-embedded
K update <vault> --apply
```

New notes get their citations and similar links; existing notes gain links to the new ones (for example when an old note's reference list cites the new paper). Links this tool added earlier that no longer qualify are removed. Running update twice changes nothing. Same review-then-apply rule as init; for small updates (≤ 10 files) a one-line summary is enough.

## topics — optional clustering

1. `K topics <vault> export [--k N]` writes `.kplex/topics.json`: clusters with sample titles, each with an empty `"topic"`.
2. Read the titles of each cluster and fill in a short topic name (2–6 words, in the user's language; leave `""` for incoherent clusters). Edit the JSON yourself — this is the step that needs judgement.
3. `K topics <vault> apply` (dry run), then `K topics <vault> apply --apply`. Writes the `topic` property; existing values are replaced only by the new name.

## Other commands

- `K status <vault>` — notes, vectors, notes with reference lists / identifiers, current config.
- `K restore <vault> [--backup .kplex/backups/<file>.jsonl]` — restore the files (and link ownership) from the last or a given apply.

## Making it show up in K-Plex

- `References` is the field K-Plex **Paper reading** registers as a parent field; if paper reading is off, add `References` to **Settings → K-Plex → Ontology → Relationship fields → Parent fields**.
- `similar` is in K-Plex's default left-friend fields. If the user's ontology differs, set `references_field` / `similar_field` in `.kplex/config.json` to fields they already use, then run `update --apply`.
- K-Plex picks up frontmatter changes incrementally; no rebuild is needed.

## Rules

- Never pass `--apply` before the user has seen the dry-run summary for this vault (init, first update of a session, or topics).
- Do not edit `.kplex/index.sqlite` or `.kplex/managed.json` by hand; change behaviour through `.kplex/config.json` (see [references/configuration.md](references/configuration.md)).
- Files that are not valid UTF-8 are skipped, never rewritten.
- If results look wrong (too many/too few similar links, missed citations), tune the config and rerun a dry run instead of hand-editing notes. Typical knobs: `similar_percentile`, `similar_top_k`, `id_fields`, `title_fields`, `notes_dir`, `exclude`.
