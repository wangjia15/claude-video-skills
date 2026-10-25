#!/usr/bin/env python3
"""Build the bilingual STE explainer page from a content file.

Usage:
    python build.py content.json out.html [--source source_excerpt.txt] [--force]

Steps
  1. validate the content structure and lint the English text
  2. stop if there are ERROR items (use --force to build anyway)
  3. write one self-contained HTML file (inline CSS and JS, no network
     requests except the optional Google Fonts stylesheet)
"""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ste_lint  # noqa: E402


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    src, out = argv[1], argv[2]
    force = "--force" in argv
    source_text = None
    if "--source" in argv:
        source_text = open(argv[argv.index("--source") + 1], encoding="utf-8").read()

    content = json.load(open(src, encoding="utf-8"))
    errors, warns = ste_lint.lint(content, source_text)
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e)
    if errors and not force:
        print(f"-- {len(errors)} errors. Fix them, or use --force to build anyway.")
        return 1

    tpl = open(os.path.join(HERE, "..", "assets", "template.html"), encoding="utf-8").read()
    title = content["meta"]["title"]
    page_title = f"{title['en']} / {title['zh']}"
    data = json.dumps(content, ensure_ascii=False).replace("</", "<\\/")
    page = tpl.replace("__TITLE__", html.escape(page_title)).replace("__DATA__", data)
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    n = sum(1 for _ in ste_lint.iter_en_sentences(content))
    print(f"-- built {out} ({len(page) // 1024} KB, {n} English sentences, {len(warns)} warnings)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
