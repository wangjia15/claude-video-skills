"""motion-explainer pipeline: scene spec -> edge-tts beats -> timeline -> HTML player -> frames -> MP4.

Usage:
  python render.py <spec.py> <out_dir> [steps...]
Steps (default: tts timeline sheet frames mux):
  tts       synthesize one mp3 per beat (cached by text hash, so edited narration is always re-voiced)
  timeline  measure beats, lay out scenes, write timeline.json, player.html, narration.m4a, <slug>.srt
  sheet     screenshot one frame per beat into qa/ and tile contact sheets (layout QA, no video)
  frames    render every frame with headless Chrome in parallel workers -> build/chunk_*.mp4
  mux       join chunks + narration into <slug>.mp4
Spec module defines META (dict) and SCENES (list of dicts); see references/spec.md.
"""
import asyncio, hashlib, importlib.util, json, os, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAYER = HERE.parent / "runtime" / "player.html"
FPS, W, H = 30, 1920, 1080
LEAD, GAP, TAIL = 0.6, 0.28, 0.9          # seconds: before first beat, between beats, after last beat


def load_spec(path):
    spec = importlib.util.spec_from_file_location("spec_mod", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.META, mod.SCENES


def beat_parts(b):
    """A beat is a string (spoken == shown) or dict(say=spoken, sub=shown)."""
    return (b, b) if isinstance(b, str) else (b["say"], b.get("sub", b["say"]))


def key(text, voice, rate):
    return hashlib.sha1(f"{voice}|{rate}|{text}".encode()).hexdigest()[:16]


async def tts(meta, scenes, out):
    import edge_tts
    d = out / "build" / "audio"; d.mkdir(parents=True, exist_ok=True)
    voice, rate = meta.get("voice", "zh-CN-YunyangNeural"), meta.get("rate", "+5%")
    jobs = [beat_parts(b)[0] for s in scenes for b in s["say"]]
    for i, text in enumerate(jobs, 1):
        mp3 = d / f"{key(text, voice, rate)}.mp3"
        if mp3.exists() and mp3.stat().st_size > 0: continue
        for attempt in range(8):
            try:
                # write to a temp name and rename, so an interrupted run never leaves a cached partial file
                part = mp3.with_suffix(f".{os.getpid()}.part")
                await edge_tts.Communicate(text, voice, rate=rate).save(str(part))
                if part.stat().st_size > 0: part.replace(mp3); break
                part.unlink(missing_ok=True)
            except Exception as e:
                print(f"tts {i}/{len(jobs)} attempt {attempt+1}: {type(e).__name__}", flush=True)
                part.unlink(missing_ok=True); await asyncio.sleep(4 * (attempt + 1))
        else:
            raise RuntimeError(f"TTS failed: {text[:30]}")
    print(f"tts: {len(jobs)} beats ready")


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(p)]).strip())


PUNCT = "，。；：！？、,.;:!?"
is_word = lambda ch: ch.isascii() and (ch.isalnum() or ch in "-_./$@`")
def sub_chunks(text, limit=24):
    """Split shown text into subtitle phrases at punctuation; punctuation itself is not displayed."""
    parts, cur = [], ""
    for ch in text:
        if ch in PUNCT:
            if cur.strip(): parts.append(cur.strip())
            cur = ""
        else: cur += ch
    if cur.strip(): parts.append(cur.strip())
    out = []
    for p in parts:                       # merge tiny pieces, cut long ones
        if out and len(out[-1]) + len(p) + 1 <= 14: out[-1] += " " + p
        else:
            while len(p) > limit:
                cut = limit               # never split inside an ASCII word such as disable-model-invocation
                while cut > 1 and is_word(p[cut - 1]) and is_word(p[cut]): cut -= 1
                if cut <= 4:               # a tiny leading fragment reads badly: extend to the word end instead
                    cut = limit
                    while cut < len(p) and is_word(p[cut - 1]) and is_word(p[cut]): cut += 1
                out.append(p[:cut].strip()); p = p[cut:].strip()
            if p: out.append(p)
    return out or [text]


def write_player(data, out):
    html = PLAYER.read_text(encoding="utf-8").replace("/*__TIMELINE__*/", "window.__TIMELINE__=" + json.dumps(data, ensure_ascii=False) + ";")
    (out / "player.html").write_text(html, encoding="utf-8")


def timeline(meta, scenes, out):
    voice, rate = meta.get("voice", "zh-CN-YunyangNeural"), meta.get("rate", "+5%")
    adir = out / "build" / "audio"
    t, tl_scenes, subs, clips = 0.0, [], [], []
    for s in scenes:
        local, beats = LEAD + (0.4 if not tl_scenes else 0), []
        for b in s["say"]:
            say, shown = beat_parts(b)
            mp3 = adir / f"{key(say, voice, rate)}.mp3"; d = dur(mp3)
            beats.append(dict(t=round(local, 3), d=round(d, 3), sub=shown))
            clips.append((t + local, mp3))
            chunks = sub_chunks(shown); w = [max(1, len(c)) for c in chunks]; acc = 0
            for c, wi in zip(chunks, w):
                a = t + local + d * acc / sum(w); acc += wi; z = t + local + d * acc / sum(w)
                subs.append(dict(t0=round(a, 3), t1=round(z + (0.15 if c == chunks[-1] else 0), 3), text=c))
            local += d + GAP
        sd = local - GAP + TAIL + s.get("hold", 0)
        spec = {k: v for k, v in s.items() if k not in ("say", "hold")}
        tl_scenes.append(dict(start=round(t, 3), dur=round(sd, 3), beats=beats, spec=spec))
        t += sd
    total = round(t, 3)
    brand = meta.get("brand", ""); ep = meta.get("episode", "")
    data = dict(meta=dict(title=meta.get("title", ""), brand_html=f"{brand} · <b>{ep}</b>" if ep else brand),
                scenes=tl_scenes, subs=subs, total=total)
    (out / "build").mkdir(parents=True, exist_ok=True)
    (out / "build" / "timeline.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    write_player(data, out)
    # narration track: every beat placed at its absolute time
    inputs, filt = [], []
    for i, (at, mp3) in enumerate(clips):
        inputs += ["-i", str(mp3)]; ms = int(at * 1000)
        filt.append(f"[{i}:a]aresample=48000,adelay={ms}|{ms}[a{i}]")
    filt.append("".join(f"[a{i}]" for i in range(len(clips))) + f"amix=inputs={len(clips)}:normalize=0,apad,atrim=0:{total}[out]")
    script = out / "build" / "mix.txt"; script.write_text(";\n".join(filt))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-/filter_complex", str(script), "-map", "[out]",
                    "-ac", "1", "-c:a", "aac", "-b:a", "160k", str(out / "narration.m4a")], check=True)
    def ts(x):
        ms = round(x * 1000); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s_, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{s_:02d},{ms:03d}"
    (out / f"{meta['slug']}.srt").write_text("\n".join(f"{i}\n{ts(s['t0'])} --> {ts(s['t1'])}\n{s['text']}\n"
                                                    for i, s in enumerate(subs, 1)), encoding="utf-8")
    (out / "narration.md").write_text(f"# {meta.get('title','')} · 讲稿\n\n" + "\n\n".join(
        f"## {i}. {re.sub(r'[{][a-z]:([^{}]*)[}]', r'\\1', s.get('title',''))}\n\n" + "\n".join(beat_parts(b)[1] for b in s["say"])
        for i, s in enumerate(scenes, 1)), encoding="utf-8")
    print(f"timeline: {len(tl_scenes)} scenes, {sum(len(s['beats']) for s in tl_scenes)} beats, {total:.1f}s")
    return data


def browser(p):
    try: return p.chromium.launch(channel="chrome", args=["--force-device-scale-factor=1"])
    except Exception: return p.chromium.launch()


def open_player(p, out):
    b = browser(p); page = b.new_page(viewport=dict(width=W, height=H), device_scale_factor=1)
    page.goto((out / "player.html").as_uri() + "?render=1"); page.evaluate("document.fonts.ready.then(()=>true)")
    return b, page


def sheet(out):
    from playwright.sync_api import sync_playwright
    data = json.loads((out / "build" / "timeline.json").read_text(encoding="utf-8"))
    qa = out / "qa"; shutil.rmtree(qa, ignore_errors=True); qa.mkdir()
    times = []
    for i, s in enumerate(data["scenes"], 1):     # each beat after its reveal settles, plus the scene's final state
        for k, b in enumerate(s["beats"]): times.append((f"s{i:02d}b{k:02d}", s["start"] + b["t"] + min(b["d"], 1.6)))
        times.append((f"s{i:02d}zz", s["start"] + s["dur"] - 0.5))
    with sync_playwright() as p:
        b, page = open_player(p, out)
        for name, t in times:
            page.evaluate(f"seek({t})"); page.screenshot(path=str(qa / f"{name}.png"), type="png")
        b.close()
    shots = sorted(qa.glob("s*zz.png"))
    lst = qa / "list.txt"; lst.write_text("".join(f"file '{x}'\n" for x in shots))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-vf", "scale=640:360,tile=4x5:padding=6", "-frames:v", "1", str(qa / "contact.png")], check=True)
    print(f"sheet: {len(times)} QA frames in {qa}, final-state contact sheet qa/contact.png")


def worker(out, a, z, idx):
    from playwright.sync_api import sync_playwright
    chunk = out / "build" / f"chunk_{idx:02d}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(chunk)],
                          stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b, page = open_player(p, out)
        for f in range(a, z):
            page.evaluate(f"seek({f / FPS})")
            ff.stdin.write(page.screenshot(type="jpeg", quality=92))
            if (f - a) % 900 == 0: print(f"worker {idx}: frame {f - a}/{z - a}", flush=True)
        b.close()
    ff.stdin.close(); assert ff.wait() == 0


def frames(out, workers):
    data = json.loads((out / "build" / "timeline.json").read_text(encoding="utf-8"))
    n = int(data["total"] * FPS); step = -(-n // workers)
    for old in (out / "build").glob("chunk_*.mp4"): old.unlink()
    procs = [subprocess.Popen([sys.executable, __file__, "_worker", str(out), str(i * step), str(min(n, (i + 1) * step)), str(i)])
             for i in range(workers) if i * step < n]
    if any(p.wait() for p in procs): raise RuntimeError("a frame worker failed")
    print(f"frames: {n} frames rendered by {len(procs)} workers")


def mux(meta, out):
    chunks = sorted((out / "build").glob("chunk_*.mp4"))
    lst = out / "build" / "chunks.txt"; lst.write_text("".join(f"file '{c}'\n" for c in chunks))
    final = out / f"{meta['slug']}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(out / "narration.m4a"),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "copy", "-shortest", "-metadata", f"title={meta.get('title','')}",
                    "-movflags", "+faststart", str(final)], check=True)
    print(f"mux: {final} ({dur(final):.1f}s)")


if __name__ == "__main__":
    if sys.argv[1] == "_worker":
        worker(Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])); sys.exit()
    meta, scenes = load_spec(sys.argv[1]); out = Path(sys.argv[2]).resolve(); out.mkdir(parents=True, exist_ok=True)
    steps = sys.argv[3:] or ["tts", "timeline", "sheet", "frames", "mux", "player"]
    if "player" in steps and (out / "build" / "timeline.json").exists(): write_player(json.loads((out / "build" / "timeline.json").read_text(encoding="utf-8")), out)
    if "tts" in steps: asyncio.run(tts(meta, scenes, out))
    if "timeline" in steps: timeline(meta, scenes, out)
    if "sheet" in steps: sheet(out)
    if "frames" in steps or "mux" in steps:
        # Frame rendering saturates the CPU; when several videos are built at once they queue here.
        import fcntl
        with open("/tmp/motion-explainer-render.lock", "w") as lock:
            print("waiting for render slot...", flush=True); fcntl.flock(lock, fcntl.LOCK_EX)
            if "frames" in steps: frames(out, int(os.environ.get("ME_WORKERS", "4")))
            if "mux" in steps: mux(meta, out)
