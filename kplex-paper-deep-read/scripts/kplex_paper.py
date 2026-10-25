#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pymupdf>=1.24",
# ]
# ///
"""
kplex_paper — turn one PDF paper into a self-contained K-Plex paper folder.

  <vault>/<root>/<Stem>/
    <Stem>.md                 deep-reading note (written by the agent; `extract` seeds its frontmatter)
    <Stem>.pdf                copy of the source PDF
    images/fig-1.png …        figures and tables cropped from the PDF
    References/<Card>.md      one paper card per cited work (frontmatter + abstract + figure)
    References/images/…       figures of cited papers (from arXiv HTML, when available)
    .work/                    manifest.json, text.md, outline.md, pages/, equations/, refs.json
                              (a dot-folder: Obsidian ignores it)

Commands:
  extract <pdf> --vault V [--root Papers/DeepRead] [--dpi 220]   metadata, text, pages, figure/table/equation crops
  crop    <dir> --page N --rect x0,y0,x1,y1 --name fig-3         re-crop one image (points, top-left origin)
  refs    <dir> [--lang zh-CN|none] [--card-figures 1] [--no-reuse] [--refresh]
                                                                 resolve citations, write paper cards
  check   <dir> [--fix]                                          verify the note; --fix merges References links
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import pymupdf

WORK = ".work"
PAGE_DPI = 144  # page renders: 1 pixel = 0.5 PDF point, so points = pixels / 2
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
S2 = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "title,authors,year,venue,externalIds,abstract,tldr,citationCount,url,openAccessPdf"
S2_REF_FIELDS = "title,authors,year,venue,externalIds,abstract,citationCount,url,openAccessPdf"  # no tldr on /references
MAX_AUTHORS = 12
UNSAFE = re.compile(r'[\\/:*?"<>|#^\[\]{}]')

ARXIV_IN_TEXT = re.compile(r"arxiv[:\s/,]*(?:abs/)?(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
DOI_IN_TEXT = re.compile(r"\b(10\.\d{4,9}/[^\s,;]+)")
YEAR = re.compile(r"\b(19[5-9]\d|20\d{2})[a-z]?\b")
CAPTION = re.compile(r"^(figure|fig\.?|table)\s*([0-9]+|[IVXLC]+)\s*[.:|]\s*", re.I)
CAPTION_IEEE_TABLE = re.compile(r"^TABLE\s+([IVXLC]+|\d+)\b\s*")
EQ_NUMBER = re.compile(r"^\((\d{1,3}[a-z]?)\)$")
REFERENCE_HEAD = re.compile(r"^\s*(?:\d+\.?\s*)?(?:references|bibliography|works cited|参考文献)\s*:?\s*$", re.I)
SECTION_END = re.compile(r"^\s*(?:(?:[A-Z]|\d+)[.:]?\s+)?(?:appendix|appendices|supplementary(?: material)?|checklist)\b", re.I)
NUMBERED_ENTRY = re.compile(r"^\s*(?:\[(\d{1,4})\]|(\d{1,4})\.\s)")
ENTRY_END = re.compile(r"\b(?:19|20)\d{2}[a-z]?\.\s*$")
HEADING_NUM = re.compile(r"^(?:(\d+(?:\.\d+)*)\.?|([IVX]+)\.|([A-H])\.)\s+[A-Z]")


def log(*parts) -> None:
    print(*parts, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------------------------
# HTTP helpers

_last_call: dict[str, float] = {}


def http(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 30, binary: bool = False):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, (body if binary else body.decode("utf-8", "replace")), resp.geturl()
    except urllib.error.HTTPError as err:
        return err.code, (b"" if binary else ""), url
    except Exception:
        return 0, (b"" if binary else ""), url


_throttle_lock = threading.Lock()


def throttle(key: str, gap: float) -> None:
    """Space calls to one service `gap` seconds apart, across threads."""
    with _throttle_lock:
        slot = max(time.time(), _last_call.get(key, 0) + gap)
        _last_call[key] = slot
    wait = slot - time.time()
    if wait > 0:
        time.sleep(wait)


_S2_FAILS = {"count": 0}


def s2(path: str, params: dict | None = None, payload: dict | None = None) -> dict | list | None:
    """Semantic Scholar call. After repeated rate-limit failures it gives up quickly so the
    OpenAlex/arXiv fallbacks take over instead of waiting minutes per request."""
    import os
    headers = {"x-api-key": os.environ["S2_API_KEY"]} if os.environ.get("S2_API_KEY") else {}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    url = f"{S2}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    attempts = 1 if _S2_FAILS["count"] >= 6 else 3
    for attempt in range(attempts):
        throttle("s2", 0.4 if "x-api-key" in headers else 1.1)
        status, body, _ = http(url, json.dumps(payload).encode() if payload is not None else None, headers)
        if status == 200:
            _S2_FAILS["count"] = 0
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return None
        if status in (429, 0, 500, 502, 503, 504):
            _S2_FAILS["count"] += 1
            if attempt + 1 < attempts:
                time.sleep(2 + 3 * attempt)
            continue
        if status == 400:
            log(f"Semantic Scholar rejected {path}: {body[:160]}")
        return None
    return None


def openalex(path: str, params: dict | None = None) -> dict | None:
    import os
    params = dict(params or {})
    if os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = os.environ["OPENALEX_API_KEY"]
    url = f"https://api.openalex.org{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    for attempt in range(3):
        throttle("openalex", 0.25)
        status, body, _ = http(url)
        if status == 200:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return None
        if status == 429 and attempt < 2:
            time.sleep(5 + 10 * attempt)
            continue
        return None
    return None


def openalex_record(work: dict) -> dict:
    inv = work.get("abstract_inverted_index") or {}
    words = sorted((pos, word) for word, positions in inv.items() for pos in positions)
    doi = (work.get("doi") or "").replace("https://doi.org/", "") or None
    arxiv = None
    for loc in work.get("locations") or []:
        m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", loc.get("landing_page_url") or "")
        if m:
            arxiv = m.group(1)
            break
    if doi and (m := re.match(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})", doi, re.I)):
        arxiv, doi = arxiv or m.group(1), None
    source = ((work.get("primary_location") or {}).get("source") or {}).get("display_name")
    return {
        "title": (work.get("display_name") or "").strip(),
        "authors": [a["author"]["display_name"] for a in work.get("authorships") or [] if (a.get("author") or {}).get("display_name")],
        "year": work.get("publication_year"),
        "venue": source,
        "doi": doi,
        "arxiv": arxiv,
        "abstract": " ".join(w for _, w in words),
        "tldr": "",
        "citations": work.get("cited_by_count"),
        "url": work.get("id"),
        "pdf_url": ((work.get("best_oa_location") or {}).get("pdf_url")) or None,
    }


def openalex_search(title: str) -> dict | None:
    data = openalex("/works", {"search": title[:250], "per_page": 3})
    best, score = None, 0.0
    for work in (data or {}).get("results") or []:
        sim = title_similarity(work.get("display_name") or "", title)
        if sim > score:
            best, score = work, sim
    return openalex_record(best) if best is not None and score >= 0.7 else None


def arxiv_api(ids: list[str]) -> dict[str, dict]:
    """Title/authors/abstract/year from the arXiv API, keyed by bare arXiv id."""
    out: dict[str, dict] = {}
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for i in range(0, len(ids), 40):
        chunk = ids[i:i + 40]
        throttle("arxiv", 3.0)
        status, body, _ = http("http://export.arxiv.org/api/query?" + urllib.parse.urlencode({"id_list": ",".join(chunk), "max_results": len(chunk)}))
        if status != 200:
            continue
        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            continue
        for entry in root.findall("a:entry", ns):
            eid = (entry.findtext("a:id", "", ns) or "").rsplit("/", 1)[-1]
            bare = re.sub(r"v\d+$", "", eid)
            if not bare:
                continue
            out[bare] = {
                "title": re.sub(r"\s+", " ", entry.findtext("a:title", "", ns)).strip(),
                "abstract": re.sub(r"\s+", " ", entry.findtext("a:summary", "", ns)).strip(),
                "authors": [re.sub(r"\s+", " ", a.findtext("a:name", "", ns)).strip() for a in entry.findall("a:author", ns)],
                "year": int((entry.findtext("a:published", "", ns) or "0")[:4] or 0) or None,
            }
    return out


def openalex_abstract(doi: str) -> str:
    throttle("openalex", 0.2)
    status, body, _ = http(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}")
    if status != 200:
        return ""
    try:
        inv = json.loads(body).get("abstract_inverted_index") or {}
    except json.JSONDecodeError:
        return ""
    words = sorted((pos, word) for word, positions in inv.items() for pos in positions)
    return " ".join(word for _, word in words)


# ---------------------------------------------------------------------------------------------
# Translation (Google, falling back to Bing) — only titles and abstracts are sent

def translate_google(text: str, target: str) -> str:
    url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&dt=t&tl=" + urllib.parse.quote(target)
    status, body, _ = http(url, urllib.parse.urlencode({"q": text}).encode(), {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    if status != 200:
        raise RuntimeError(f"Google Translate HTTP {status}")
    return "".join(seg[0] for seg in json.loads(body)[0] if seg and seg[0])


_BING: dict = {}


def translate_bing(text: str, target: str) -> str:
    to = {"zh-CN": "zh-Hans", "zh-TW": "zh-Hant"}.get(target, target)
    for host in ([_BING["host"]] if _BING.get("host") else []) + ["www.bing.com", "cn.bing.com"]:
        status, page, _ = http(f"https://{host}/translator")
        ig = re.search(r'IG:"([0-9A-Fa-f]+)"', page)
        iid = re.search(r'data-iid="(translator\.[^"]+)"', page)
        params = re.search(r'params_AbusePreventionHelper\s*=\s*\[\s*(\d+)\s*,\s*"([^"]+)"', page)
        if status != 200 or not ig or not params:
            continue
        form = urllib.parse.urlencode({"fromLang": "auto-detect", "to": to, "text": text, "key": params.group(1), "token": params.group(2)}).encode()
        url = f"https://{host}/ttranslatev3?isVertical=1&IG={ig.group(1)}&IID={(iid.group(1) if iid else 'translator.5023')}.1"
        status, body, _ = http(url, form, {"Content-Type": "application/x-www-form-urlencoded", "Referer": f"https://{host}/translator"})
        if status == 200 and body.strip().startswith("["):
            _BING["host"] = host
            return json.loads(body)[0]["translations"][0]["text"]
    raise RuntimeError("Bing Translator unavailable")


_TRANSLATIONS: dict[str, str] = {}


def translate(text: str, target: str) -> str | None:
    text = text.strip()
    if not text:
        return None
    key = f"{target}\u0000{text}"
    if key in _TRANSLATIONS:
        return _TRANSLATIONS[key]
    done = _translate(text, target)
    if done:
        _TRANSLATIONS[key] = done
    return done


def _translate(text: str, target: str) -> str | None:
    chunks, cur = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", text):
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
        for fn in (translate_google, translate_bing):
            try:
                throttle("translate", 0.3)
                done = fn(chunk, target).strip()
                break
            except Exception:
                continue
        if not done:
            return None
        out.append(done)
    return ("" if target.startswith(("zh", "ja")) else " ").join(out)


# ---------------------------------------------------------------------------------------------
# Naming / frontmatter

def last_name(author: str) -> str:
    parts = author.strip().split()
    return parts[-1] if parts else ""


def paper_stem(title: str, authors: list[str], year) -> str:
    prefix = " ".join(p for p in [last_name(authors[0]) if authors else "", str(year) if year else ""] if p)
    raw = f"{prefix} - {title}" if prefix else title
    stem = re.sub(r"\s+", " ", UNSAFE.sub(" ", re.sub(r"\s+", " ", raw))).strip().lstrip(".")
    if len(stem) > 90:
        cut = stem[:90]
        space = cut.rfind(" ")
        stem = (cut[:space] if space > 45 else cut).strip()
    return stem or "Untitled paper"


def unique_path(folder: Path, stem: str, suffix: str = ".md") -> Path:
    path = folder / f"{stem}{suffix}"
    n = 2
    while path.exists():
        path = folder / f"{stem} ({n}){suffix}"
        n += 1
    return path


def yaml_scalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def frontmatter(props: dict) -> str:
    lines = ["---"]
    for key, value in props.items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines += [f"  - {yaml_scalar(item)}" for item in value]
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def paper_props(meta: dict, note_type: str = "Paper") -> dict:
    authors = meta.get("authors") or []
    if len(authors) > MAX_AUTHORS:
        authors = authors[:MAX_AUTHORS] + ["et al."]
    arxiv, doi = meta.get("arxiv"), meta.get("doi")
    url = f"https://arxiv.org/abs/{arxiv}" if arxiv else (f"https://doi.org/{doi}" if doi else meta.get("url"))
    aliases = [a for a in [meta.get("title_translated"), meta.get("title")] if a]
    return {
        "title": meta.get("title"),
        "aliases": aliases,
        "authors": authors,
        "year": meta.get("year"),
        "venue": meta.get("venue"),
        "doi": doi,
        "arxiv": arxiv,
        "url": url,
        "pdf": meta.get("pdf_url") or (f"https://arxiv.org/pdf/{arxiv}" if arxiv else None),
        "citations": meta.get("citations"),
        "Note type": note_type,
        "abstract_zh": meta.get("abstract_translated"),
    }


def norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9一-鿿]+", " ", (title or "").lower()).strip()


def title_similarity(a: str, b: str) -> float:
    ta, tb = set(norm_title(a).split()), set(norm_title(b).split())
    if not ta or not tb:
        return 0.0
    na, nb = norm_title(a), norm_title(b)
    if len(na) >= 20 and len(nb) >= 20 and (na.startswith(nb) or nb.startswith(na)):
        return 0.95
    return len(ta & tb) / len(ta | tb)


def s2_record(paper: dict) -> dict:
    ext = paper.get("externalIds") or {}
    return {
        "title": (paper.get("title") or "").strip(),
        "authors": [a.get("name", "") for a in (paper.get("authors") or []) if a.get("name")],
        "year": paper.get("year"),
        "venue": paper.get("venue") or None,
        "doi": ext.get("DOI"),
        "arxiv": ext.get("ArXiv"),
        "abstract": (paper.get("abstract") or "").strip(),
        "tldr": ((paper.get("tldr") or {}).get("text") or "").strip(),
        "citations": paper.get("citationCount"),
        "url": paper.get("url"),
        "pdf_url": ((paper.get("openAccessPdf") or {}).get("url") or None),
        "s2": paper.get("paperId"),
    }


# ---------------------------------------------------------------------------------------------
# PDF analysis

def block_text(block: dict) -> str:
    out = ""
    for line in block.get("lines", []):
        dx, dy = line.get("dir", (1, 0))
        if abs(dx) < 0.9:  # rotated text: arXiv side stamp, axis labels
            continue
        text = "".join(span["text"] for span in line["spans"]).strip()
        if not text:
            continue
        if not out:
            out = text
        elif re.search(r"[A-Za-z]-$", out) and re.match(r"^[a-z]", text):
            out = out[:-1] + text
        else:
            out += " " + text
    return re.sub(r"\s+", " ", out).strip()


def block_size(block: dict) -> float:
    sizes = Counter()
    for line in block.get("lines", []):
        for span in line["spans"]:
            sizes[round(span["size"], 1)] += len(span["text"].strip())
    return sizes.most_common(1)[0][0] if sizes else 0.0


def block_bold(block: dict) -> bool:
    spans = [s for l in block.get("lines", []) for s in l["spans"] if s["text"].strip()]
    return bool(spans) and all((s["flags"] & 16) or "bold" in s["font"].lower() for s in spans)


class Page:
    def __init__(self, page: pymupdf.Page):
        self.page = page
        self.number = page.number + 1
        self.rect = page.rect
        self.W, self.H = page.rect.width, page.rect.height
        data = page.get_text("dict")
        self.blocks = []
        for b in data["blocks"]:
            if b["type"] != 0:
                continue
            text = block_text(b)
            if not text:
                continue
            x0, y0, x1, y1 = b["bbox"]
            self.blocks.append({"bbox": pymupdf.Rect(x0, y0, x1, y1), "text": text, "size": block_size(b),
                                "bold": block_bold(b), "raw": b})
        narrow = [b for b in self.blocks if len(b["text"]) > 150 and b["bbox"].width < self.W * 0.55]
        wide = [b for b in self.blocks if len(b["text"]) > 150 and b["bbox"].width >= self.W * 0.6]
        self.two_col = len(narrow) >= 2 and len(narrow) >= len(wide)

    def is_full(self, rect: pymupdf.Rect) -> bool:
        return not self.two_col or rect.width > self.W * 0.6 or (rect.x0 < self.W * 0.4 and rect.x1 > self.W * 0.6)

    def column(self, rect: pymupdf.Rect) -> tuple[float, float]:
        if self.is_full(rect):
            return (0.0, self.W)
        return (0.0, self.W / 2) if (rect.x0 + rect.x1) / 2 < self.W / 2 else (self.W / 2, self.W)

    def ordered(self) -> list[dict]:
        blocks = [b for b in self.blocks if not self.noise(b)]
        if not self.two_col:
            return sorted(blocks, key=lambda b: (b["bbox"].y0, b["bbox"].x0))
        fulls = sorted([b for b in blocks if self.is_full(b["bbox"])], key=lambda b: b["bbox"].y0)
        rest = [b for b in blocks if not self.is_full(b["bbox"])]
        out, prev = [], -1e9
        for cut in fulls + [None]:
            limit = cut["bbox"].y0 if cut else 1e9
            seg = [b for b in rest if prev <= (b["bbox"].y0 + b["bbox"].y1) / 2 < limit]
            out += sorted([b for b in seg if (b["bbox"].x0 + b["bbox"].x1) / 2 < self.W / 2], key=lambda b: b["bbox"].y0)
            out += sorted([b for b in seg if (b["bbox"].x0 + b["bbox"].x1) / 2 >= self.W / 2], key=lambda b: b["bbox"].y0)
            if cut:
                out.append(cut)
                prev = limit
        return out

    def noise(self, block: dict) -> bool:
        r = block["bbox"]
        short = len(block["text"]) < 60
        return short and (r.y1 < self.H * 0.06 or r.y0 > self.H * 0.94 or r.x0 > self.W or r.x1 < 0)

    def graphics(self) -> list[pymupdf.Rect]:
        rects = []
        page_area = self.W * self.H
        for info in self.page.get_image_info():
            r = pymupdf.Rect(info["bbox"]) & self.rect
            if not r.is_empty and r.width > 4 and r.height > 4:
                rects.append(r)
        for d in self.page.get_drawings():
            r = pymupdf.Rect(d["rect"]) & self.rect
            if r.is_empty or r.get_area() > page_area * 0.8:
                continue
            if r.width > 1.5 or r.height > 1.5:
                rects.append(r)
        return rects


def union(rects: list[pymupdf.Rect]) -> pymupdf.Rect | None:
    if not rects:
        return None
    out = pymupdf.Rect(rects[0])
    for r in rects[1:]:
        out |= r
    return out


def is_prose(page: Page, block: dict) -> bool:
    """Running text (not a caption, table cells, or chart labels)."""
    text = block["text"]
    if len(text) <= 160 or CAPTION.match(text) or CAPTION_IEEE_TABLE.match(text):
        return False
    letters = sum(c.isalpha() for c in text)
    digits = sum(c.isdigit() for c in text)
    words = re.findall(r"[A-Za-z]{3,}", text)
    return letters > 0.6 * len(text) and digits < 0.12 * len(text) and len(words) > 20


def caption_label(text: str) -> tuple[str, str] | None:
    m = CAPTION.match(text)
    if m:
        kind = "table" if m.group(1).lower().startswith("tab") else "figure"
        return kind, m.group(2)
    m = CAPTION_IEEE_TABLE.match(text)
    if m:
        return "table", m.group(1)
    return None


def region_near(page: Page, cap: dict, graphics: list[pymupdf.Rect], above: bool, skip: set[int]) -> tuple[pymupdf.Rect | None, int]:
    """Figure/table region above (or below) a caption within its column, bounded by prose."""
    cx0, cx1 = page.column(cap["bbox"])
    capr = cap["bbox"]
    in_col = lambda r: r.x1 > cx0 + 2 and r.x0 < cx1 - 2  # noqa: E731
    others = [b for b in page.blocks if id(b) not in skip and in_col(b["bbox"])]
    if above:
        stops = [b["bbox"].y1 for b in others if b["bbox"].y1 <= capr.y0 + 1 and (is_prose(page, b) or caption_label(b["text"]))]
        limit = max(stops + [page.H * 0.05])
        members = [r for r in graphics if in_col(r) and r.y1 <= capr.y0 + 2 and r.y0 >= limit - 2]
        members += [b["bbox"] for b in others if b["bbox"].y0 >= limit - 1 and b["bbox"].y1 <= capr.y0 + 1 and not is_prose(page, b)]
        fallback = pymupdf.Rect(cx0 + 20, limit, cx1 - 20, capr.y0)
    else:
        stops = [b["bbox"].y0 for b in others if b["bbox"].y0 >= capr.y1 - 1 and (is_prose(page, b) or caption_label(b["text"]))]
        limit = min(stops + [page.H * 0.95])
        members = [r for r in graphics if in_col(r) and r.y0 >= capr.y1 - 2 and r.y1 <= limit + 2]
        members += [b["bbox"] for b in others if b["bbox"].y0 >= capr.y1 - 1 and b["bbox"].y1 <= limit + 1 and not is_prose(page, b)]
        fallback = pymupdf.Rect(cx0 + 20, capr.y1, cx1 - 20, limit)
    region = union(members)
    if region is None:
        return (fallback if fallback.height > 30 else None), 0
    region = pymupdf.Rect(max(region.x0, cx0) - 3, region.y0 - 3, min(region.x1, cx1) + 3, region.y1 + 3) & page.rect
    return region, len(members)


def pdfpp_rect(page: Page, r: pymupdf.Rect) -> str:
    """PDF++ `rect=` subpath uses PDF user space (origin bottom-left)."""
    vals = [r.x0, page.H - r.y1, r.x1, page.H - r.y0]
    return ",".join(f"{v:.2f}".rstrip("0").rstrip(".") for v in vals)


def save_crop(page: Page, rect: pymupdf.Rect, path: Path, dpi: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    page.page.get_pixmap(clip=rect, dpi=dpi).save(str(path))


def split_reference_entries(lines: list[str]) -> list[tuple[int | None, str]]:
    def join(parts: list[str]) -> str:
        out = ""
        for raw in parts:
            line = raw.strip()
            if not line:
                continue
            if not out:
                out = line
            elif re.search(r"[A-Za-z]-$", out) and re.match(r"^[a-z]", line):
                out = out[:-1] + line
            else:
                out += " " + line
        return out

    entries: list[tuple[int | None, str]] = []
    if sum(1 for l in lines if NUMBERED_ENTRY.match(l)) >= 3:
        num, cur = None, []
        for line in lines:
            m = NUMBERED_ENTRY.match(line)
            if m:
                if cur:
                    entries.append((num, join(cur)))
                num = int(m.group(1) or m.group(2))
                cur = [line[m.end():]]
            elif cur:
                cur.append(line)
        if cur:
            entries.append((num, join(cur)))
    else:
        cur = []
        for line in lines:
            if not line.strip():
                continue
            cur.append(line)
            if ENTRY_END.search(line.strip()):
                entries.append((None, join(cur)))
                cur = []
        if cur:
            entries.append((None, join(cur)))
    return [(n, e) for n, e in entries if len(e) >= 20][:600]


def parse_reference(text: str) -> dict:
    text = re.sub(r"\s+", " ", text).strip()
    out: dict = {"raw": text, "title": "", "arxiv": None, "doi": None, "year": None}
    m = ARXIV_IN_TEXT.search(text)
    if m:
        out["arxiv"] = m.group(1)
    m = DOI_IN_TEXT.search(text)
    if m:
        doi = m.group(1).rstrip(".,;:)]}")
        arx = re.match(r"10\.48550/arxiv\.(\d{4}\.\d{4,5})", doi, re.I)
        if arx:
            out["arxiv"] = out["arxiv"] or arx.group(1)
        else:
            out["doi"] = doi
    years = YEAR.findall(text)
    out["year"] = int(years[-1]) if years else None
    quoted = re.search(r"[“\"]([^”\"]{8,300}?)[,.]?[”\"]", text)
    if quoted:
        out["title"] = quoted.group(1).strip().rstrip(",.")
        return out
    # "Authors. Title. Venue, year." / "Authors. Title. In Proc…"
    parts = [p.strip() for p in re.split(r"(?<![A-Z])\.\s+(?=[A-Z0-9])", text) if p.strip()]
    if len(parts) >= 2:
        candidate = parts[1]
        if re.match(r"^(?:in|arxiv|proceedings|advances|ieee|journal)\b", candidate, re.I) and len(parts) >= 1:
            candidate = parts[0]
        out["title"] = candidate.rstrip(",.")
    return out


def guess_title(doc: pymupdf.Document) -> str:
    meta = (doc.metadata or {}).get("title") or ""
    if len(meta) > 10 and not re.search(r"\.(pdf|dvi|tex)$|^untitled|^microsoft", meta, re.I):
        return meta.strip()
    page = Page(doc[0])
    top = [b for b in page.blocks if b["bbox"].y1 < page.H * 0.45 and len(b["text"]) > 8]
    if not top:
        return ""
    best = max(b["size"] for b in top)
    return " ".join(b["text"] for b in top if abs(b["size"] - best) < 0.6)


def lookup_paper(title: str, arxiv: str | None, doi: str | None) -> dict | None:
    for pid in ([f"ARXIV:{arxiv}"] if arxiv else []) + ([f"DOI:{doi}"] if doi else []):
        data = s2(f"/paper/{urllib.parse.quote(pid, safe=':')}", {"fields": S2_FIELDS})
        if data and data.get("paperId"):
            return data
    if title and _S2_FAILS["count"] < 6:
        data = s2("/paper/search/match", {"query": title[:300], "fields": S2_FIELDS})
        if data and data.get("data"):
            hit = data["data"][0]
            if title_similarity(hit.get("title", ""), title) >= 0.7:
                return hit
    return None


def lookup_record(title: str, arxiv: str | None, doi: str | None) -> dict | None:
    """Resolve one reference: identifiers via S2, then title search via OpenAlex, then S2."""
    for pid in ([f"ARXIV:{arxiv}"] if arxiv else []) + ([f"DOI:{doi}"] if doi else []):
        data = s2(f"/paper/{urllib.parse.quote(pid, safe=':')}", {"fields": S2_FIELDS})
        if isinstance(data, dict) and data.get("paperId"):
            return s2_record(data)
    if doi:
        work = openalex(f"/works/doi:{urllib.parse.quote(doi)}")
        if work and work.get("id"):
            return openalex_record(work)
    if title:
        rec = openalex_search(title)
        if rec:
            return rec
        if _S2_FAILS["count"] < 6:
            data = s2("/paper/search/match", {"query": title[:300], "fields": S2_FIELDS})
            if isinstance(data, dict) and data.get("data"):
                hit = data["data"][0]
                if title_similarity(hit.get("title", ""), title) >= 0.7:
                    return s2_record(hit)
    return None


# ---------------------------------------------------------------------------------------------
# Commands

def load_manifest(folder: Path) -> dict:
    path = folder / WORK / "manifest.json"
    if not path.exists():
        sys.exit(f"no manifest at {path}; run `extract` first")
    return json.loads(path.read_text("utf-8"))


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def line_text(line: dict) -> str:
    return re.sub(r"\s+", " ", "".join(s["text"] for s in line["spans"])).strip()


def unsmallcap(text: str) -> str:
    """`I NTRODUCTION` / `R EFERENCES` (small caps split into two runs) -> `INTRODUCTION`."""
    return re.sub(r"\b([A-Z]) (?=[A-Z]{2,}\b)", r"\1", text)


def split_heading(block: dict, body: float) -> tuple[int, str, str] | None:
    """(level, heading, remaining block text) when the block starts with a section heading."""
    lines = [l for l in block["raw"]["lines"] if abs(l.get("dir", (1, 0))[0]) >= 0.9 and line_text(l)]
    if not lines:
        return None
    first = lines[0]
    spans = [s for s in first["spans"] if s["text"].strip()]
    text = unsmallcap(line_text(first))
    text = re.sub(r"\s+[A-Z]$", "", text)  # a drop cap that shares the heading line
    if len(text) > 90 or len(text) < 3 or CAPTION.match(text) or CAPTION_IEEE_TABLE.match(text) or not re.search(r"[A-Za-z]{3,}", text):
        return None
    size = max(s["size"] for s in spans)
    bold = all((s["flags"] & 16) or "bold" in s["font"].lower() for s in spans)
    italic = all((s["flags"] & 2) or "ital" in s["font"].lower() for s in spans)
    emphasized = bold or size > body + 0.8
    level = None
    words = text.split()
    if re.match(r"^(?:abstract|references|bibliography|acknowledge?ments?|appendix)\b", text, re.I) and len(words) <= 3 and (emphasized or text.isupper()):
        level = 2
    elif m := re.match(r"^(\d+(?:\.\d+)*)\.?\s+[A-Z]", text):
        if emphasized and not text.endswith(".") and len(words) <= 12:
            level = 2 + m.group(1).count(".")
    elif re.match(r"^[IVX]+\.\s+[A-Z][A-Z\s\-&:,]+$", text):
        level = 2
    elif re.match(r"^[A-H]\.\s+[A-Z]", text) and (italic or bold) and len(words) <= 10:
        level = 3
    elif size >= body + 1.8 and not text.endswith(".") and len(words) <= 14:
        level = 2
    if not level:
        return None
    rest = " ".join(line_text(l) for l in lines[1:])
    return level, text, rest


def cmd_extract(args) -> None:
    pdf = Path(args.pdf).expanduser().resolve()
    vault = Path(args.vault).expanduser().resolve()
    if not pdf.exists():
        sys.exit(f"PDF not found: {pdf}")
    if not (vault / ".obsidian").exists():
        log(f"warning: {vault} has no .obsidian folder; is it the vault root?")
    doc = pymupdf.open(str(pdf))
    pages = [Page(p) for p in doc]

    head_text = " ".join(b["text"] for p in pages[:2] for b in p.blocks)
    side = " ".join(block_text(b) for b in doc[0].get_text("dict")["blocks"] if b["type"] == 0)
    arxiv_m = ARXIV_IN_TEXT.search(side) or ARXIV_IN_TEXT.search(head_text)
    doi_m = DOI_IN_TEXT.search(head_text)
    arxiv = args.arxiv or (arxiv_m.group(1) if arxiv_m else None)
    doi = args.doi or (doi_m.group(1).rstrip(".,;:)]}") if doi_m else None)
    title = guess_title(doc)
    log(f"title guess: {title!r}  arXiv: {arxiv}  DOI: {doi}")

    meta: dict = {"title": title, "authors": [], "year": None, "arxiv": arxiv, "doi": doi}
    found = None if args.offline else lookup_paper(title, arxiv, doi)
    if found:
        rec = s2_record(found)
        meta.update({k: v for k, v in rec.items() if v})
    elif arxiv and not args.offline:
        rec = arxiv_api([arxiv]).get(arxiv)
        if rec:
            meta.update({k: v for k, v in rec.items() if v})
    if not meta.get("authors"):
        author = (doc.metadata or {}).get("author") or ""
        meta["authors"] = [a.strip() for a in re.split(r";|,| and ", author) if a.strip()]

    stem = args.name or paper_stem(meta["title"] or pdf.stem, meta.get("authors") or [], meta.get("year"))
    folder = vault / args.root / stem
    work = folder / WORK
    if (work / "manifest.json").exists() and not args.force:
        sys.exit(f"{folder} already extracted; pass --force to redo (the note is never overwritten)")
    (folder / "images").mkdir(parents=True, exist_ok=True)
    (work / "pages").mkdir(parents=True, exist_ok=True)
    (work / "equations").mkdir(parents=True, exist_ok=True)
    pdf_copy = folder / f"{stem}.pdf"
    if pdf.resolve() != pdf_copy.resolve():
        shutil.copy2(pdf, pdf_copy)

    # Body font size: the most common size by characters.
    sizes = Counter()
    for p in pages:
        for b in p.blocks:
            sizes[b["size"]] += len(b["text"])
    body = sizes.most_common(1)[0][0] if sizes else 10.0

    figures, equations, headings, text_lines, outline = [], [], [], [], []
    seen_labels: set[tuple[str, str]] = set()
    ref_lines: list[str] = []
    in_refs = False
    for p in pages:
        p.page.get_pixmap(dpi=PAGE_DPI).save(str(work / "pages" / f"p-{p.number:02d}.png"))
        text_lines.append(f"\n<!-- page {p.number} -->\n")
        graphics = p.graphics()
        # Captions first, so blocks inside a figure/table (axis labels, cell text) stay out of the text.
        regions: dict[int, tuple[str, str, pymupdf.Rect, int, str]] = {}
        continuation: set[int] = set()
        for b in p.blocks:
            label = caption_label(b["text"])
            if not label or label in seen_labels:
                continue
            kind, number = label
            # A caption set as several short blocks (IEEE: "TABLE IV" / "COMPARISON OF …" / "VAL SET.").
            box, texts, parts = pymupdf.Rect(b["bbox"]), [b["text"]], {id(b)}
            while True:
                nxt = next((o for o in p.blocks if id(o) not in parts and id(o) not in continuation
                            and -1 <= o["bbox"].y0 - box.y1 < 4 and o["bbox"].x0 < box.x1 and o["bbox"].x1 > box.x0
                            and len(o["text"]) < 400 and not caption_label(o["text"])), None)
                if nxt is None:
                    break
                parts.add(id(nxt))
                box |= nxt["bbox"]
                texts.append(nxt["text"])
            cap = {**b, "bbox": box, "text": " ".join(texts)}
            # Figures sit above their caption, tables usually below; the other side is a fallback.
            region, score = region_near(p, cap, graphics, above=kind != "table", skip=parts)
            if score == 0:
                other, other_score = region_near(p, cap, graphics, above=kind == "table", skip=parts)
                if other is not None and (other_score > 0 or region is None):
                    region, score = other, other_score
            if region is not None:
                seen_labels.add(label)
                continuation |= parts - {id(b)}
                regions[id(b)] = (kind, number, region, score, cap["text"])
        inside = lambda r: any((r & reg).get_area() > 0.7 * max(r.get_area(), 1e-3) for _, _, reg, _, _ in regions.values())  # noqa: E731
        for b in p.ordered():
            text = b["text"]
            if id(b) in regions:
                kind, number, region, score, text = regions[id(b)]
                name = f"{'fig' if kind == 'figure' else 'table'}-{number}"
                save_crop(p, region, folder / "images" / f"{name}.png", args.dpi)
                m = CAPTION.match(text) or CAPTION_IEEE_TABLE.match(text)
                caption = f"{'Figure' if kind == 'figure' else 'Table'} {number}: {text[m.end():].strip()}"
                figures.append({"kind": kind, "number": number, "page": p.number, "file": f"images/{name}.png",
                                "caption": caption, "rect": [round(v, 1) for v in region],
                                "pdfpp": f"{stem}.pdf#page={p.number}&rect={pdfpp_rect(p, region)}", "confidence": score})
                outline.append(f"    [{kind} {number}] images/{name}.png  (p.{p.number})")
                text_lines.append(f"\n[[{kind.upper()} {number} → images/{name}.png]] {caption}\n")
                continue
            if id(b) in continuation or inside(b["bbox"]):
                continue
            heading = split_heading(b, body)
            if heading and REFERENCE_HEAD.match(heading[1]):
                in_refs = True
                text_lines.append(f"\n## {heading[1]}\n")
                for line in b["raw"]["lines"][1:]:
                    ref_lines.append(line_text(line))
                continue
            if in_refs:
                if heading and SECTION_END.match(heading[1]):
                    in_refs = False
                else:
                    for line in b["raw"]["lines"]:
                        ref_lines.append(line_text(line))
                    continue
            if heading:
                level, htext, rest = heading
                if p.number == 1 and norm_title(htext) and norm_title(htext) in norm_title(meta.get("title") or ""):
                    continue
                headings.append({"level": level, "text": htext, "page": p.number})
                outline.append(f"{'#' * level} {htext}  (p.{p.number})")
                text_lines.append(f"\n{'#' * level} {htext}\n")
                if rest:
                    text_lines.append(rest)
                continue
            # Right-aligned equation numbers inside the block.
            for line in b["raw"]["lines"]:
                ltext = "".join(s["text"] for s in line["spans"]).strip()
                m = EQ_NUMBER.match(ltext)
                if not m:
                    continue
                lr = pymupdf.Rect(line["bbox"])
                cx0, cx1 = p.column(lr)
                if lr.x0 < cx0 + (cx1 - cx0) * 0.7:
                    continue
                num = m.group(1)
                if any(e["number"] == num for e in equations):
                    continue
                prose_above = [o["bbox"].y1 for o in p.blocks if is_prose(p, o) and o["bbox"].y1 <= lr.y0 and o["bbox"].x1 > cx0 and o["bbox"].x0 < cx1]
                prose_below = [o["bbox"].y0 for o in p.blocks if is_prose(p, o) and o["bbox"].y0 >= lr.y1 and o["bbox"].x1 > cx0 and o["bbox"].x0 < cx1]
                top = max(prose_above + [lr.y0 - 70])
                bottom = min(prose_below + [lr.y1 + 40])
                rect = pymupdf.Rect(cx0 + 8, max(top, lr.y0 - 70) - 2, cx1 - 4, min(bottom, lr.y1 + 40) + 2) & p.rect
                save_crop(p, rect, work / "equations" / f"eq-{num}.png", 200)
                equations.append({"number": num, "page": p.number, "file": f"{WORK}/equations/eq-{num}.png"})
                outline.append(f"    (eq {num}) {WORK}/equations/eq-{num}.png  (p.{p.number})")
            text_lines.append(text)

    refs = []
    for number, raw in split_reference_entries(ref_lines):
        ref = parse_reference(raw)
        ref["n"] = number
        refs.append(ref)

    manifest = {
        "stem": stem, "folder": str(folder), "vault": str(vault), "root": args.root,
        "note": f"{stem}.md", "pdf": f"{stem}.pdf", "source_pdf": str(pdf), "pages": len(pages),
        "page_dpi": PAGE_DPI, "meta": meta, "headings": headings, "figures": figures,
        "equations": equations, "pdf_references": len(refs),
    }
    save_json(work / "manifest.json", manifest)
    save_json(work / "pdf_refs.json", refs)
    (work / "text.md").write_text("\n\n".join(text_lines), "utf-8")
    (work / "outline.md").write_text("\n".join(outline) + "\n", "utf-8")

    note = folder / f"{stem}.md"
    if not note.exists():
        props = paper_props(meta)
        props["pdf"] = f"[[{stem}.pdf]]"
        if meta.get("url") or meta.get("arxiv"):
            props["source"] = f"https://arxiv.org/abs/{meta['arxiv']}" if meta.get("arxiv") else meta.get("url")
        props["References"] = []
        note.write_text(frontmatter(props) + f"# {meta.get('title') or stem}\n\n<!-- deep reading goes here -->\n", "utf-8")

    print(json.dumps({
        "folder": str(folder), "note": str(note), "title": meta.get("title"), "authors": len(meta.get("authors") or []),
        "year": meta.get("year"), "arxiv": meta.get("arxiv"), "doi": meta.get("doi"), "metadata_found": bool(found),
        "pages": len(pages), "headings": len(headings), "figures": sum(f["kind"] == "figure" for f in figures),
        "tables": sum(f["kind"] == "table" for f in figures), "numbered_equations": len(equations),
        "pdf_references": len(refs),
        "low_confidence_crops": [f["file"] for f in figures if f["confidence"] == 0],
    }, ensure_ascii=False, indent=2))


def cmd_crop(args) -> None:
    folder = Path(args.dir).expanduser().resolve()
    manifest = load_manifest(folder)
    doc = pymupdf.open(str(folder / manifest["pdf"]))
    page = Page(doc[args.page - 1])
    x0, y0, x1, y1 = (float(v) for v in args.rect.split(","))
    rect = pymupdf.Rect(x0, y0, x1, y1) & page.rect
    rel = f"images/{args.name}.png"
    save_crop(page, rect, folder / rel, args.dpi)
    for fig in manifest["figures"]:
        if fig["file"] == rel:
            fig.update({"page": args.page, "rect": [round(v, 1) for v in rect], "confidence": -1,
                        "pdfpp": f"{manifest['pdf']}#page={args.page}&rect={pdfpp_rect(page, rect)}"})
            break
    else:
        kind = "table" if args.name.startswith("table") else "figure"
        manifest["figures"].append({"kind": kind, "number": args.name.split("-", 1)[-1], "page": args.page, "file": rel,
                                    "caption": args.caption or "", "rect": [round(v, 1) for v in rect], "confidence": -1,
                                    "pdfpp": f"{manifest['pdf']}#page={args.page}&rect={pdfpp_rect(page, rect)}"})
    save_json(folder / WORK / "manifest.json", manifest)
    print(json.dumps({"saved": str(folder / rel), "pdfpp": f"{manifest['pdf']}#page={args.page}&rect={pdfpp_rect(page, rect)}"}))


def vault_papers(vault: Path, skip: Path) -> dict[str, str]:
    """arXiv/DOI/title keys -> vault-relative note path (without .md) for existing notes."""
    index: dict[str, str] = {}
    for path in vault.rglob("*.md"):
        rel = path.relative_to(vault)
        if any(part.startswith(".") for part in rel.parts) or skip in path.parents:
            continue
        try:
            head = path.read_text("utf-8", errors="strict")[:4000]
        except (UnicodeDecodeError, OSError):
            continue
        fm = re.match(r"\A---\r?\n(.*?)\r?\n---", head, re.S)
        if not fm:
            continue
        link = str(rel.with_suffix(""))
        block = fm.group(1)
        for m in ARXIV_IN_TEXT.finditer(block):
            index.setdefault(f"arxiv:{m.group(1)}", link)
        m = re.search(r"^arxiv:\s*[\"']?(\d{4}\.\d{4,5})", block, re.M | re.I)
        if m:
            index.setdefault(f"arxiv:{m.group(1)}", link)
        m = re.search(r"^doi:\s*[\"']?(10\.[^\s\"']+)", block, re.M | re.I)
        if m:
            index.setdefault(f"doi:{m.group(1).lower()}", link)
        m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", block, re.M)
        if m and len(norm_title(m.group(1))) >= 20:
            index.setdefault(f"title:{norm_title(m.group(1))}", link)
    return index


def arxiv_figures(arxiv: str, limit: int) -> list[tuple[str, str]]:
    """(image URL, caption) of the first figures in the arXiv HTML rendering."""
    for host in ("https://arxiv.org/html/", "https://ar5iv.labs.arxiv.org/html/"):
        throttle("arxiv-html", 1.0)
        status, page, final = http(f"{host}{arxiv}", timeout=40)
        if status == 200 and "ltx_figure" in page:
            found = figures_in_html(page, final, limit)
            if found:
                return found
    return []


def figures_in_html(page: str, base: str, limit: int) -> list[tuple[str, str]]:
    out = []
    for fig in re.finditer(r'<figure[^>]*class="[^"]*ltx_figure[^"]*"[^>]*>(.*?)</figure>', page, re.S):
        inner = fig.group(1)
        img = re.search(r'<img[^>]*src="([^"]+)"', inner)
        if not img or "ltx_table" in fig.group(0)[:200]:
            continue
        cap = re.search(r"<figcaption[^>]*>(.*?)</figcaption>", inner, re.S)
        caption = html.unescape(re.sub(r"<[^>]+>", "", cap.group(1))) if cap else ""
        caption = re.sub(r"\s+", " ", caption).strip()
        caption = re.sub(r"^(Figure|Fig\.)\s*(\d+)\s*[:.]?\s*", r"Figure \2: ", caption)
        # arXiv writes `2503.00513v2/x1.png` relative to /html/, ar5iv writes root-relative paths.
        out.append((urllib.parse.urljoin(base, html.unescape(img.group(1))), caption))
        if len(out) >= limit:
            break
    return out


def card_markdown(rec: dict, lang: str | None, figures: list[tuple[str, str]], cited_as: str | None) -> str:
    props = paper_props(rec)
    if cited_as:
        props["cited_as"] = cited_as
    parts = [frontmatter(props)]
    if rec.get("tldr"):
        parts.append(f"> [!summary] TL;DR\n> {rec['tldr']}\n")
    if rec.get("abstract"):
        parts.append(f"## Abstract\n\n{rec['abstract']}\n")
    if rec.get("abstract_translated"):
        parts.append(f"## 摘要（{'简体中文' if lang == 'zh-CN' else lang}）\n\n{rec['abstract_translated']}\n")
    if figures:
        parts.append("## Figures\n")
        for rel, caption in figures:
            parts.append(f"![[{rel}]]\n\n{caption}\n" if caption else f"![[{rel}]]\n")
    if not rec.get("abstract") and rec.get("raw"):
        parts.append(f"## Reference\n\n{rec['raw']}\n")
    return "\n".join(parts)


def cmd_refs(args) -> None:
    folder = Path(args.dir).expanduser().resolve()
    manifest = load_manifest(folder)
    vault = Path(manifest["vault"])
    meta = manifest["meta"]
    lang = None if args.lang == "none" else args.lang
    pdf_refs = json.loads((folder / WORK / "pdf_refs.json").read_text("utf-8"))

    # 1. Structured references from Semantic Scholar.
    s2_refs: list[dict] = []
    pid = f"ARXIV:{meta['arxiv']}" if meta.get("arxiv") else (f"DOI:{meta['doi']}" if meta.get("doi") else (f"{meta['s2']}" if meta.get("s2") else None))
    if pid:
        data = s2(f"/paper/{urllib.parse.quote(pid, safe=':')}/references", {"fields": S2_REF_FIELDS, "limit": 1000})
        for item in (data or {}).get("data") or [] if isinstance(data, dict) else []:
            cited = item.get("citedPaper") or {}
            if cited.get("title"):
                s2_refs.append(s2_record(cited))
    if not s2_refs and (meta.get("doi") or meta.get("arxiv")):
        # OpenAlex fallback: referenced_works of the paper itself.
        doi = meta.get("doi") or f"10.48550/arXiv.{meta['arxiv']}"
        work = openalex(f"/works/doi:{urllib.parse.quote(doi)}") or {}
        ids = [w.rsplit("/", 1)[-1] for w in work.get("referenced_works") or []]
        for i in range(0, len(ids), 50):
            page = openalex("/works", {"filter": "openalex:" + "|".join(ids[i:i + 50]), "per_page": 50})
            s2_refs += [openalex_record(w) for w in (page or {}).get("results") or [] if w.get("display_name")]
    log(f"structured references: {len(s2_refs)}; PDF reference entries: {len(pdf_refs)}")

    # 2. Pair PDF entries (which carry the citation numbers) with S2 records.
    used: set[int] = set()
    items: list[dict] = []
    for entry in pdf_refs:
        best, best_score = None, 0.0
        for i, rec in enumerate(s2_refs):
            if i in used:
                continue
            score = 0.0
            if entry.get("arxiv") and entry["arxiv"] == rec.get("arxiv"):
                score = 1.0
            elif entry.get("doi") and rec.get("doi") and entry["doi"].lower() == rec["doi"].lower():
                score = 1.0
            elif entry.get("title"):
                score = title_similarity(entry["title"], rec["title"])
                if score < 0.6 and norm_title(rec["title"]) and norm_title(rec["title"]) in norm_title(entry["raw"]):
                    score = 0.9
            if score > best_score:
                best, best_score = i, score
        rec = None
        if best is not None and best_score >= 0.6:
            used.add(best)
            rec = dict(s2_refs[best])
        items.append({"n": entry.get("n"), "raw": entry["raw"], "parsed_title": entry.get("title"), "rec": rec,
                      "arxiv": entry.get("arxiv"), "doi": entry.get("doi"), "year": entry.get("year")})
    for i, rec in enumerate(s2_refs):
        if i not in used:
            items.append({"n": None, "raw": "", "parsed_title": rec["title"], "rec": dict(rec)})

    # 3. Look up PDF entries S2 did not list.
    searched = 0
    for item in items:
        if item["rec"] or searched >= args.max_search:
            continue
        title = item.get("parsed_title") or ""
        if not title and not item.get("arxiv") and not item.get("doi"):
            continue
        searched += 1
        if searched % 10 == 0:
            log(f"  looked up {searched} unmatched entries…")
        hit = lookup_record(title, item.get("arxiv"), item.get("doi"))
        if hit:
            item["rec"] = hit
        elif title:
            item["rec"] = {"title": title, "authors": [], "year": item.get("year"), "arxiv": item.get("arxiv"),
                           "doi": item.get("doi"), "abstract": "", "raw": item["raw"]}
    if searched:
        log(f"searched {searched} unmatched PDF entries")

    # 4. Fill missing abstracts from arXiv / OpenAlex.
    recs = [i["rec"] for i in items if i["rec"]]
    need_arxiv = sorted({r["arxiv"] for r in recs if r.get("arxiv") and not r.get("abstract")})
    if need_arxiv:
        found = arxiv_api(need_arxiv)
        for r in recs:
            extra = found.get(r.get("arxiv") or "")
            if extra and not r.get("abstract"):
                r["abstract"] = extra["abstract"]
                r["authors"] = r.get("authors") or extra["authors"]
    for r in recs:
        if not r.get("abstract") and r.get("doi"):
            r["abstract"] = openalex_abstract(r["doi"])
    # TL;DRs are only served by the batch endpoint.
    s2_ids = [r["s2"] for r in recs if r.get("s2") and not r.get("tldr")]
    for i in range(0, len(s2_ids), 400):
        batch = s2("/paper/batch", {"fields": "tldr"}, {"ids": s2_ids[i:i + 400]})
        if isinstance(batch, list):
            tldrs = {p["paperId"]: ((p.get("tldr") or {}).get("text") or "") for p in batch if p}
            for r in recs:
                if r.get("s2") in tldrs and tldrs[r["s2"]]:
                    r["tldr"] = tldrs[r["s2"]]
    log(f"resolved {len(recs)} references; writing cards…")

    # 5. Write cards (or link existing vault notes).
    cache_path = folder / WORK / "translations.json"
    if cache_path.exists():
        _TRANSLATIONS.update(json.loads(cache_path.read_text("utf-8")))
    existing = {} if args.no_reuse else vault_papers(vault, folder)
    ref_dir = folder / "References"
    ref_dir.mkdir(exist_ok=True)
    root_rel = folder.relative_to(vault)
    out, created, reused = [], 0, 0
    seen_links: set[str] = set()
    jobs: list[tuple[Path, dict, str, str | None]] = []
    planned: set[Path] = set()
    for item in items:
        rec = item["rec"]
        if not rec or not rec.get("title"):
            out.append({"n": item["n"], "raw": item["raw"], "link": None})
            continue
        keys = ([f"arxiv:{rec['arxiv']}"] if rec.get("arxiv") else []) + ([f"doi:{rec['doi'].lower()}"] if rec.get("doi") else []) + [f"title:{norm_title(rec['title'])}"]
        link = next((existing[k] for k in keys if k in existing), None)
        status = "reused"
        if link and not link.startswith(str(root_rel / "References")):
            reused += 1
        else:
            stem = paper_stem(rec["title"], rec.get("authors") or [], rec.get("year"))
            path = ref_dir / f"{stem}.md"
            link = str((root_rel / "References" / stem))
            if path in planned:
                status = "duplicate"
            elif path.exists() and not args.refresh:
                status = "kept"
            else:
                status = "updated" if path.exists() else "created"
                planned.add(path)
                jobs.append((path, rec, stem, f"[{item['n']}]" if item.get("n") else None))
            for k in keys:
                existing.setdefault(k, link)
        if link in seen_links:
            status = "duplicate"
        seen_links.add(link)
        out.append({"n": item["n"], "title": rec["title"], "year": rec.get("year"),
                    "first_author": (rec.get("authors") or [""])[0], "link": link, "status": status})

    def build(job: tuple[Path, dict, str, str | None]) -> None:
        path, rec, stem, cited = job
        if lang:
            rec["title_translated"] = translate(rec["title"], lang)
            if rec.get("abstract"):
                rec["abstract_translated"] = translate(rec["abstract"], lang)
        figs: list[tuple[str, str]] = []
        if rec.get("arxiv") and args.card_figures > 0:
            for k, (url, caption) in enumerate(arxiv_figures(rec["arxiv"], args.card_figures), 1):
                status_code, data, _ = http(url, binary=True, timeout=40)
                if status_code != 200 or not data:
                    continue
                ext = Path(urllib.parse.urlparse(url).path).suffix.lower() or ".png"
                rel = f"images/{stem}-fig{k}{ext}"
                (ref_dir / "images").mkdir(exist_ok=True)
                (ref_dir / rel).write_bytes(data)
                figs.append((rel, caption))
        path.write_text(card_markdown(rec, lang, figs, cited), "utf-8")

    # Translation and figure downloads dominate; run cards concurrently (throttles stay global).
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(build, job) for job in jobs]
        for done, future in enumerate(as_completed(futures), 1):
            try:
                future.result()
                created += 1
            except Exception as err:  # one bad card must not stop the rest
                log(f"  card failed: {err}")
            if done % 10 == 0:
                log(f"  cards: {done}/{len(jobs)}")
    save_json(folder / WORK / "refs.json", out)
    save_json(cache_path, _TRANSLATIONS)
    linked = [o for o in out if o.get("link")]
    print(json.dumps({"references": len(out), "linked": len(linked), "cards_written": created, "reused_vault_notes": reused,
                      "unresolved": [o["raw"][:120] for o in out if not o.get("link")][:15],
                      "refs_json": str(folder / WORK / "refs.json")}, ensure_ascii=False, indent=2))


def note_frontmatter(text: str) -> tuple[str, str, str] | None:
    m = re.match(r"\A(---\r?\n)(.*?)(\r?\n---\r?\n?)", text, re.S)
    if not m:
        return None
    return m.group(2), text[:m.start(2)], text[m.end(2):]


def cmd_check(args) -> None:
    folder = Path(args.dir).expanduser().resolve()
    manifest = load_manifest(folder)
    note_path = folder / manifest["note"]
    text = note_path.read_text("utf-8")
    body = text
    issues: list[str] = []
    parsed = note_frontmatter(text)
    if not parsed:
        issues.append("note has no frontmatter")
    else:
        body = parsed[2]
    if "<!-- deep reading goes here -->" in text:
        issues.append("note still contains the placeholder; the deep reading has not been written")

    embeds = set(re.findall(r"!\[\[([^\]|#]+)", body))
    for fig in manifest["figures"]:
        if fig["file"] not in embeds:
            issues.append(f"{fig['kind']} {fig['number']} not embedded: ![[{fig['file']}]]")
    for target in embeds:
        if not (folder / target).exists() and not list(Path(manifest["vault"]).rglob(Path(target).name))[:1]:
            issues.append(f"broken embed: {target}")
    tags = set(re.findall(r"\\tag\{([^}]+)\}", body))
    for eq in manifest["equations"]:
        if eq["number"] not in tags:
            issues.append(f"equation ({eq['number']}) missing: write it as $$ … \\tag{{{eq['number']}}} $$")
    if body.count("$$") % 2:
        issues.append("unbalanced $$ delimiters")

    refs_path = folder / WORK / "refs.json"
    links = []
    if refs_path.exists():
        links = list(dict.fromkeys(r["link"] for r in json.loads(refs_path.read_text("utf-8")) if r.get("link")))
    else:
        issues.append("references not resolved yet: run `refs`")
    fm = parsed[0] if parsed else ""
    present = set(re.findall(r"\[\[([^\]|]+)", fm))
    missing = [l for l in links if l not in present]
    if missing and args.fix and parsed:
        lines = fm.splitlines()
        start = next((i for i, l in enumerate(lines) if re.match(r"^References:", l)), None)
        entries = [f'  - "[[{l}]]"' for l in missing]
        if start is None:
            lines += ["References:"] + entries
        else:
            end = start + 1
            while end < len(lines) and re.match(r"^\s+-\s", lines[end]):
                end += 1
            if lines[start].strip() != "References:":
                lines[start] = "References:"
            lines[end:end] = entries
        text = parsed[1] + "\n".join(lines) + parsed[2]
        note_path.write_text(text, "utf-8")
        log(f"added {len(missing)} References links")
        missing = []
    if missing:
        issues.append(f"{len(missing)} reference links missing from frontmatter References (run check --fix)")

    stats = {
        "note": str(note_path), "chars": len(body), "sections": len(re.findall(r"^#{2,6} ", body, re.M)),
        "figures_expected": len(manifest["figures"]), "embeds": len(embeds),
        "equations_expected": len(manifest["equations"]), "display_math": body.count("$$") // 2,
        "highlights": len(re.findall(r"==[^=\n]+==", body)), "footnotes": len(re.findall(r"^\[\^[^\]]+\]:", body, re.M)),
        "reference_links": len(links), "issues": issues,
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    sys.exit(1 if issues else 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("extract")
    p.add_argument("pdf")
    p.add_argument("--vault", required=True)
    p.add_argument("--root", default="Papers/DeepRead", help="folder (relative to the vault) that holds paper folders")
    p.add_argument("--name", help="override the folder/note name")
    p.add_argument("--arxiv")
    p.add_argument("--doi")
    p.add_argument("--dpi", type=int, default=220)
    p.add_argument("--offline", action="store_true", help="skip metadata lookup")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_extract)
    p = sub.add_parser("crop")
    p.add_argument("dir")
    p.add_argument("--page", type=int, required=True)
    p.add_argument("--rect", required=True, help="x0,y0,x1,y1 in PDF points, top-left origin (page-render pixels / 2)")
    p.add_argument("--name", required=True, help="fig-3, table-2, …")
    p.add_argument("--caption")
    p.add_argument("--dpi", type=int, default=220)
    p.set_defaults(fn=cmd_crop)
    p = sub.add_parser("refs")
    p.add_argument("dir")
    p.add_argument("--lang", default="zh-CN", help="translate card titles/abstracts; 'none' to skip")
    p.add_argument("--card-figures", type=int, default=1, help="figures per card from arXiv HTML (0 = none)")
    p.add_argument("--max-search", type=int, default=80)
    p.add_argument("--no-reuse", action="store_true", help="always create cards, even when the vault already has the paper")
    p.add_argument("--refresh", action="store_true", help="rewrite existing cards")
    p.add_argument("--workers", type=int, default=4, help="cards built in parallel")
    p.set_defaults(fn=cmd_refs)
    p = sub.add_parser("check")
    p.add_argument("dir")
    p.add_argument("--fix", action="store_true")
    p.set_defaults(fn=cmd_check)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
