#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = [
#   "numpy>=1.26",
#   "ruamel.yaml>=0.18",
#   "fastembed>=0.4",
# ]
# ///
"""
kplex_organize — organize Markdown paper notes into a K-Plex relationship graph.

For every note in a folder it extracts the abstract, introduction and reference list,
embeds "title + abstract + introduction" into a local vector store (.kplex/index.sqlite),
and writes K-Plex frontmatter:

  References: ["[[cited note]]", ...]   citation links found in the reference list (parent field)
  similar:    ["[[related note]]", ...] nearest neighbours by meaning (friend field)
  topic:      <name>                    optional, from `topics apply`
  aliases:    [<translated title>, ...] English title translated (default Chinese), inserted first
  abstract_zh: <translated abstract>    abstract translated (only when absent or written by this tool)

Only links this tool added before are replaced on later runs; links you add by hand are kept.
Nothing is written without --apply, and every write is backed up (see `restore`).

Commands:
  init    <vault> [--dir notes] [--apply]   create .kplex/, index everything, plan/apply links
  update  <vault> [--apply]                 index new/changed notes only, re-plan, apply diff
  status  <vault>                           index statistics
  topics  <vault> export|apply FILE         cluster notes / write topic names chosen by a person or agent
  restore <vault> [--backup FILE]           undo the last (or a given) --apply
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import io
import json
import math
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np

STATE_DIR = ".kplex"
DEFAULT_CONFIG = {
    "notes_dir": "",                       # relative to the vault; "" = whole vault
    "exclude": [".obsidian", ".kplex", ".trash", "templates", "Templates"],
    "id_fields": ["doi", "arxiv", "url", "source"],
    "title_fields": ["title", "aliases"],
    "references_field": "References",      # K-Plex parent field (paper reading mode default)
    "similar_field": "similar",            # K-Plex left-friend field (default ontology)
    "topic_field": "topic",
    "backend": "fastembed",                # fastembed | tfidf
    "model": "BAAI/bge-small-en-v1.5",
    "similar_top_k": 5,
    "similar_min_score": "auto",           # "auto" = similar_percentile of all pair scores, or a cosine value
    "similar_percentile": 90,
    "max_embed_chars": 2400,
    "translate_titles": True,              # add a translated title as the first alias
    "translate_target": "zh-CN",
    "translator": "google",                # google | bing (the other is tried on failure)
    "alias_field": "aliases",
    "translate_abstracts": True,           # store the translated abstract in abstract_field
    "abstract_field": "abstract_zh",
}

# --------------------------------------------------------------------------------------------
# Frontmatter / Markdown parsing

FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)


def split_frontmatter(text: str) -> tuple[str | None, str]:
    match = FRONTMATTER.match(text)
    if not match:
        return None, text
    return match.group(1), text[match.end():]


def yaml_rt():
    from ruamel.yaml import YAML
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.width = 100000
    yaml.indent(mapping=2, sequence=2, offset=0)
    return yaml


def load_frontmatter(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        from ruamel.yaml import YAML
        data = YAML(typ="safe", pure=True).load(raw)
        return data if isinstance(data, dict) else {}
    except Exception:  # malformed YAML: treat as no frontmatter, never crash the run
        return {}


ABSTRACT_HEAD = re.compile(r"^\s*(?:#{1,6}\s*)?(?:abstract|摘要)\s*[:.]?\s*$", re.I)
ABSTRACT_INLINE = re.compile(r"^\s*(?:>\s*)?(?:\*\*)?abstract(?:\*\*)?\s*[:.—-]\s*(.+)$", re.I)
# Web-page chrome that crawled notes share (arXiv abs pages etc.); it must not drive similarity.
BOILERPLATE = re.compile(r"skip to main content|press enter to search|advanced search|submitted on|view a pdf of|computer science >|cite as:|bibliographic tools|access paper", re.I)
INTRO_HEAD = re.compile(r"^\s*(?:#{1,6}\s*)?(?:(?:\d+|[IVX]+)\.?\s+)?(?:introduction|引言|简介)\s*$", re.I)
SECTION_HEAD = re.compile(r"^\s*(?:#{1,6}\s+\S|(?:\d+|[IVX]+)\.?\s+[A-Z][A-Za-z ,:-]{2,60}$)")
REFERENCE_HEAD = re.compile(r"^\s*(?:#{1,6}\s*)?(?:\d+\.?\s*)?(?:references|bibliography|works cited|参考文献)\s*:?\s*$", re.I)


def section_after(lines: list[str], start: int, limit_chars: int) -> str:
    out: list[str] = []
    size = 0
    for line in lines[start:]:
        if out and (SECTION_HEAD.match(line) or INTRO_HEAD.match(line) or REFERENCE_HEAD.match(line)):
            break
        out.append(line.strip())
        size += len(line)
        if size >= limit_chars:
            break
    return re.sub(r"\s+", " ", " ".join(out)).strip()


def clean_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)            # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)          # links → their text
    text = re.sub(r"https?://\S+", " ", text)
    return text


def extract_sections(body: str) -> dict[str, str]:
    lines = [l for l in clean_markdown(body).splitlines() if not BOILERPLATE.search(l)]
    abstract = intro = ""
    for i, line in enumerate(lines[:600]):
        if not abstract:
            if ABSTRACT_HEAD.match(line):
                abstract = section_after(lines, i + 1, 3000)
            else:
                m = ABSTRACT_INLINE.match(line)
                if m:
                    abstract = (m.group(1) + " " + section_after(lines, i + 1, 3000)).strip()
        if not intro and INTRO_HEAD.match(line):
            intro = section_after(lines, i + 1, 3000)
        if abstract and intro:
            break
    labelled = abstract
    if not abstract:
        # No labelled abstract: use the opening prose (skip very short lines such as author names).
        prose = [l.strip() for l in lines[:200] if len(l.strip()) > 60]
        abstract = re.sub(r"\s+", " ", " ".join(prose))[:1500]
    return {"abstract": abstract, "labelled_abstract": labelled, "introduction": intro}


# ---- reference list parsing (mirrors K-Plex src/paper/ReferenceParser.ts) -----------------

SECTION_END = re.compile(r"^\s*(?:#{1,6}\s*)?(?:(?:[A-Z]|\d+)[.:]?\s+)?(?:appendix|appendices|supplementary(?: material)?|checklist)\b", re.I)
NUMBERED_ENTRY = re.compile(r"^\s*(?:[-*+]\s+)?(?:\\?\[(\d{1,4})\\?\]|(\d{1,4})\.\s)")
ENTRY_END = re.compile(r"\b(?:19|20)\d{2}[a-z]?\.\s*$")
TRAILING = re.compile(r"^(?:URL\s|doi:|https?://|[\w./?=&%-]+\.(?:pdf|html?)\.?$|[0-9a-f]{12,}\S*$)", re.I)
ARXIV_IN_TEXT = re.compile(r"arxiv[:\s/,]*(?:abs/)?(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
DOI_IN_TEXT = re.compile(r"\b(10\.\d{4,9}/[^\s,;]+)")
YEAR = re.compile(r"\b(19[5-9]\d|20\d{2})[a-z]?\b")


def reference_section(body: str) -> str | None:
    lines = body.splitlines()
    start = -1
    for i in range(len(lines) - 1, -1, -1):
        if REFERENCE_HEAD.match(lines[i]):
            start = i + 1
            break
    if start < 0:
        return None
    out = []
    for line in lines[start:start + 4000]:
        if SECTION_END.match(line) and not NUMBERED_ENTRY.match(line) and len(line.strip()) < 80:
            break
        out.append(line)
    text = "\n".join(out).strip()
    return text or None


def join_lines(lines: list[str]) -> str:
    out = ""
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if not out:
            out = line
        elif re.search(r"[A-Za-z0-9]-$", out) and re.match(r"^[a-z]", line):
            word = re.search(r"(\S+)-$", out).group(1)
            out = out + line if re.search(r"[-\d]", word) else out[:-1] + line
        else:
            out += " " + line
    return out


def without_page_noise(lines: list[str]) -> list[str]:
    out, after_break = [], False
    for line in lines:
        t = line.strip()
        if re.fullmatch(r"-{3,}|\*{3,}", t):
            after_break = True
            continue
        if re.fullmatch(r"\d{1,4}", t):
            continue
        if after_break and t:
            after_break = False
            if len(t) < 60 and not re.search(r"[.,;:]", t):
                continue
        out.append(line)
    return out


def split_entries(section: str) -> list[str]:
    lines = without_page_noise(section.splitlines())
    entries: list[str] = []
    if sum(1 for l in lines if NUMBERED_ENTRY.match(l)) >= 3:
        cur: list[str] = []
        for line in lines:
            if NUMBERED_ENTRY.match(line):
                if cur:
                    entries.append(join_lines(cur))
                cur = [NUMBERED_ENTRY.sub("", line, count=1)]
            elif cur:
                cur.append(line)
        if cur:
            entries.append(join_lines(cur))
    elif sum(1 for l in lines if ENTRY_END.search(l.strip())) >= 3:
        groups: list[list[str]] = []
        cur = []
        for line in lines:
            t = line.strip()
            if not t:
                continue
            if not cur and groups and TRAILING.match(t):
                groups[-1].append(t)
                continue
            cur.append(t)
            if ENTRY_END.search(t):
                groups.append(cur)
                cur = []
        if cur:
            groups.append(cur)
        entries = [join_lines(g) for g in groups]
    else:
        cur = []
        for line in lines:
            if not line.strip():
                if cur:
                    entries.append(join_lines(cur))
                cur = []
            else:
                cur.append(line)
        if cur:
            entries.append(join_lines(cur))
    return [e for e in entries if len(e) >= 20][:500]


ABBREV = re.compile(r"^(?:[A-Z]|[A-Z][a-z]|[A-Z]\.[A-Z]|al|et|vs|eds?|pp|vol|no|Proc|Conf|Int|Jr|Sr|St|Dr|Inc|Ltd)$")


def sentences(entry: str) -> list[str]:
    parts, start = [], 0
    for m in re.finditer(r"([.?!])\s+", entry):
        tail = re.search(r"([A-Za-z.]+)$", entry[start:m.start()])
        word = tail.group(1) if tail else ""
        if m.group(1) == "." and ABBREV.match(word.rstrip(".")):
            continue
        parts.append(entry[start:m.start() + 1].strip())
        start = m.end()
    if start < len(entry):
        parts.append(entry[start:].strip())
    return [p for p in parts if p]


def parse_entry(entry: str) -> dict | None:
    text = re.sub(r"\s+", " ", entry).strip()
    ids = []
    m = ARXIV_IN_TEXT.search(text)
    if m:
        ids.append(f"arxiv:{m.group(1)}")
    m = DOI_IN_TEXT.search(text)
    if m:
        doi = m.group(1).rstrip(".,;:)]}").lower()
        arx = re.match(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})", doi)
        ids.append(f"arxiv:{arx.group(1)}" if arx else f"doi:{doi}")
    title = ""
    apa = re.match(r"^(.+?)\s*\((?:19|20)\d{2}[a-z]?\)\.?\s+(.+)$", text)
    lncs = re.match(r"^(.{3,400}?\b[A-Z][a-z]?\.(?:,?\s*et al\.)?):\s+(.+)$", text)
    if lncs and not (apa and ":" in apa.group(1)):
        title = (sentences(lncs.group(2)) or [""])[0]
    elif apa:
        title = (sentences(apa.group(2)) or [""])[0]
    else:
        parts = sentences(text)
        title = parts[1] if len(parts) >= 2 else (parts[0] if parts else "")
    title = re.sub(r"^[\"“'‘]+|[\"”'’]+$", "", title).rstrip(".,")
    title = re.sub(r"\s*\((?:19|20)\d{2}[a-z]?\)$", "", title).strip()
    if len(title) < 8 or re.match(r"^(?:in|arxiv preprint|proceedings)\b", title, re.I):
        title = ""
    if not title and not ids:
        return None
    years = YEAR.findall(text)
    return {"title": title, "ids": sorted(set(ids)), "year": int(years[-1]) if years else None}


def parse_references(body: str) -> list[dict]:
    section = reference_section(body)
    if not section:
        return []
    return [r for r in (parse_entry(e) for e in split_entries(section)) if r]


# ---- identifiers ----------------------------------------------------------------------------

def paper_ids(value) -> list[str]:
    out: list[str] = []
    if isinstance(value, list):
        for item in value:
            out += paper_ids(item)
        return out
    if not isinstance(value, (str, int, float)):
        return out
    text = str(value).strip()
    m = re.search(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})", text, re.I) or re.match(r"^(?:arxiv:\s*)?(\d{4}\.\d{4,5})(?:v\d+)?$", text, re.I)
    if m:
        return [f"arxiv:{m.group(1)}"]
    m = re.search(r"(10\.\d{4,9}/[^\s\"'<>]+)", text)
    if m:
        doi = m.group(1).rstrip(".,;:)]}").lower()
        arx = re.match(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})", doi)
        return [f"arxiv:{arx.group(1)}" if arx else f"doi:{doi}"]
    return out


def norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9一-鿿]+", " ", title.lower()).strip()


# --------------------------------------------------------------------------------------------
# Vector store (SQLite; brute-force cosine in numpy — fine for tens of thousands of notes)

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
  path TEXT PRIMARY KEY,
  content_hash TEXT NOT NULL,
  title TEXT NOT NULL,
  titles TEXT NOT NULL,
  ids TEXT NOT NULL,
  refs TEXT NOT NULL,
  embed_text TEXT NOT NULL,
  indexed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS abstracts (
  path TEXT PRIMARY KEY,
  text TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS translations (
  source TEXT NOT NULL,
  target TEXT NOT NULL,
  text TEXT NOT NULL,
  PRIMARY KEY (source, target)
);
CREATE TABLE IF NOT EXISTS vectors (
  path TEXT PRIMARY KEY,
  model TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  dim INTEGER NOT NULL,
  vec BLOB NOT NULL
);
"""


class Store:
    def __init__(self, vault: Path):
        self.dir = vault / STATE_DIR
        self.dir.mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.dir / "index.sqlite")
        self.db.executescript(SCHEMA)

    def notes(self) -> dict[str, dict]:
        rows = self.db.execute("SELECT path, content_hash, title, titles, ids, refs, embed_text FROM notes").fetchall()
        return {r[0]: {"hash": r[1], "title": r[2], "titles": json.loads(r[3]), "ids": json.loads(r[4]),
                       "refs": json.loads(r[5]), "embed_text": r[6]} for r in rows}

    def upsert(self, path: str, note: dict) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO notes VALUES (?,?,?,?,?,?,?,?)",
            (path, note["hash"], note["title"], json.dumps(note["titles"], ensure_ascii=False), json.dumps(note["ids"]),
             json.dumps(note["refs"], ensure_ascii=False), note["embed_text"], _dt.datetime.now().isoformat(timespec="seconds")),
        )

    def put_abstract(self, path: str, text: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO abstracts VALUES (?,?)", (path, text))

    def abstracts(self) -> dict[str, str]:
        return dict(self.db.execute("SELECT path, text FROM abstracts").fetchall())

    def delete(self, path: str) -> None:
        self.db.execute("DELETE FROM abstracts WHERE path=?", (path,))
        self.db.execute("DELETE FROM notes WHERE path=?", (path,))
        self.db.execute("DELETE FROM vectors WHERE path=?", (path,))

    def vectors(self, model: str) -> dict[str, tuple[str, np.ndarray]]:
        rows = self.db.execute("SELECT path, content_hash, dim, vec FROM vectors WHERE model=?", (model,)).fetchall()
        return {r[0]: (r[1], np.frombuffer(r[3], dtype=np.float32).reshape(r[2])) for r in rows}

    def put_vector(self, path: str, model: str, content_hash: str, vec: np.ndarray) -> None:
        v = np.asarray(vec, dtype=np.float32)
        self.db.execute("INSERT OR REPLACE INTO vectors VALUES (?,?,?,?,?)", (path, model, content_hash, v.shape[0], v.tobytes()))

    def translations(self, target: str) -> dict[str, str]:
        return dict(self.db.execute("SELECT source, text FROM translations WHERE target=?", (target,)).fetchall())

    def put_translation(self, source: str, target: str, text: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO translations VALUES (?,?,?)", (source, target, text))

    def commit(self) -> None:
        self.db.commit()


# --------------------------------------------------------------------------------------------
# Embedding backends


def embed_fastembed(texts: list[str], model: str) -> np.ndarray:
    from fastembed import TextEmbedding
    embedder = TextEmbedding(model_name=model)
    vecs = np.array(list(embedder.embed(texts, batch_size=32)), dtype=np.float32)
    return vecs / np.maximum(np.linalg.norm(vecs, axis=1, keepdims=True), 1e-12)


TOKEN = re.compile(r"[a-z][a-z0-9-]{2,}|[一-鿿]")
STOP = set("the and for with this that from are was were been have has our their which using use based into than more also can such these those its not but all any each other between over under via new two one".split())


def tfidf_matrix(texts: list[str]) -> np.ndarray:
    docs = []
    for text in texts:
        toks = [t for t in TOKEN.findall(text.lower()) if t not in STOP]
        cjk = [a + b for a, b in zip(toks, toks[1:]) if len(a) == 1 and len(b) == 1]
        docs.append([t for t in toks if len(t) > 1] + cjk)
    vocab: dict[str, int] = {}
    df: dict[str, int] = {}
    for doc in docs:
        for tok in set(doc):
            df[tok] = df.get(tok, 0) + 1
    n = len(docs)
    for tok, count in df.items():
        if 1 < count <= max(2, int(n * 0.6)):
            vocab[tok] = len(vocab)
    mat = np.zeros((n, max(1, len(vocab))), dtype=np.float32)
    for i, doc in enumerate(docs):
        for tok in doc:
            j = vocab.get(tok)
            if j is not None:
                mat[i, j] += 1
    idf = np.log((1 + n) / (1 + np.array([df[t] for t in vocab] or [1], dtype=np.float32))) + 1
    mat = np.log1p(mat) * idf
    return mat / np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-12)


# --------------------------------------------------------------------------------------------
# Scanning


@dataclass
class Vault:
    root: Path
    config: dict

    @property
    def state(self) -> Path:
        return self.root / STATE_DIR

    def note_paths(self) -> list[Path]:
        base = self.root / self.config["notes_dir"] if self.config["notes_dir"] else self.root
        excluded = set(self.config["exclude"])
        out = []
        for path in sorted(base.rglob("*.md")):
            rel = path.relative_to(self.root)
            if any(part in excluded or part.startswith(".") for part in rel.parts[:-1]):
                continue
            out.append(path)
        return out


def load_config(root: Path) -> dict:
    path = root / STATE_DIR / "config.json"
    config = dict(DEFAULT_CONFIG)
    if path.exists():
        config.update(json.loads(path.read_text(encoding="utf-8")))
    return config


def analyse(vault: Vault, path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    raw, body = split_frontmatter(text)
    fm = load_frontmatter(raw)
    lower = {str(k).lower(): v for k, v in fm.items()}
    titles: list[str] = []
    for key in vault.config["title_fields"]:
        value = lower.get(key.lower())
        titles += [str(v) for v in (value if isinstance(value, list) else [value]) if isinstance(v, (str, int)) and str(v).strip()]
    titles.append(path.stem)
    ids = sorted({i for key in vault.config["id_fields"] for i in paper_ids(lower.get(key.lower()))})
    sections = extract_sections(body)
    summary = lower.get("summary") if isinstance(lower.get("summary"), str) else ""
    embed_text = "\n".join(filter(None, [titles[0], sections["abstract"], summary, sections["introduction"]]))[: vault.config["max_embed_chars"]]
    refs = parse_references(body)
    content_hash = hashlib.sha256((embed_text + json.dumps(refs, sort_keys=True) + json.dumps(ids)).encode()).hexdigest()[:16]
    return {"hash": content_hash, "title": titles[0], "titles": titles, "ids": ids, "refs": refs, "embed_text": embed_text,
            "abstract": sections["labelled_abstract"], "has_intro": bool(sections["introduction"])}


def index(vault: Vault, store: Store, log) -> dict:
    """Refresh the note table and vectors; returns counts. Only new/changed notes are re-embedded."""
    known = store.notes()
    paths = vault.note_paths()
    seen = set()
    changed: list[str] = []
    stats = {"notes": len(paths), "new": 0, "changed": 0, "removed": 0, "embedded": 0, "with_refs": 0}
    for path in paths:
        rel = path.relative_to(vault.root).as_posix()
        seen.add(rel)
        note = analyse(vault, path)
        if note["refs"]:
            stats["with_refs"] += 1
        store.put_abstract(rel, note["abstract"])
        old = known.get(rel)
        if old is None or old["hash"] != note["hash"]:
            stats["new" if old is None else "changed"] += 1
            store.upsert(rel, note)
            changed.append(rel)
    for rel in set(known) - seen:
        store.delete(rel)
        stats["removed"] += 1
        log(f"removed from index (file no longer present): {rel}")

    if vault.config["backend"] == "fastembed":
        model = vault.config["model"]
        notes = store.notes()
        vectors = store.vectors(model)
        todo = [p for p, n in notes.items() if p not in vectors or vectors[p][0] != n["hash"]]
        if todo:
            log(f"embedding {len(todo)} note(s) with {model} …")
            vecs = embed_fastembed([notes[p]["embed_text"] or notes[p]["title"] for p in todo], model)
            for p, v in zip(todo, vecs):
                store.put_vector(p, model, notes[p]["hash"], v)
            stats["embedded"] = len(todo)
    store.commit()
    return stats


# --------------------------------------------------------------------------------------------
# Title translation (aliases). Same public web endpoints as K-Plex paper reading.

BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
CJK = re.compile(r"[\u3400-\u9fff]")
# Titles that are really PDF headers / site chrome, not paper titles.
NOT_A_TITLE = re.compile(
    r"^(?:arxiv:\d|journal of latex class files|published as a conference paper|contents lists available|ieee transactions on|"
    r"preprint|under review|cvpr \d{4} open access|\(ijacsa\)|international journal of|proceedings of)", re.I)


def clean_title(title: str) -> str | None:
    """Paper title suitable for translation, or None (already translated, too short, or not a title)."""
    t = re.sub(r"^\[\d{4}\.\d{4,5}\]\s*", "", title.strip())            # "[2104.12763] …"
    t = re.sub(r"\s+(?:-|\||·)\s+(?:PMC|PLOS One|Medium|Frontiers|Scientific Reports|Ultralytics|ScienceDirect|arXiv)\b.*$", "", t, flags=re.I)
    t = re.sub(r"^Frontiers\s*\|\s*", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) < 8 or CJK.search(t) or NOT_A_TITLE.match(t):
        return None
    return t


NAME_PREFIX = re.compile(r"^([^:：]{1,32})\s*[:：]\s*(.{8,})$")


def split_name_prefix(title: str) -> tuple[str, str]:
    """("Ferret", "Refer and Ground …") for "Ferret: Refer and Ground …": model/dataset names stay untranslated."""
    m = NAME_PREFIX.match(title)
    if m:
        words = m.group(1).split()
        # A name is one word ("Ferret"), or words with digits / inner capitals ("Florence-2",
        # "nuScenes", "Mamba YOLO"); ordinary title phrases ("Detecting What Matters") are translated.
        looks_like_name = len(words) == 1 or any(
            re.search(r"\d|[A-Z]", part[1:]) for word in words for part in word.split("-") if part)
        if len(words) <= 3 and looks_like_name:
            return m.group(1).strip(), m.group(2).strip()
    return "", title


def _http(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 20) -> tuple[int, str]:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": BROWSER_UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, ""


def translate_google(text: str, target: str) -> str:
    url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&dt=t&tl=" + urllib.parse.quote(target)
    status, body = _http(url, urllib.parse.urlencode({"q": text}).encode(), {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    if status != 200:
        raise RuntimeError(f"Google Translate HTTP {status}")
    return "".join(seg[0] for seg in json.loads(body)[0] if seg and seg[0])


_BING: dict = {}


def translate_bing(text: str, target: str) -> str:
    to = {"zh-CN": "zh-Hans", "zh-TW": "zh-Hant"}.get(target, target)
    for host in ([_BING["host"]] if _BING.get("host") else []) + ["www.bing.com", "cn.bing.com"]:
        status, page = _http(f"https://{host}/translator")
        ig = re.search(r'IG:"([0-9A-Fa-f]+)"', page)
        iid = re.search(r'data-iid="(translator\.[^"]+)"', page)
        params = re.search(r'params_AbusePreventionHelper\s*=\s*\[\s*(\d+)\s*,\s*"([^"]+)"', page)
        if status != 200 or not ig or not params:
            continue
        form = urllib.parse.urlencode({"fromLang": "auto-detect", "to": to, "text": text, "key": params.group(1), "token": params.group(2)}).encode()
        url = f"https://{host}/ttranslatev3?isVertical=1&IG={ig.group(1)}&IID={(iid.group(1) if iid else 'translator.5023')}.1"
        status, body = _http(url, form, {"Content-Type": "application/x-www-form-urlencoded", "Referer": f"https://{host}/translator"})
        if status == 200 and body.strip().startswith("["):
            _BING["host"] = host
            return json.loads(body)[0]["translations"][0]["text"]
    raise RuntimeError("Bing Translator unavailable")


def translate_long(text: str, target: str, preferred: str) -> str | None:
    """Translate one long text in sentence-aligned chunks small enough for either service."""
    order = [translate_google, translate_bing] if preferred != "bing" else [translate_bing, translate_google]
    sentences_ = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", text)
    chunks, cur = [], ""
    for sentence in sentences_:
        if cur and len(cur) + len(sentence) + 1 > 850:
            chunks.append(cur)
            cur = sentence
        else:
            cur = f"{cur} {sentence}".strip()
    if cur:
        chunks.append(cur)
    out = []
    for chunk in chunks:
        done = None
        for fn in order:
            try:
                done = fn(chunk, target).strip()
                break
            except Exception:
                continue
        if not done:
            return None
        out.append(done)
    joiner = "" if target.startswith(("zh", "ja")) else " "
    return joiner.join(out)


def translate_texts(texts: list[str], target: str, preferred: str, log) -> dict[str, str]:
    """Translate paragraphs (abstracts): Google in ~4000-character batches, else chunk by chunk."""
    out: dict[str, str] = {}
    batches, cur, size = [], [], 0
    for text in texts:
        if cur and size + len(text) > 4000:
            batches.append(cur)
            cur, size = [], 0
        cur.append(text)
        size += len(text) + 2
    if cur:
        batches.append(cur)
    for number, batch in enumerate(batches, 1):
        log(f"  abstracts batch {number}/{len(batches)}")
        parts: list[str] = []
        if preferred != "bing":
            try:
                parts = [x.strip() for x in re.split(r"\n\s*\n", translate_google("\n\n".join(batch), target)) if x.strip()]
            except Exception:
                parts = []
        if len(parts) == len(batch):
            out.update(zip(batch, parts))
            continue
        for text in batch:
            value = translate_long(text, target, preferred)
            if value:
                out[text] = value
    return out


def abstract_translations(vault: Vault, store: Store, log) -> dict[str, str]:
    """Translated abstract per note path (cached; only labelled English abstracts are translated)."""
    if not vault.config.get("translate_abstracts", True):
        return {}
    target = vault.config.get("translate_target", "zh-CN")
    abstracts = {p: re.sub(r"\s+", " ", t).strip() for p, t in store.abstracts().items() if t}
    wanted = {p: t for p, t in abstracts.items() if len(t) >= 80 and len(CJK.findall(t)) < len(t) * 0.2}
    cache = store.translations(target)
    todo = sorted({t for t in wanted.values() if t not in cache})
    if todo:
        log(f"translating {len(todo)} abstract(s) to {target} …")
        for src, text in translate_texts(todo, target, vault.config.get("translator", "google"), log).items():
            store.put_translation(src, target, text)
        store.commit()
        cache = store.translations(target)
        missing = [t for t in todo if t not in cache]
        if missing:
            log(f"{len(missing)} abstract(s) could not be translated now; they will be retried on the next run")
    return {p: cache[t] for p, t in wanted.items() if t in cache}


def translate_batch(lines: list[str], target: str, preferred: str) -> dict[str, str]:
    """Translate titles in batches separated by blank lines (both services keep them); unaligned batches are retried one by one."""
    order = [translate_google, translate_bing] if preferred != "bing" else [translate_bing, translate_google]
    out: dict[str, str] = {}

    def one(text: str) -> str | None:
        for fn in order:
            try:
                return fn(text, target).strip()
            except Exception:
                continue
        return None

    for start in range(0, len(lines), 25):
        batch = lines[start:start + 25]
        joined = None
        for fn in order:
            try:
                joined = fn("\n\n".join(batch), target)
                break
            except Exception:
                continue
        parts = [x.strip() for x in re.split(r"\n\s*\n", joined or "") if x.strip()]
        if len(parts) == len(batch):
            out.update(zip(batch, parts))
        else:
            for line in batch:
                value = one(line)
                if value:
                    out[line] = value
    return out


def title_aliases(vault: Vault, store: Store, log) -> dict[str, str]:
    """Translated title per note path (cached in the index, so each title is translated once)."""
    if not vault.config.get("translate_titles", True):
        return {}
    target = vault.config.get("translate_target", "zh-CN")
    notes = store.notes()
    cache = store.translations(target)
    parts: dict[str, tuple[str, str]] = {}
    for p, n in notes.items():
        title = clean_title(n["title"])
        if title:
            parts[p] = split_name_prefix(title)
    todo = sorted({rest for _, rest in parts.values() if rest not in cache})
    if todo:
        log(f"translating {len(todo)} title(s) to {target} …")
        for src, text in translate_batch(todo, target, vault.config.get("translator", "google")).items():
            if text and text.lower() != src.lower():
                store.put_translation(src, target, text)
        store.commit()
        cache = store.translations(target)
        missing = [t for t in todo if t not in cache]
        if missing:
            log(f"{len(missing)} title(s) could not be translated now; they will be retried on the next run")
    out = {}
    for p, (name, rest) in parts.items():
        if rest in cache:
            text = cache[rest].strip().rstrip("。")
            out[p] = f"{name}：{text}" if name else text
    return out


# --------------------------------------------------------------------------------------------
# Relationship planning


def link_target(path: str, basenames: dict[str, int]) -> str:
    stem = Path(path).stem
    return f"[[{stem}]]" if basenames.get(stem, 0) == 1 else f"[[{path[:-3] if path.endswith('.md') else path}]]"


def plan(vault: Vault, store: Store) -> dict[str, dict[str, list[str]]]:
    """Desired tool-managed links per note: {path: {"references": [...paths], "similar": [...paths]}}."""
    notes = store.notes()
    paths = sorted(notes)
    by_id: dict[str, str] = {}
    by_title: list[tuple[str, str]] = []
    for p in paths:
        for i in notes[p]["ids"]:
            by_id.setdefault(i, p)
        for t in notes[p]["titles"]:
            nt = norm_title(t)
            if len(nt) >= 12:
                by_title.append((nt, p))

    def match(ref: dict) -> str | None:
        for i in ref["ids"]:
            if i in by_id:
                return by_id[i]
        nt = norm_title(ref["title"])
        if len(nt) < 12:
            return None
        for cand, p in by_title:
            # Exact, or one title truncated inside the other (vault titles are often cut short).
            if cand == nt or (len(cand) >= 20 and nt.startswith(cand)) or (len(nt) >= 20 and cand.startswith(nt)):
                return p
        return None

    result: dict[str, dict[str, list[str]]] = {p: {"references": [], "similar": []} for p in paths}
    linked: set[tuple[str, str]] = set()
    for p in paths:
        cited = []
        for ref in notes[p]["refs"]:
            target = match(ref)
            if target and target != p and target not in cited:
                cited.append(target)
                linked.add((p, target))
                linked.add((target, p))
        result[p]["references"] = cited

    k = int(vault.config["similar_top_k"])
    if k <= 0 or len(paths) < 2:
        return result
    if vault.config["backend"] == "fastembed":
        vectors = store.vectors(vault.config["model"])
        usable = [p for p in paths if p in vectors]
        if not usable:
            return result
        mat = np.stack([vectors[p][1] for p in usable])
    else:
        usable = paths
        mat = tfidf_matrix([notes[p]["embed_text"] or notes[p]["title"] for p in usable])
    sims = mat @ mat.T
    np.fill_diagonal(sims, -1)
    # Absolute cosine levels differ per model and per collection (one research topic scores high
    # everywhere), so by default only the closest pairs of this collection qualify.
    setting = vault.config.get("similar_min_score", "auto")
    if setting == "auto":
        pairs = sims[np.triu_indices(len(usable), 1)]
        threshold = float(np.percentile(pairs, float(vault.config.get("similar_percentile", 90))))
    else:
        threshold = float(setting)
    # Hubness correction (CSLS): notes that are close to everything are ranked down.
    neighbours = min(10, len(usable) - 1)
    local = np.sort(sims, axis=1)[:, -neighbours:].mean(axis=1)
    ranked = 2 * sims - local[:, None] - local[None, :]
    np.fill_diagonal(ranked, -np.inf)
    for row, p in enumerate(usable):
        order = np.argsort(-ranked[row])
        chosen = []
        for col in order:
            if sims[row, col] < threshold or len(chosen) >= k:
                break
            q = usable[col]
            if (p, q) in linked:
                continue
            chosen.append(q)
        result[p]["similar"] = chosen
    # Keep "similar" symmetric-light: a pair appears once, on the note listed first alphabetically,
    # so K-Plex does not show the same friendship twice.
    for p in paths:
        result[p]["similar"] = [q for q in result[p]["similar"] if not (q < p and p in result[q]["similar"])]
    return result


# --------------------------------------------------------------------------------------------
# Writing frontmatter (round-trip YAML; only tool-managed links change)


def read_strict(path: Path) -> str | None:
    """Text for rewriting. Files that are not valid UTF-8 are never rewritten (no lossy round-trip)."""
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        return None


def managed_path(vault: Vault) -> Path:
    return vault.state / "managed.json"


def load_managed(vault: Vault) -> dict:
    path = managed_path(vault)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def as_list(value) -> list:
    if value is None or value == "":
        return []
    return list(value) if isinstance(value, list) else [value]


def rewrite(text: str, updates: dict[str, tuple[list[str], list[str]]], topic: tuple[str, str | None] | None,
            front: frozenset[str] = frozenset(), scalars: dict[str, tuple[str | None, str | None]] | None = None) -> str | None:
    """updates: field -> (values to remove because this tool added them earlier, values to add).
    Fields named in `front` get their added values inserted first (used for display aliases)."""
    raw, body = split_frontmatter(text)
    yaml = yaml_rt()
    data = yaml.load(raw) if raw else None
    if data is None:
        from ruamel.yaml.comments import CommentedMap
        data = CommentedMap()
    changed = False
    for fieldname, (remove, add) in updates.items():
        key = next((k for k in data if str(k).lower() == fieldname.lower()), fieldname)
        current = as_list(data.get(key))
        kept = [v for v in current if str(v) not in remove]
        fresh = [v for v in add if v not in [str(x) for x in kept]]
        final = fresh + kept if fieldname in front else kept + fresh
        if [str(v) for v in final] != [str(v) for v in current]:
            changed = True
            if final:
                data[key] = final
            elif key in data:
                del data[key]
    for fieldname, (previous, value) in (scalars or {}).items():
        # Only fill an empty field or replace the value this tool wrote last time.
        key = next((k for k in data if str(k).lower() == fieldname.lower()), fieldname)
        current = data.get(key)
        if current not in (None, "") and str(current) != (previous or ""):
            continue
        if value and current != value:
            data[key] = value
            changed = True
        elif not value and key in data and previous is not None and str(current) == previous:
            del data[key]
            changed = True
    if topic:
        fieldname, value = topic
        key = next((k for k in data if str(k).lower() == fieldname.lower()), fieldname)
        if value and data.get(key) != value:
            data[key] = value
            changed = True
    if not changed:
        return None
    stream = io.StringIO()
    yaml.dump(data, stream)
    return f"---\n{stream.getvalue()}---\n{body if raw is not None else text}"


def apply_plan(vault: Vault, store: Store, desired: dict, write: bool, log, aliases: dict[str, str] | None = None,
               abstracts: dict[str, str] | None = None) -> dict:
    notes = store.notes()
    basenames: dict[str, int] = {}
    for p in notes:
        basenames[Path(p).stem] = basenames.get(Path(p).stem, 0) + 1
    managed = load_managed(vault)
    managed_before = json.loads(json.dumps(managed))
    fields = {"references": vault.config["references_field"], "similar": vault.config["similar_field"]}
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = vault.state / "backups" / f"{stamp}.jsonl"
    report = {"files": 0, "references_added": 0, "similar_added": 0, "aliases_added": 0, "abstracts_added": 0, "links_removed": 0, "changes": []}
    abstracts = abstracts or {}
    abstract_field = vault.config.get("abstract_field", "abstract_zh")
    aliases = aliases or {}
    alias_field = vault.config.get("alias_field", "aliases")
    for p, want in sorted(desired.items()):
        previous = managed.get(p, {})
        updates = {}
        added_now = {}
        for kind, fieldname in fields.items():
            links = [link_target(q, basenames) for q in want[kind]]
            old = previous.get(kind, [])
            remove = [l for l in old if l not in links]
            add = [l for l in links if l not in old]
            added_now[kind] = links
            if remove or add:
                updates[fieldname] = (old, links)  # drop all of our old links, re-add the current set
                report[f"{kind}_added"] += len(add)
                report["links_removed"] += len(remove)
        want_alias = [aliases[p]] if p in aliases else []
        old_alias = previous.get("alias", [])
        added_now["alias"] = want_alias
        if want_alias != old_alias:
            updates[alias_field] = (old_alias, want_alias)
            report["aliases_added"] += len([a for a in want_alias if a not in old_alias])
        scalars = {}
        want_abstract = abstracts.get(p)
        old_abstract = previous.get("abstract")
        if want_abstract != old_abstract:
            scalars[abstract_field] = (old_abstract, want_abstract)
        if not updates and not scalars:
            continue
        path = vault.root / p
        text = read_strict(path)
        if text is None:
            log(f"skipped (not valid UTF-8, left untouched): {p}")
            continue
        new_text = rewrite(text, updates, None, frozenset({alias_field}), scalars)
        if scalars:
            # Remember what we own only if the field was actually ours to write (empty or ours before).
            raw, _ = split_frontmatter(text)
            existing = load_frontmatter(raw)
            current = next((v for k, v in existing.items() if str(k).lower() == abstract_field.lower()), None)
            if current in (None, "") or str(current) == (old_abstract or ""):
                added_now["abstract"] = want_abstract
                if want_abstract and want_abstract != old_abstract:
                    report["abstracts_added"] += 1
            else:
                added_now["abstract"] = old_abstract
        elif "abstract" in previous:
            added_now["abstract"] = previous["abstract"]
        managed[p] = added_now
        if new_text is None:
            continue
        report["files"] += 1
        report["changes"].append({"path": p, "alias": want_alias, **{k: want[k] for k in fields}})
        if write:
            backup_file.parent.mkdir(exist_ok=True)
            fresh = not backup_file.exists()
            with backup_file.open("a", encoding="utf-8") as fh:
                if fresh:  # first line: which links this tool owned before this run
                    fh.write(json.dumps({"managed": managed_before}, ensure_ascii=False) + "\n")
                fh.write(json.dumps({"path": p, "text": text}, ensure_ascii=False) + "\n")
            path.write_text(new_text, encoding="utf-8")
    if write:
        managed_path(vault).write_text(json.dumps(managed, ensure_ascii=False, indent=1), encoding="utf-8")
        if report["files"]:
            log(f"backup: {backup_file.relative_to(vault.root)}")
    return report


def write_report(vault: Vault, store: Store, stats: dict, report: dict, applied: bool) -> Path:
    notes = store.notes()
    lines = [f"# K-Plex organize report — {_dt.datetime.now():%Y-%m-%d %H:%M}", "",
             f"- notes indexed: {stats['notes']} (new {stats['new']}, changed {stats['changed']}, removed {stats['removed']}, embedded {stats['embedded']})",
             f"- notes with a parsed reference list: {stats['with_refs']}",
             f"- files {'updated' if applied else 'that would change'}: {report['files']}",
             f"- citation links added: {report['references_added']}, similar links added: {report['similar_added']}, translated aliases added: {report['aliases_added']}, translated abstracts added: {report['abstracts_added']}, tool values removed: {report['links_removed']}",
             f"- mode: {'APPLIED' if applied else 'DRY RUN (use --apply to write)'}", ""]
    for change in report["changes"][:400]:
        lines.append(f"## {notes[change['path']]['title']}  \n`{change['path']}`")
        if change.get("alias"):
            lines.append(f"- alias: {change['alias'][0]}")
        for kind, label in (("references", "cites"), ("similar", "similar")):
            if change[kind]:
                lines.append(f"- {label}: " + "; ".join(notes[q]["title"][:80] for q in change[kind]))
        lines.append("")
    out = vault.state / "report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# --------------------------------------------------------------------------------------------
# Topics (clusters named by a person or an agent)


def kmeans(mat: np.ndarray, k: int, iters: int = 50, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    centers = mat[rng.choice(len(mat), size=k, replace=False)]
    labels = np.full(len(mat), -1, dtype=int)
    for _ in range(iters):
        labels_new = np.argmax(mat @ centers.T, axis=1)
        if np.array_equal(labels_new, labels):
            break
        labels = labels_new
        for j in range(k):
            members = mat[labels == j]
            if len(members):
                c = members.mean(axis=0)
                centers[j] = c / max(np.linalg.norm(c), 1e-12)
    return labels


def topics_export(vault: Vault, store: Store, out: Path, k: int | None) -> None:
    notes = store.notes()
    paths = sorted(notes)
    if vault.config["backend"] == "fastembed":
        vectors = store.vectors(vault.config["model"])
        paths = [p for p in paths if p in vectors]
        mat = np.stack([vectors[p][1] for p in paths])
    else:
        mat = tfidf_matrix([notes[p]["embed_text"] for p in paths])
    k = k or max(2, min(24, round(math.sqrt(len(paths) / 2))))
    labels = kmeans(mat, k)
    clusters = []
    for j in range(k):
        members = [paths[i] for i in np.where(labels == j)[0]]
        if members:
            clusters.append({"cluster": j, "topic": "", "size": len(members),
                             "titles": [notes[p]["title"][:120] for p in members[:15]], "paths": members})
    out.write_text(json.dumps({"field": vault.config["topic_field"], "clusters": clusters}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(clusters)} clusters to {out}. Fill each \"topic\", then run: topics apply {out}")


def topics_apply(vault: Vault, source: Path, write: bool) -> None:
    data = json.loads(source.read_text(encoding="utf-8"))
    fieldname = data.get("field") or vault.config["topic_field"]
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_file = vault.state / "backups" / f"{stamp}-topics.jsonl"
    count = 0
    for cluster in data["clusters"]:
        topic = (cluster.get("topic") or "").strip()
        if not topic:
            continue
        for p in cluster["paths"]:
            path = vault.root / p
            if not path.exists():
                continue
            text = read_strict(path)
            if text is None:
                continue
            new_text = rewrite(text, {}, (fieldname, topic))
            if new_text is None:
                continue
            count += 1
            if write:
                backup_file.parent.mkdir(exist_ok=True)
                with backup_file.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"path": p, "text": text}, ensure_ascii=False) + "\n")
                path.write_text(new_text, encoding="utf-8")
    print(f"{'updated' if write else 'would update'} {count} note(s) with `{fieldname}`" + ("" if write else " (use --apply)"))


# --------------------------------------------------------------------------------------------
# CLI


def run(args) -> None:
    root = Path(args.vault).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"not a folder: {root}")
    (root / STATE_DIR).mkdir(exist_ok=True)
    config_path = root / STATE_DIR / "config.json"
    log = lambda m: print(m, file=sys.stderr)

    if args.command == "init":
        config = load_config(root)
        if args.dir is not None:
            config["notes_dir"] = args.dir
        if args.backend:
            config["backend"] = args.backend
        if args.model:
            config["model"] = args.model
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        gitignore = root / STATE_DIR / ".gitignore"
        gitignore.write_text("index.sqlite\nbackups/\n", encoding="utf-8")
    elif not config_path.exists():
        sys.exit("no .kplex/config.json — run `init` first")

    vault = Vault(root, load_config(root))
    store = Store(root)

    if args.command == "status":
        notes = store.notes()
        vecs = store.vectors(vault.config["model"])
        print(json.dumps({"notes": len(notes), "vectors": len(vecs), "with_refs": sum(1 for n in notes.values() if n["refs"]),
                          "with_ids": sum(1 for n in notes.values() if n["ids"]), "config": vault.config}, ensure_ascii=False, indent=2))
        return
    if args.command == "restore":
        backups = sorted((vault.state / "backups").glob("*.jsonl"))
        target = Path(args.backup) if args.backup else (backups[-1] if backups else None)
        if not target or not target.exists():
            sys.exit("no backup found")
        restored = 0
        for line in target.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            if "managed" in item:
                managed_path(vault).write_text(json.dumps(item["managed"], ensure_ascii=False, indent=1), encoding="utf-8")
                continue
            (root / item["path"]).write_text(item["text"], encoding="utf-8")
            restored += 1
        print(f"restored {restored} file(s) from {target.name}")
        return

    stats = index(vault, store, log)
    if args.command == "topics":
        if args.action == "export":
            topics_export(vault, store, Path(args.file or root / STATE_DIR / "topics.json"), args.k)
        else:
            topics_apply(vault, Path(args.file or root / STATE_DIR / "topics.json"), args.apply)
        return

    desired = plan(vault, store)
    aliases = title_aliases(vault, store, log)
    abstracts = abstract_translations(vault, store, log)
    report = apply_plan(vault, store, desired, args.apply, log, aliases, abstracts)
    out = write_report(vault, store, stats, report, args.apply)
    print(json.dumps({**stats, **{k: v for k, v in report.items() if k != "changes"}, "report": str(out.relative_to(root)),
                      "applied": bool(args.apply)}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init")
    p.add_argument("vault")
    p.add_argument("--dir", help="notes folder relative to the vault (default: whole vault)")
    p.add_argument("--backend", choices=["fastembed", "tfidf"])
    p.add_argument("--model")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("update")
    p.add_argument("vault")
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("status")
    p.add_argument("vault")
    p = sub.add_parser("topics")
    p.add_argument("vault")
    p.add_argument("action", choices=["export", "apply"])
    p.add_argument("file", nargs="?")
    p.add_argument("--k", type=int)
    p.add_argument("--apply", action="store_true")
    p = sub.add_parser("restore")
    p.add_argument("vault")
    p.add_argument("--backup")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
