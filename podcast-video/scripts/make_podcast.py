"""双人播客合成：script.txt（A:/B: 行）→ edge-tts 分句合成 → ffmpeg 拼接为 podcast.mp3"""
import asyncio, subprocess, sys
from pathlib import Path
import edge_tts

ROOT = Path(sys.argv[1]).resolve()
VOICES = {"A": ("zh-CN-XiaoxiaoNeural", "+5%"), "B": ("zh-CN-YunxiNeural", "+0%")}
GAP_MS = 350
CONCURRENCY = 2

lines = []
for raw in (ROOT / "script.txt").read_text(encoding="utf-8").splitlines():
    if raw[:2] in ("A:", "B:"):
        lines.append((raw[0], raw[2:].strip()))

seg_dir = ROOT / "segments"
seg_dir.mkdir(exist_ok=True)

async def synth(i, spk, text, sem):
    out = seg_dir / f"{i:03d}_{spk}.mp3"
    if out.exists() and out.stat().st_size > 0:
        return out
    voice, rate = VOICES[spk]
    async with sem:
        for attempt in range(4):
            try:
                await edge_tts.Communicate(text, voice, rate=rate).save(str(out))
                return out
            except Exception as e:
                print(f"retry {i}: {e}", file=sys.stderr)
                await asyncio.sleep(2 * (attempt + 1))
    raise RuntimeError(f"segment {i} failed")

async def main():
    sem = asyncio.Semaphore(CONCURRENCY)
    return await asyncio.gather(*(synth(i, s, t, sem) for i, (s, t) in enumerate(lines)))

segs = asyncio.run(main())

# 统一转成 wav 并插入停顿，再整体编码成 mp3
silence = seg_dir / "gap.wav"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                "anullsrc=r=24000:cl=mono", "-t", str(GAP_MS / 1000), str(silence)], check=True)
lst = seg_dir / "list.txt"
with lst.open("w") as f:
    for s in segs:
        wav = s.with_suffix(".wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(s),
                        "-ar", "24000", "-ac", "1", str(wav)], check=True)
        f.write(f"file '{wav.name}'\nfile '{silence.name}'\n")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                "-af", "loudnorm=I=-16:TP=-1.5", "-c:a", "libmp3lame", "-b:a", "128k",
                str(ROOT / "podcast.mp3")], check=True)
print(f"done: {len(segs)} segments -> {ROOT / 'podcast.mp3'}")
