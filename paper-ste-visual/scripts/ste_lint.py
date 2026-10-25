#!/usr/bin/env python3
"""Lint and validate a paper-ste-visual content file.

Usage:
    python ste_lint.py content.json [--source source_excerpt.txt]

Exit code 1 when there are ERROR items. WARN items are advice only.

What it checks
  figures     3 to 5 figure cards; each card has original, plain (read, meaning,
              caution), and one redraw of a known type
  structure   every required field exists, ids resolve, English and Chinese
              text have the same number of sentences
  STE style   sentence length, paragraph length, vague words, contractions
              (ERROR); passive voice, -ing forms, complex tenses (WARN)
  layout      diagram labels that are too long for their box (WARN)
  numbers     with --source: every chart value and every decimal or percent
              number in the English text must appear in the source text,
              unless the number is listed in meta.derived_numbers (ERROR)

This is a helper for the main ASD-STE100 writing rules. It does not use the
official STE dictionary, so a clean result is not an STE certification.
"""
import json
import re
import sys

VAGUE = [
    "very", "really", "quite", "rather", "fairly", "extremely", "highly", "huge",
    "massive", "tiny", "amazing", "incredible", "dramatically", "significantly",
    "substantially", "greatly", "easily",
]
VAGUE_WARN = ["state-of-the-art", "cutting-edge", "novel", "groundbreaking", "robust", "seamless"]
PASSIVE = re.compile(
    r"\b(is|are|was|were|be|been|being)\s+"
    r"(\w+ed|made|done|shown|given|called|used|built|seen|taken|written|known|run|found|kept|held|set|put|chosen|driven|trained)\b",
    re.I)
PROGRESSIVE = re.compile(r"\b(is|are|was|were)\s+(?!training\b|testing\b|processing\b|existing\b|missing\b)\w+ing\b", re.I)
COMPLEX_TENSE = re.compile(r"\b(will have|would|could have|should have|has been|have been|had been|having)\b", re.I)
CONTRACTION = re.compile(r"\b\w+(n't|'re|'ve|'ll|'d|'m)\b", re.I)
NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?")


def words(s):
    return len(s.replace("**", "").split())


def split_sentences(text):
    return [t for t in re.split(r"(?<=[.!?])\s+", text.strip()) if t]


def strip_md(s):
    return s.replace("**", "")


def iter_diagram_sentences(d, base):
    if d.get("caption"):
        for s in split_sentences(d["caption"].get("en", "")):
            yield f"{base}.caption", s
    for sci, sc in enumerate(d.get("scenarios", [])):
        for sti, st in enumerate(sc.get("steps", [])):
            for s in split_sentences((st.get("caption") or {}).get("en", "")):
                yield f"{base}.scenarios[{sci}].steps[{sti}].caption", s
    for nid, n in d.get("nodes", {}).items():
        if n.get("desc"):
            for s in split_sentences(n["desc"].get("en", "")):
                yield f"{base}.nodes.{nid}.desc", s


def card_blocks(card):
    """Yield (name, block) for every {en: [...], zh: [...]} block of a figure card."""
    if "original" in card:
        yield "original", card["original"]
    for k in ("read", "meaning", "caution"):
        b = (card.get("plain") or {}).get(k)
        if b is not None:
            yield f"plain.{k}", b


def iter_figure_sentences(c):
    fg = c.get("figures") or {}
    for ci, card in enumerate(fg.get("cards", [])):
        base = f"figures.cards[{ci}]"
        for name, b in card_blocks(card):
            for k, s in enumerate(b.get("en", [])):
                yield f"{base}.{name}.en[{k}]", s
        rd = card.get("redraw") or {}
        if rd.get("type") == "diagram":
            yield from iter_diagram_sentences(rd.get("diagram", rd), f"{base}.redraw")
        for ii, it in enumerate(rd.get("items", [])):
            if rd.get("type") == "timeline":
                for k, s in enumerate((it.get("text") or {}).get("en", [])):
                    yield f"{base}.redraw.items[{ii}].text.en[{k}]", s
            if rd.get("type") == "panels":
                for key in ("claim", "plain"):
                    for k, s in enumerate((it.get(key) or {}).get("en", [])):
                        yield f"{base}.redraw.items[{ii}].{key}.en[{k}]", s


def iter_en_sentences(c):
    """Yield (path, sentence) for every English sentence that the page counts."""
    yield from iter_figure_sentences(c)
    for si, sec in enumerate(c.get("sections", [])):
        for pi, para in enumerate(sec.get("paras", [])):
            for k, s in enumerate(para.get("en", [])):
                yield f"sections[{si}].paras[{pi}].en[{k}]", s
        d = sec.get("diagram")
        if d:
            yield from iter_diagram_sentences(d, f"sections[{si}].diagram")
    for ti, t in enumerate(c.get("tables", [])):
        for ri, r in enumerate(t.get("rows", [])):
            if t.get("kind") == "compare":
                for ci, cell in enumerate(r.get("cells", [])):
                    for k, s in enumerate(cell):
                        yield f"tables[{ti}].rows[{ri}].cells[{ci}][{k}]", s
            else:
                for k, s in enumerate(r.get("def", [])):
                    yield f"tables[{ti}].rows[{ri}].def[{k}]", s


def validate(c):
    errs = []
    meta = c.get("meta")
    if not meta or "title" not in meta:
        errs.append("meta.title is missing")
    else:
        for k in ("en", "zh"):
            if k not in meta["title"]:
                errs.append(f"meta.title.{k} is missing")
    if not c.get("sections"):
        errs.append("sections must have at least one item")
    for si, sec in enumerate(c.get("sections", [])):
        p = f"sections[{si}]"
        if "title" not in sec or "en" not in sec["title"] or "zh" not in sec["title"]:
            errs.append(f"{p}.title needs en and zh")
        for pi, para in enumerate(sec.get("paras", [])):
            en, zh = para.get("en"), para.get("zh")
            if not isinstance(en, list) or not isinstance(zh, list):
                errs.append(f"{p}.paras[{pi}] needs en and zh lists")
            elif len(en) != len(zh):
                errs.append(f"{p}.paras[{pi}] has {len(en)} English and {len(zh)} Chinese sentences")
        d = sec.get("diagram")
        if d:
            errs += validate_diagram(d, p + ".diagram")
        ch = sec.get("chart")
        if ch:
            errs += validate_chart(ch, p + ".chart")
    errs += validate_figures(c.get("figures"))
    glossary_terms = set()
    for ti, t in enumerate(c.get("tables", [])):
        p = f"tables[{ti}]"
        if t.get("kind") not in ("glossary", "compare"):
            errs.append(f"{p}.kind must be glossary or compare")
            continue
        if "title" not in t:
            errs.append(f"{p}.title is missing")
        for ri, r in enumerate(t.get("rows", [])):
            if t["kind"] == "glossary":
                if not all(k in r for k in ("term", "def", "note")):
                    errs.append(f"{p}.rows[{ri}] needs term, def, note")
                else:
                    glossary_terms.add(r["term"]["en"].lower())
                    for a in r.get("aliases", []):
                        glossary_terms.add(a.lower())
            else:
                if not all(k in r for k in ("item", "cells", "note")):
                    errs.append(f"{p}.rows[{ri}] needs item, cells, note")
                elif len(r["cells"]) != len(t.get("cols", [])):
                    errs.append(f"{p}.rows[{ri}] has {len(r['cells'])} cells but cols has {len(t.get('cols', []))}")
    return errs, glossary_terms


REDRAW_TYPES = ("scatter", "diagram", "chart", "datatable", "timeline", "panels")


def validate_figures(fg):
    errs = []
    if not fg:
        return errs
    cards = fg.get("cards", [])
    if not 3 <= len(cards) <= 5:
        errs.append(f"figures.cards has {len(cards)} cards; use 3 to 5 core figures or tables")
    for ci, card in enumerate(cards):
        p = f"figures.cards[{ci}]"
        for k in ("label", "title"):
            if k not in card or "en" not in card[k] or "zh" not in card[k]:
                errs.append(f"{p}.{k} needs en and zh")
        for name, b in card_blocks(card):
            if not isinstance(b.get("en"), list) or not isinstance(b.get("zh"), list):
                errs.append(f"{p}.{name} needs en and zh lists")
            elif len(b["en"]) != len(b["zh"]):
                errs.append(f"{p}.{name} has {len(b['en'])} English and {len(b['zh'])} Chinese sentences")
        present = dict(card_blocks(card))
        for need in ("original", "plain.read", "plain.meaning", "plain.caution"):
            if need not in present:
                errs.append(f"{p} is missing '{need}'")
        rd = card.get("redraw") or {}
        t = rd.get("type")
        if t not in REDRAW_TYPES:
            errs.append(f"{p}.redraw.type must be one of {', '.join(REDRAW_TYPES)}")
            continue
        if t == "diagram":
            errs += validate_diagram(rd.get("diagram", rd), p + ".redraw")
        elif t == "chart":
            errs += validate_chart(rd.get("chart", rd), p + ".redraw")
        else:
            if t in ("scatter", "datatable", "timeline") and not rd.get("source"):
                errs.append(f"{p}.redraw.source is required (name the table or figure)")
            if t == "scatter":
                for k in ("x", "y"):
                    if k not in rd or "label" not in rd[k]:
                        errs.append(f"{p}.redraw.{k}.label needs en and zh")
                if not rd.get("points"):
                    errs.append(f"{p}.redraw.points is empty")
            if t == "datatable" and not (rd.get("columns") and rd.get("rows")):
                errs.append(f"{p}.redraw needs columns and rows")
            if t in ("timeline", "panels") and not rd.get("items"):
                errs.append(f"{p}.redraw.items is empty")
            if t == "panels":
                for ii, it in enumerate(rd.get("items", [])):
                    if (it.get("evidence") or {}).get("level") not in ("claim", "partial", "table"):
                        errs.append(f"{p}.redraw.items[{ii}].evidence.level must be claim, partial, or table")
            if t in ("timeline", "panels"):
                for ii, it in enumerate(rd.get("items", [])):
                    for key in (("text",) if t == "timeline" else ("claim", "plain")):
                        b = it.get(key) or {}
                        if len(b.get("en", [])) != len(b.get("zh", [])):
                            errs.append(f"{p}.redraw.items[{ii}].{key} has unequal English and Chinese sentences")
    return errs


def validate_diagram(d, p):
    errs = []
    rows, nodes = d.get("rows"), d.get("nodes")
    if not rows or not nodes:
        return [f"{p} needs rows and nodes"]
    placed = [n for r in rows for n in r]
    for n in placed:
        if n not in nodes:
            errs.append(f"{p}.rows uses unknown node '{n}'")
    for n, v in nodes.items():
        if n not in placed:
            errs.append(f"{p}.nodes.{n} is not placed in rows")
        if "label" not in v or "en" not in v["label"] or "zh" not in v["label"]:
            errs.append(f"{p}.nodes.{n}.label needs en and zh")
        if v.get("sub") and ("en" not in v["sub"] or "zh" not in v["sub"]):
            errs.append(f"{p}.nodes.{n}.sub needs en and zh")
    keys = set()
    for e in d.get("edges", []):
        a, b = (e[0], e[1]) if isinstance(e, list) else (e.get("from"), e.get("to"))
        if a not in nodes or b not in nodes:
            errs.append(f"{p}.edges uses unknown node in {a}>{b}")
        keys.add(f"{a}>{b}")
    for si, sc in enumerate(d.get("scenarios", [])):
        if "label" not in sc:
            errs.append(f"{p}.scenarios[{si}].label is missing")
        for sti, st in enumerate(sc.get("steps", [])):
            for n in st.get("nodes", []):
                if n not in nodes:
                    errs.append(f"{p}.scenarios[{si}].steps[{sti}] uses unknown node '{n}'")
            for e in st.get("edges", []):
                if f"{e[0]}>{e[1]}" not in keys:
                    errs.append(f"{p}.scenarios[{si}].steps[{sti}] uses unknown edge {e[0]}>{e[1]}")
            cap = st.get("caption")
            if not cap or "en" not in cap or "zh" not in cap:
                errs.append(f"{p}.scenarios[{si}].steps[{sti}].caption needs en and zh")
    return errs


def validate_chart(ch, p):
    errs = []
    if not ch.get("source"):
        errs.append(f"{p}.source is required (name the table or figure)")
    ids = [m.get("id") for m in ch.get("metrics", [])]
    if not ids:
        errs.append(f"{p}.metrics is empty")
    for m in ch.get("metrics", []):
        if "label" not in m or "en" not in m["label"] or "zh" not in m["label"]:
            errs.append(f"{p}.metrics label needs en and zh")
    for it in ch.get("items", []):
        for k in it.get("values", {}):
            if k not in ids:
                errs.append(f"{p}.items '{it.get('label')}' has unknown metric '{k}'")
    return errs


def est_width(text, size, bold):
    return sum((1.0 if ord(ch) > 0x2E80 else (0.62 if bold else 0.56)) * size for ch in text)


def all_diagrams(c):
    for si, sec in enumerate(c.get("sections", [])):
        if sec.get("diagram"):
            yield f"sections[{si}].diagram", sec["diagram"]
    for ci, card in enumerate((c.get("figures") or {}).get("cards", [])):
        rd = card.get("redraw") or {}
        if rd.get("type") == "diagram":
            yield f"figures.cards[{ci}].redraw", rd.get("diagram", rd)


def layout_warnings(c):
    warns = []
    for base, d in all_diagrams(c):
        if "rows" not in d or "nodes" not in d:
            continue
        rows, nodes = d["rows"], d["nodes"]
        edges = [(e[0], e[1]) if isinstance(e, list) else (e["from"], e["to"]) for e in d.get("edges", [])]
        row_of = {n: i for i, r in enumerate(rows) for n in r}
        for ri, ids in enumerate(rows):
            side = any(row_of[a] == ri and row_of[b] == ri for a, b in edges)
            gap = 36 if side else 14
            n = len(ids)
            w = min(300, (320 - (n - 1) * gap) / n)
            for nid in ids:
                node = nodes[nid]
                for lang in ("en", "zh"):
                    if est_width(node["label"][lang], 13, True) > w - 14:
                        warns.append(f"{base}.nodes.{nid}.label.{lang} is long for a {w:.0f}px box (font will shrink)")
                    if node.get("sub") and est_width(node["sub"][lang], 12, False) > w - 14:
                        warns.append(f"{base}.nodes.{nid}.sub.{lang} is long for a {w:.0f}px box (font will shrink)")
    return warns


def lint(c, source_text=None):
    limit = c.get("meta", {}).get("limit", 25)
    errors, warns = [], []
    v_errs, glossary_terms = validate(c)
    errors += v_errs

    for path, s in iter_en_sentences(c):
        n = words(s)
        if n > limit:
            errors.append(f"{path}: {n} words (limit {limit}): {strip_md(s)[:70]}...")
        low = strip_md(s).lower()
        for w in VAGUE:
            if re.search(rf"\b{re.escape(w)}\b", low):
                errors.append(f"{path}: vague word '{w}'")
        for w in VAGUE_WARN:
            if w in low:
                warns.append(f"{path}: vague or marketing word '{w}'")
        if CONTRACTION.search(strip_md(s)):
            errors.append(f"{path}: contraction")
        if PASSIVE.search(strip_md(s)):
            warns.append(f"{path}: possible passive voice: {strip_md(s)[:70]}")
        if PROGRESSIVE.search(strip_md(s)):
            warns.append(f"{path}: -ing verb form: {strip_md(s)[:70]}")
        if COMPLEX_TENSE.search(strip_md(s)):
            warns.append(f"{path}: complex tense: {strip_md(s)[:70]}")

    for si, sec in enumerate(c.get("sections", [])):
        for pi, para in enumerate(sec.get("paras", [])):
            if len(para.get("en", [])) > 6:
                errors.append(f"sections[{si}].paras[{pi}]: {len(para['en'])} sentences (limit 6)")

    # bold terms should have a glossary row
    seen = set()
    for si, sec in enumerate(c.get("sections", [])):
        for para in sec.get("paras", []):
            for s in para.get("en", []):
                for t in re.findall(r"\*\*(.+?)\*\*", s):
                    key = t.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    if glossary_terms and key not in glossary_terms:
                        warns.append(f"sections[{si}]: bold term '{t}' has no glossary row (use term or aliases)")

    warns += layout_warnings(c)

    if source_text is not None:
        derived = set(map(str, c.get("meta", {}).get("derived_numbers", [])))

        def in_source(num):
            plain = num.rstrip("%")
            return re.search(rf"(?<![\d.]){re.escape(plain)}(?![\d])", source_text) is not None

        for si, sec in enumerate(c.get("sections", [])):
            ch = sec.get("chart")
            if ch:
                for it in ch.get("items", []):
                    for mid, val in it.get("values", {}).items():
                        m = next((m for m in ch["metrics"] if m["id"] == mid), {})
                        dec = m.get("decimals", 1)
                        text = f"{val:.{dec}f}"
                        if text not in derived and not in_source(text):
                            errors.append(f"sections[{si}].chart: value {text} ({it['label']}, {mid}) is not in the source text")
        for ci, card in enumerate((c.get("figures") or {}).get("cards", [])):
            rd = card.get("redraw") or {}
            base = f"figures.cards[{ci}].redraw"
            if rd.get("type") == "scatter":
                dx, dy = rd.get("x", {}).get("decimals"), rd.get("y", {}).get("decimals")
                for p in rd.get("points", []):
                    for key, dec in (("x", dx), ("y", dy)):
                        text = f"{p[key]:.{dec}f}" if isinstance(dec, int) else str(p[key])
                        if text not in derived and not in_source(text):
                            errors.append(f"{base}: point {p['label']} {key}={text} is not in the source text")
            if rd.get("type") == "datatable":
                for r in rd.get("rows", []):
                    for col in rd.get("columns", []):
                        v = r.get("values", {}).get(col["id"])
                        if isinstance(v, (int, float)):
                            text = f"{v:.{col.get('decimals', 1)}f}"
                            if text not in derived and not in_source(text):
                                errors.append(f"{base}: value {text} ({r['label']}, {col['id']}) is not in the source text")
        for path, s in iter_en_sentences(c):
            for num in NUMBER.findall(strip_md(s)):
                interesting = ("." in num) or num.endswith("%") or (num.isdigit() and int(num) >= 100)
                if interesting and num not in derived and num.rstrip("%") not in derived and not in_source(num):
                    errors.append(f"{path}: number {num} is not in the source text (add it to meta.derived_numbers if you calculated it)")
    return errors, warns


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = argv[1]
    source = None
    if "--source" in argv:
        source = open(argv[argv.index("--source") + 1], encoding="utf-8").read()
    c = json.load(open(path, encoding="utf-8"))
    errors, warns = lint(c, source)
    n_sent = sum(1 for _ in iter_en_sentences(c))
    longest = max((words(s) for _, s in iter_en_sentences(c)), default=0)
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    print(f"-- {n_sent} English sentences, longest {longest} words, {len(errors)} errors, {len(warns)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
