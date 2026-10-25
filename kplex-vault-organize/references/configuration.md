# `.kplex/config.json`

Created by `init`; edit it and rerun `update` (dry run first). Unknown keys are ignored.

| Key | Default | Meaning |
| --- | --- | --- |
| `notes_dir` | `""` | Folder to organize, relative to the vault (`""` = whole vault). Set by `init --dir`. |
| `exclude` | `.obsidian, .kplex, .trash, templates, Templates` | Folder names skipped anywhere in the path. Dot-folders are always skipped. |
| `id_fields` | `doi, arxiv, url, source` | Frontmatter properties read for arXiv ids / DOIs (values like `arXiv:2104.09864`, `https://arxiv.org/abs/…`, `10.1038/…`). Used to match citations. |
| `title_fields` | `title, aliases` | Properties used as the note's titles for citation matching (the file name is always added). Truncated titles still match by prefix (≥ 20 characters). |
| `references_field` | `References` | Property that receives citation links (K-Plex parent field). |
| `similar_field` | `similar` | Property that receives similar-note links (K-Plex left-friend field). |
| `topic_field` | `topic` | Property written by `topics apply`. |
| `backend` | `fastembed` | `fastembed` (local ONNX embeddings, stored in the vector index) or `tfidf` (no model download; recomputed each run). |
| `model` | `BAAI/bge-small-en-v1.5` | fastembed model. For mostly Chinese notes try `BAAI/bge-small-zh-v1.5`; for mixed languages `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Changing it re-embeds everything once. |
| `similar_top_k` | `5` | Maximum similar links per note. `0` disables similar links. |
| `similar_min_score` | `"auto"` | `"auto"` = only pairs above the `similar_percentile` of all pair scores in this collection qualify; or a fixed cosine value such as `0.85`. |
| `similar_percentile` | `90` | Used by `"auto"`. Raise (e.g. 95) for fewer, stronger links. |
| `translate_titles` | `true` | Add the translated paper title as the first alias. |
| `translate_target` | `zh-CN` | Target language (`zh-CN`, `zh-TW`, `ja`, `en`, …). |
| `translator` | `google` | `google` or `bing`; the other one is tried when it fails. |
| `alias_field` | `aliases` | Property that receives the translated title. |
| `translate_abstracts` | `true` | Translate labelled abstracts into `abstract_field`. |
| `abstract_field` | `abstract_zh` | Property for the translated abstract (read by the K-Plex hover card). |
| `max_embed_chars` | `2400` | Characters of title + abstract + summary + introduction that are embedded. |

## What is read from each note

- **Abstract**: a heading/line `Abstract` / `摘要`, an inline `Abstract: …` (also inside `> ` quotes), else the opening prose. Web-page chrome of crawled notes (arXiv "Skip to main content", "Submitted on", …) is ignored.
- **Introduction**: the section after `Introduction` / `1 Introduction` / `引言`.
- **Summary**: a `summary` frontmatter property, if present.
- **References**: the last `References` / `Bibliography` / `参考文献` section; numbered (`[1]`, `1.`, `- \[1\]`), author-year and LNCS styles, with PDF page noise removed. Entries are matched to notes by arXiv id / DOI first, then by normalized title.

Similar links are hubness-corrected (a note that is close to everything is ranked down), exclude pairs already connected by a citation, and appear on only one of the two notes.
