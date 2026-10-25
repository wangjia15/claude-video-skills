"""Static slide-video pipeline: a slides.py spec -> HTML deck -> PNG slides -> PDF,
edge-tts narration per slide, SRT subtitles and an MP4.

Usage: build.py <slides.py> <out_dir> [html png tts video]
The spec module defines TITLE, SLUG, FOOTER and SLIDES; optional VOICE, RATE and
THEME (dict of CSS-variable overrides, e.g. {"--acc": "#7aa2f7"}) customize it.
See ../references/spec.md and ../references/modes.md.
"""
import asyncio, html, importlib.util, re, subprocess, sys
from pathlib import Path

# Usage: build.py <slides.py> <out_dir> [html png tts video]
# slides.py must define TITLE, SLUG (e.g. "02-memory"), FOOTER (e.g. "Claude How To · 02 记忆") and SLIDES.
_spec = importlib.util.spec_from_file_location("slides_mod", Path(sys.argv[1]).resolve())
_mod = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mod)
SLIDES, TITLE, SLUG, FOOTER = _mod.SLIDES, _mod.TITLE, _mod.SLUG, _mod.FOOTER
VOICE = getattr(_mod, "VOICE", "zh-CN-YunyangNeural")
RATE = getattr(_mod, "RATE", "+5%")
THEME = getattr(_mod, "THEME", {})

OUT = Path(sys.argv[2]).resolve()
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
W, H = 1920, 1080
PAD = 0.8  # seconds of silence after each slide

CSS = r"""
:root{--bg:#14120f;--panel:#1f1c18;--panel2:#2a2620;--ink:#f3eee6;--mute:#a79f93;--acc:#d97757;--acc2:#e9b44c;--ok:#6fbf73;--bad:#e06c6c;--line:#3a352d}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#000;font-family:"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;color:var(--ink)}
.slide{width:1920px;height:1080px;position:relative;overflow:hidden;background:radial-gradient(1200px 700px at 85% -10%,#3a2418 0%,transparent 60%),var(--bg);padding:90px 120px 110px;display:flex;flex-direction:column}
.slide .tag{font-size:26px;letter-spacing:4px;color:var(--acc);font-weight:600;margin-bottom:14px}
.slide h2{font-size:64px;font-weight:700;margin-bottom:40px;line-height:1.2}
.slide h2 code{font-size:56px}
.body{flex:1;display:flex;flex-direction:column;gap:28px;font-size:30px;line-height:1.55}
.foot{position:absolute;left:120px;right:120px;bottom:44px;display:flex;justify-content:space-between;font-size:22px;color:var(--mute)}
.bar{position:absolute;left:0;bottom:0;height:8px;background:linear-gradient(90deg,var(--acc),var(--acc2))}
code,pre,kbd{font-family:"JetBrains Mono","SF Mono",Menlo,monospace}
code{background:rgba(217,119,87,.14);color:#ffb38f;padding:2px 10px;border-radius:8px;font-size:.88em}
kbd{border:1px solid var(--line);border-bottom-width:3px;border-radius:6px;padding:0 8px;font-size:.85em}
pre{background:#0d0c0a;border:1px solid var(--line);border-radius:18px;padding:28px 34px;font-size:25px;line-height:1.55;white-space:pre;overflow:hidden}
pre code{background:none;color:#e8e2d8;padding:0;font-size:1em}
pre .c{color:#7d7568}pre .k{color:#e9b44c}pre .v{color:#ff9a6b;font-weight:600}
pre.mini{padding:18px 26px;font-size:22px}
.lead{font-size:34px;color:#e6dfd3}
b,strong{color:var(--acc2)}
table{border-collapse:collapse;width:100%;font-size:28px;background:var(--panel);border-radius:18px;overflow:hidden}
th{background:var(--panel2);text-align:left;color:var(--acc2);padding:16px 26px;font-weight:600}
td{padding:13px 26px;border-top:1px solid var(--line);vertical-align:top}
td:first-child{white-space:nowrap}
table.small{font-size:24px}table.small td,table.small th{padding:10px 20px}
.grid2,.grid3,.grid4{display:grid;gap:28px}
.grid2{grid-template-columns:1fr 1fr}.grid3{grid-template-columns:repeat(3,1fr)}.grid4{grid-template-columns:repeat(4,1fr)}
.split{display:grid;grid-template-columns:1.15fr 1fr;gap:36px;align-items:start}
.split pre{font-size:22px;padding:24px 28px}
.split>div{display:flex;flex-direction:column;gap:22px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:22px;padding:28px 30px;display:flex;flex-direction:column;gap:12px}
.card h3{font-size:31px;color:var(--ink)}
.card p,.card li{font-size:26px;color:var(--mute);line-height:1.5}
.card ul{padding-left:30px;display:flex;flex-direction:column;gap:6px}
.card .ic{font-size:52px}
.card.bad{border-color:rgba(224,108,108,.45)}
.cmds .card code{font-size:27px;align-self:flex-start}
.note{background:rgba(233,180,76,.09);border-left:6px solid var(--acc2);padding:18px 26px;border-radius:10px;font-size:27px}
.note.warn{background:rgba(224,108,108,.09);border-left-color:var(--bad)}
.note.small{font-size:23px}
.sub{font-size:32px;margin-bottom:16px}
.ex{margin-top:16px;font-size:27px}
.pill{display:inline-block;padding:2px 16px;border-radius:99px;background:var(--panel2);color:var(--mute);font-size:24px}
.pill.ok{background:rgba(111,191,115,.18);color:var(--ok)}
.migrate{display:flex;align-items:center;gap:40px;justify-content:center;margin:10px 0}
.mbox{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:24px 34px}
.mbox.ok{border-color:var(--ok)}
.mlabel{font-size:22px;color:var(--mute);margin-bottom:8px}
.arrow{font-size:60px;color:var(--acc)}
.flow{display:flex;align-items:center;gap:22px;justify-content:center;margin:20px 0}
.fnode{background:var(--panel);border:2px solid var(--line);border-radius:20px;padding:26px 30px;text-align:center;font-size:29px;min-width:250px}
.fnode small{color:var(--mute);font-size:22px;display:block;margin-top:6px}
.fnode.in{border-color:var(--acc)}.fnode.out{border-color:var(--ok)}
.farrow{font-size:46px;color:var(--acc)}
.dodont th.ok{color:var(--ok)}.dodont th.bad{color:var(--bad)}
.dodont td{width:50%;white-space:normal}
.cover{justify-content:center;background:radial-gradient(900px 700px at 80% 20%,#5a2f1c 0%,transparent 65%),radial-gradient(700px 600px at 0% 100%,#2b2312 0%,transparent 60%),var(--bg)}
.cover .tag,.cover h2{display:none}
.cover-kicker{font-size:30px;letter-spacing:8px;color:var(--acc);margin-bottom:30px}
.cover-title{font-size:150px;line-height:1.1;font-weight:800}
.cover-title span{font-size:84px;color:var(--acc2);font-weight:600}
.cover-sub{font-size:42px;color:#e6dfd3;margin-top:40px}
.cover-meta{font-size:28px;color:var(--mute);margin-top:30px}
.takeaways{display:flex;flex-direction:column;gap:22px;padding-left:0;counter-reset:t;list-style:none}
.takeaways li{counter-increment:t;font-size:33px;background:var(--panel);border-radius:18px;padding:20px 30px 20px 100px;position:relative}
.fig{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:16px;display:flex;flex-direction:column;gap:10px;align-items:center;justify-content:center;min-height:0}
.fig img{max-width:100%;max-height:520px;object-fit:contain;border-radius:8px}
.fig figcaption{font-size:24px;color:var(--mute)}
.analogy{background:rgba(111,191,115,.08);border-left:6px solid var(--ok);padding:18px 26px;border-radius:10px;font-size:28px}
.analogy b{color:var(--ok)}
.takeaways li::before{content:counter(t);position:absolute;left:28px;top:50%;transform:translateY(-50%);width:50px;height:50px;border-radius:50%;background:var(--acc);color:#1b120c;font-weight:800;display:flex;align-items:center;justify-content:center;font-size:28px}
.next{margin-top:10px;font-size:30px;color:var(--mute);text-align:right}
/* viewer */
body.view{display:flex;align-items:center;justify-content:center;height:100vh;overflow:hidden}
body.view .slide{display:none;transform-origin:center;flex-shrink:0}
body.view .slide.on{display:flex}
body.print .slide{page-break-after:always}
body.shot .slide{display:none}body.shot .slide.on{display:flex}
@page{size:1920px 1080px;margin:0}
"""

JS = r"""
const q=new URLSearchParams(location.search),S=[...document.querySelectorAll('.slide')];
let i=Math.max(0,Math.min(S.length-1,(+q.get('n')||1)-1));
const mode=q.has('print')?'print':q.has('n')&&q.has('shot')?'shot':'view';
document.body.classList.add(mode);
function show(){S.forEach((s,k)=>s.classList.toggle('on',k===i));if(mode==='view'){const sc=Math.min(innerWidth/1920,innerHeight/1080);S[i].style.transform=`scale(${sc})`;history.replaceState(null,'','?n='+(i+1))}}
if(mode!=='print'){show();addEventListener('resize',show);
addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' ','Enter'].includes(e.key))i=Math.min(S.length-1,i+1);else if(['ArrowLeft','PageUp','Backspace'].includes(e.key))i=Math.max(0,i-1);else if(e.key==='Home')i=0;else if(e.key==='End')i=S.length-1;else return;e.preventDefault();show()});
addEventListener('click',e=>{i=e.clientX>innerWidth/2?Math.min(S.length-1,i+1):Math.max(0,i-1);show()});}
"""


def build_html():
    n = len(SLIDES)
    parts = []
    for k, s in enumerate(SLIDES, 1):
        parts.append(f"""<section class="slide {s.get('cls','')}">
<div class="tag">{s['tag']}</div><h2>{s['title']}</h2>
<div class="body">{s['body']}</div>
<div class="foot"><span>{FOOTER}</span><span>{k} / {n}</span></div>
<div class="bar" style="width:{k/n*100:.2f}%"></div>
<aside class="notes" hidden>{html.escape(s['notes'])}</aside>
</section>""")
    theme = ''.join(f':root{{{k}:{v}}}' for k, v in THEME.items())
    doc = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>{TITLE}</title><style>{CSS}{theme}</style></head><body>
{''.join(parts)}<script>{JS}</script></body></html>"""
    p = OUT / "slides.html"
    p.write_text(doc, encoding="utf-8")
    return p


def chrome(*args):
    # Parallel chapter builds share this machine: serialize Chrome through a global file lock,
    # give each call a private profile, and judge success by the output file because headless
    # Chrome sometimes exits non-zero during teardown after writing it.
    import fcntl, os, shutil, tempfile, time
    out = next((a.split("=", 1)[1] for a in args if a.startswith(("--screenshot=", "--print-to-pdf="))), None)
    with open("/tmp/kplex-course-chrome.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for attempt in range(5):
            if out: Path(out).unlink(missing_ok=True)
            prof = tempfile.mkdtemp(prefix="kchrome-")
            try:
                subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                                f"--user-data-dir={prof}", "--no-first-run", "--no-default-browser-check",
                                "--disable-crash-reporter", "--force-device-scale-factor=1", *args],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
            except subprocess.TimeoutExpired:
                pass
            finally:
                shutil.rmtree(prof, ignore_errors=True)
            if out and Path(out).exists() and Path(out).stat().st_size > 0:
                return
            time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"Chrome failed to produce {out}")


def screenshots(deck):
    d = OUT / "build" / "png"; d.mkdir(parents=True, exist_ok=True)
    for k in range(1, len(SLIDES) + 1):
        chrome(f"--window-size={W},{H}", "--virtual-time-budget=1500",
               f"--screenshot={d}/slide{k:02d}.png", f"{deck.as_uri()}?shot&n={k}")
    chrome("--no-pdf-header-footer", f"--print-to-pdf={OUT}/slides.pdf", f"{deck.as_uri()}?print")


async def tts():
    import edge_tts
    d = OUT / "build" / "audio"; d.mkdir(parents=True, exist_ok=True)
    async def once(k, text):
        mp3, srt = d / f"slide{k:02d}.mp3", d / f"slide{k:02d}.srt"
        txt = d / f"slide{k:02d}.txt"  # narration the cached audio was made from
        if srt.exists() and mp3.exists() and mp3.stat().st_size > 0 and txt.exists() \
                and txt.read_text(encoding="utf-8") == text: return
        sub = edge_tts.SubMaker()
        comm = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="SentenceBoundary")
        with open(mp3, "wb") as f:
            async for ch in comm.stream():
                if ch["type"] == "audio": f.write(ch["data"])
                elif ch["type"] in ("WordBoundary", "SentenceBoundary"): sub.feed(ch)
        srt.write_text(sub.get_srt(), encoding="utf-8")
        txt.write_text(text, encoding="utf-8")
    async def one(k, text):
        for attempt in range(10):
            try: return await once(k, text)
            except Exception as e:
                print(f"slide {k} attempt {attempt+1} failed: {type(e).__name__}", flush=True)
                (d / f"slide{k:02d}.srt").unlink(missing_ok=True)
                await asyncio.sleep(5 * (attempt + 1))
        raise RuntimeError(f"TTS failed for slide {k}")
    sem = asyncio.Semaphore(1)
    async def guarded(k, t):
        async with sem: await one(k, t)
    await asyncio.gather(*(guarded(k, s["notes"]) for k, s in enumerate(SLIDES, 1)))


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]).strip())


TS = re.compile(r"(\d+):(\d+):(\d+),(\d+)")
def ts2s(t): h, m, s, ms = map(int, TS.match(t).groups()); return h*3600+m*60+s+ms/1000
def s2ts(x):
    ms = round(x*1000); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def video():
    b = OUT / "build"; segs = b / "seg"; segs.mkdir(exist_ok=True)
    srt_out, idx, offset, lst = [], 1, 0.0, []
    for k in range(1, len(SLIDES) + 1):
        png, mp3 = b / "png" / f"slide{k:02d}.png", b / "audio" / f"slide{k:02d}.mp3"
        d = dur(mp3) + PAD + (0.4 if k == 1 else 0)
        seg = segs / f"seg{k:02d}.mp4"
        lead = 400 if k == 1 else 0
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "30", "-i", str(png),
                        "-i", str(mp3), "-filter_complex",
                        f"[1:a]adelay={lead}|{lead},apad,atrim=0:{d:.3f},aresample=48000[a]",
                        "-map", "0:v", "-map", "[a]", "-t", f"{d:.3f}",
                        "-c:v", "libx264", "-preset", "medium", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                        "-r", "30", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", str(seg)], check=True)
        lst.append(f"file '{seg}'")
        for block in (b / "audio" / f"slide{k:02d}.srt").read_text(encoding="utf-8").strip().split("\n\n"):
            lines = block.strip().splitlines()
            if len(lines) < 3: continue
            a, z = [ts2s(x.strip()) for x in lines[1].split("-->")]
            text = " ".join(lines[2:])
            srt_out.append(f"{idx}\n{s2ts(a+offset+lead/1000)} --> {s2ts(z+offset+lead/1000)}\n{text}\n")
            idx += 1
        offset += dur(seg)
    (b / "list.txt").write_text("\n".join(lst))
    srt = OUT / f"{SLUG}.srt"; srt.write_text("\n".join(srt_out), encoding="utf-8")
    raw = b / "joined.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(b / "list.txt"),
                    "-c", "copy", str(raw)], check=True)
    # MP4 with soft (toggleable) Chinese subtitle track
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-i", str(srt),
                    "-map", "0", "-map", "1", "-c", "copy", "-c:s", "mov_text",
                    "-metadata:s:s:0", "language=chi", "-metadata", f"title={TITLE}",
                    "-movflags", "+faststart", str(OUT / f"{SLUG}.mp4")], check=True)
    raw.unlink()


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    steps = sys.argv[3:] or ["html", "png", "tts", "video"]
    deck = build_html()
    if "png" in steps: screenshots(deck)
    if "tts" in steps: asyncio.run(tts())
    if "video" in steps: video()
    (OUT / "narration.md").write_text(
        f"# {TITLE} · 讲稿\n\n" + "\n\n".join(
            f"## {k}. {re.sub('<[^>]+>', '', s['title']) or '封面'}\n\n{s['notes']}"
            for k, s in enumerate(SLIDES, 1)), encoding="utf-8")
    print("done", steps)
